import atexit
import json
import multiprocessing
import os
import selectors
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Mapping
from multiprocessing.connection import Connection
from typing import IO, Any

from ...exceptions import ExecutorRuntimeError, ExecutorTimeoutError

_SET_TAG = "__type__"
_SET_TYPE = "set"
_SET_VALUE = "value"
_SUPERVISOR_MODULE = __spec__.name if __spec__ is not None else __name__
_SUPERVISOR_TIMEOUT_GRACE_S = 1.0
_PIPE_READ_CHUNK_SIZE = 64 * 1024


# ---------------------------------------------------------------------------
# JSON tagging for non-native types (currently: set)
# ---------------------------------------------------------------------------


def _to_json_safe(value: Any) -> Any:
    """Encode a value into a JSON-serializable form, tagging non-native types."""
    if isinstance(value, set):
        return {_SET_TAG: _SET_TYPE, _SET_VALUE: sorted(value)}
    return value


def _from_json_safe(value: Any) -> Any:
    """Decode a JSON-safe value back into its original Python type."""
    if isinstance(value, dict) and value.get(_SET_TAG) == _SET_TYPE and _SET_VALUE in value:
        return set(value[_SET_VALUE])
    return value


# ---------------------------------------------------------------------------
# Variable serialization
# ---------------------------------------------------------------------------


def _encode_variables(variables: dict[str, Any], *, strict: bool = True) -> str:
    """
    Serialize variables to a JSON string, encoding non-native types via tagging.

    When *strict* is True, raises TypeError for non-serializable values.
    When False, silently drops non-serializable entries (used for result encoding).
    """
    tagged = {k: _to_json_safe(v) for k, v in variables.items()}
    if not strict:
        tagged = {k: v for k, v in tagged.items() if _is_json_safe(v)}
    try:
        return json.dumps(tagged)
    except TypeError as e:
        raise TypeError(f"variables must be JSON-serializable: {e}") from e


def _decode_variables(raw_json: str) -> dict[str, Any]:
    """
    Deserialize variables from a JSON string, restoring tagged types.

    Raises:
        ExecutorRuntimeError: If the JSON cannot be parsed.
    """
    try:
        decoded = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ExecutorRuntimeError(f"Failed to parse output: {e}\nRaw: {raw_json!r}") from e
    return {k: _from_json_safe(v) for k, v in decoded.items()}


def _is_json_safe(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# JSON-line protocol helpers
# ---------------------------------------------------------------------------


def _write_json_line(stream: IO[bytes], message: Mapping[str, str | int]) -> None:
    stream.write(json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n")
    stream.flush()


def _read_json_line(stream: IO[bytes], timeout_s: float) -> str:
    """Read a single newline-terminated line from *stream* within *timeout_s* seconds."""
    sel = selectors.DefaultSelector()
    chunks: list[bytes] = []
    deadline = time.monotonic() + timeout_s
    try:
        sel.register(stream.fileno(), selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if not sel.select(remaining):
                raise TimeoutError

            chunk = os.read(stream.fileno(), _PIPE_READ_CHUNK_SIZE)
            if not chunk:
                raise EOFError

            chunks.append(chunk)
            if b"\n" in chunk:
                return b"".join(chunks).split(b"\n", maxsplit=1)[0].decode("utf-8")
    finally:
        sel.close()


def _decode_response(raw_response: str) -> tuple[str, str]:
    try:
        message = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ExecutorRuntimeError(
            f"Execution supervisor returned malformed JSON: {raw_response!r}"
        ) from e

    if (
        not isinstance(message, dict)
        or not isinstance(message.get("status"), str)
        or not isinstance(message.get("payload"), str)
    ):
        raise ExecutorRuntimeError("Execution supervisor returned an invalid result.")

    return message["status"], message["payload"]


# ---------------------------------------------------------------------------
# Forked child execution
# ---------------------------------------------------------------------------


def _discard_standard_streams() -> None:
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
    finally:
        if devnull_fd > 2:
            os.close(devnull_fd)


def _execute_child(conn: Connection, variables_json: str, code: str) -> None:
    try:
        _discard_standard_streams()
        variables = _decode_variables(variables_json)
        exec(code, variables)
        message = {"status": "ok", "payload": _encode_variables(variables, strict=False)}
    except BaseException:
        message = {"status": "error", "payload": traceback.format_exc()}

    try:
        conn.send_bytes(json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n")
    finally:
        conn.close()
        os._exit(0)


def _run_forked_child(variables_json: str, code: str, time_limit_s: int) -> dict[str, str]:
    context = multiprocessing.get_context("fork")
    parent_conn, child_conn = context.Pipe(duplex=False)
    process = context.Process(target=_execute_child, args=(child_conn, variables_json, code))
    process.start()
    child_conn.close()

    try:
        if not parent_conn.poll(time_limit_s):
            process.kill()
            process.join()
            return {"status": "timeout", "payload": str(time_limit_s)}

        try:
            raw_response = parent_conn.recv_bytes().decode("utf-8")
        except EOFError:
            return {
                "status": "error",
                "payload": "Child process exited without returning a result.",
            }

        status, payload = _decode_response(raw_response)
        return {"status": status, "payload": payload}
    finally:
        parent_conn.close()
        if process.is_alive():
            process.kill()
        process.join()
        process.close()


# ---------------------------------------------------------------------------
# Supervisor (long-lived process that receives requests over stdin/stdout)
# ---------------------------------------------------------------------------


def _supervisor_main() -> None:
    for raw_line in sys.stdin.buffer:
        try:
            request = json.loads(raw_line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")

            initial_json = request.get("initial_json")
            code = request.get("code")
            time_limit_s = request.get("time_limit_s")
            if (
                not isinstance(initial_json, str)
                or not isinstance(code, str)
                or not isinstance(time_limit_s, int)
            ):
                raise ValueError("request has invalid fields")

            message = _run_forked_child(initial_json, code, time_limit_s)
        except BaseException:
            message = {"status": "error", "payload": traceback.format_exc()}

        _write_json_line(sys.stdout.buffer, message)


class _ForkSupervisor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None

    def run(self, initial_json: str, code: str, time_limit_s: int) -> str:
        with self._lock:
            self._ensure_started()
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._process.stdout is not None

            try:
                _write_json_line(
                    self._process.stdin,
                    {"initial_json": initial_json, "code": code, "time_limit_s": time_limit_s},
                )
                raw_response = _read_json_line(
                    self._process.stdout, time_limit_s + _SUPERVISOR_TIMEOUT_GRACE_S
                )
            except (BrokenPipeError, EOFError, OSError, TimeoutError) as e:
                self.close()
                raise ExecutorRuntimeError(
                    "Execution supervisor stopped before returning a result."
                ) from e

            status, payload = _decode_response(raw_response)
            if status == "ok":
                return payload
            if status == "timeout":
                raise ExecutorTimeoutError(time_limit_s)
            if status == "error":
                raise ExecutorRuntimeError(payload.strip())
            raise ExecutorRuntimeError(f"Execution supervisor returned unknown status: {status}")

    def close(self) -> None:
        process = self._process
        self._process = None

        if process is None:
            return

        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()

        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return

        self.close()
        process = subprocess.Popen(
            [sys.executable, "-m", _SUPERVISOR_MODULE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            process.wait()
            raise ExecutorRuntimeError("Failed to start execution supervisor.")

        self._process = process


_thread_local = threading.local()
_fork_supervisors_lock = threading.Lock()
_fork_supervisors: list[_ForkSupervisor] = []


def _get_fork_supervisor() -> _ForkSupervisor:
    supervisor: _ForkSupervisor | None = getattr(_thread_local, "fork_supervisor", None)
    if supervisor is not None:
        return supervisor

    supervisor = _ForkSupervisor()
    _thread_local.fork_supervisor = supervisor
    with _fork_supervisors_lock:
        _fork_supervisors.append(supervisor)
    return supervisor


def _close_fork_supervisors() -> None:
    with _fork_supervisors_lock:
        supervisors = list(_fork_supervisors)
        _fork_supervisors.clear()

    for supervisor in supervisors:
        supervisor.close()


atexit.register(_close_fork_supervisors)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(code: str, variables: dict[str, Any], time_limit_s: int) -> None:
    """
    Execute a Python code block in a disposable child process with a wall-clock timeout.

    Serializes variables into the child process using a tagged JSON encoding that supports sets
    in addition to standard JSON-native types. The child reconstructs the original types before
    running user code, and re-encodes results for the return trip. The caller's variables dict is
    mutated in-place with the results.

    Supported round-trip types:
        - All JSON-native types (str, int, float, bool, None, list, dict)
        - set (encoded as a tagged dict; element order is not preserved)

    Args:
        code: Python source code to execute in the child process.
        variables: Initial variables to inject into the child's scope. Mutated
            in-place with updated values after execution.
        time_limit_s: Wall-clock timeout in seconds.

    Raises:
        TypeError: If any variable value cannot be encoded for IPC.
        ExecutorTimeoutError: If the child process exceeds time_limit_s.
        ExecutorRuntimeError: If the child process fails or its output cannot be parsed.
    """
    initial_json = _encode_variables(variables)
    variables.update(
        _decode_variables(_get_fork_supervisor().run(initial_json, code, time_limit_s))
    )


if __name__ == "__main__":
    _supervisor_main()
