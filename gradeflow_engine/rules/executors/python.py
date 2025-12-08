import json
import subprocess
import sys
from typing import Any


def run(code: str, variables: dict[str, Any], time_limit_s: int) -> None:
    """
    Execute a Python code block in a separate interpreter, with a wall-clock timeout.
    - Initializes the child process's globals with values from variables (JSON-serializable).
    - Executes `code` via exec().
    - Returns updated values for the same variable names back to the caller by mutating variables.

    Notes:
      - Only JSON-serializable values are supported for round-tripping.
      - time_limit_s is enforced by subprocess timeout.
    """
    # Prepare initial variables (must be JSON serializable)
    try:
        initial_json = json.dumps(variables)
    except TypeError as e:
        raise TypeError(f"variables must be JSON-serializable: {e}") from e

    # Child program: load vars, exec user code, emit updated vars as JSON
    child_program = f"""
import json

variables = json.loads({initial_json!r})

code = {code!r}
exec(code, {{}}, variables)

def _is_jsonable(v):
    try:
        json.dumps(v)
        return True
    except TypeError:
        return False

to_dump = {{ k:v for k, v in variables.items() if _is_jsonable(v) }}
print(json.dumps(to_dump))
"""

    # Run child process with timeout
    try:
        completed = subprocess.run(
            [sys.executable, "-c", child_program],
            capture_output=True,
            check=False,
            timeout=time_limit_s,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Code execution timed out after {time_limit_s}s") from e

    if completed.returncode != 0:
        err = completed.stderr.strip()
        raise RuntimeError(err)

    # Parse result and update variables
    try:
        updated = json.loads(completed.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse output: {e}\nRaw: {completed.stdout!r}") from e

    variables.update(updated)
