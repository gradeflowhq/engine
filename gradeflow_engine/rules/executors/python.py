import inspect
import json
import subprocess
import sys
import textwrap
from typing import Any

from ...exceptions import ExecutorRuntimeError, ExecutorTimeoutError

# Tagged dict representation used for JSON round-tripping of non-serializable types.
_SET_TAG = "__type__"
_SET_TYPE = "set"
_SET_VALUE = "value"


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


def _is_json_safe(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def _encode_variables(variables: dict[str, Any]) -> str:
    """
    Serialize variables to a JSON string, encoding non-native types via tagging.

    Raises:
        TypeError: If a variable value cannot be made JSON-serializable.
    """
    try:
        return json.dumps({k: _to_json_safe(v) for k, v in variables.items()})
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


def _json_helper_source() -> str:
    helpers = (_to_json_safe, _from_json_safe, _is_json_safe)
    return "\n\n".join(textwrap.dedent(inspect.getsource(helper)) for helper in helpers)


def _build_child_program(initial_json: str, code: str) -> str:
    """
    Build the source of the child Python process.

    The child:
      1. Deserializes and restores tagged variables from the parent.
      2. Executes user-supplied code with those variables in scope.
      3. Re-encodes and emits JSON-serializable results to stdout.
    """
    return f"""\
import json
from typing import Any

_SET_TAG = {_SET_TAG!r}
_SET_TYPE = {_SET_TYPE!r}
_SET_VALUE = {_SET_VALUE!r}

{_json_helper_source()}


raw = json.loads({initial_json!r})
variables = {{k: _from_json_safe(v) for k, v in raw.items()}}

code = {code!r}
exec(code, variables)

encoded = {{k: _to_json_safe(v) for k, v in variables.items()}}
print(json.dumps({{k: v for k, v in encoded.items() if _is_json_safe(v)}}))
"""


def _run_subprocess(child_program: str, time_limit_s: int) -> subprocess.CompletedProcess[str]:
    """
    Run the child program in a subprocess with a wall-clock timeout.

    Raises:
        ExecutorTimeoutError: If execution exceeds time_limit_s.
        ExecutorRuntimeError: If the child process exits with a non-zero return code.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", child_program],
            capture_output=True,
            check=False,
            timeout=time_limit_s,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        raise ExecutorTimeoutError(time_limit_s) from e

    if result.returncode != 0:
        raise ExecutorRuntimeError(result.stderr.strip())

    return result


def run(code: str, variables: dict[str, Any], time_limit_s: int) -> None:
    """
    Execute a Python code block in a separate interpreter with a wall-clock timeout.

    Serializes variables into the child process using a tagged JSON encoding that
    supports sets in addition to standard JSON-native types. The child reconstructs
    the original types before running user code, and re-encodes results for the
    return trip. The caller's variables dict is mutated in-place with the results.

    Supported round-trip types:
        - All JSON-native types (str, int, float, bool, None, list, dict)
        - set (encoded as a tagged dict; element order is not preserved)

    Args:
        code: Python source code to execute in the child process.
        variables: Initial variables to inject into the child's scope. Mutated
            in-place with updated values after execution.
        time_limit_s: Wall-clock timeout in seconds.

    Raises:
        TypeError: If any variable value cannot be encoded for IPC.Raises:
        ExecutorTimeoutError: If the child process exceeds time_limit_s.
        ExecutorRuntimeError: If the child process fails or its output cannot be parsed.
    """
    initial_json = _encode_variables(variables)
    child_program = _build_child_program(initial_json, code)
    completed = _run_subprocess(child_program, time_limit_s)
    variables.update(_decode_variables(completed.stdout))
