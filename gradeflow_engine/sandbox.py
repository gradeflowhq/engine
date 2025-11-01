"""
Sandbox module for executing programmable grading rules safely.

Provides restricted execution environment for user-provided Python scripts
with time and memory limits using RestrictedPython.

PLATFORM SUPPORT:
This module requires Unix-like systems (Linux, macOS) for proper sandboxing.
Windows is NOT supported due to lack of signal.SIGALRM and resource limits.

SUPPORTED PYTHON FEATURES:
==========================

The sandbox uses RestrictedPython's predefined policies and builtins to provide
a safe but functional Python environment for grading scripts.

Built-in Functions (from safe_builtins):
- Type constructors: bool, bytes, int, float, complex, str, tuple
- Aggregation: len, sum, min, max, all, any, sorted
- Iteration: enumerate, map, filter, reversed, zip, range
- Math: abs, round, pow, divmod, hex, oct
- Type checking: isinstance, issubclass, callable
- Utilities: chr, ord, repr, hash, id, slice

Additional Types (from limited_builtins & utility_builtins):
- Sequence types: list, tuple, range
- Collection types: set, frozenset, dict
- Modules: math, random, string

Supported Operations:
- Arithmetic: +, -, *, /, //, %, **
- Comparison: ==, !=, <, <=, >, >=
- Logical: and, or, not
- Membership: in, not in
- Augmented assignments: +=, -=, *=, /=, //=, %=, **=
- Indexing/slicing: obj[key], obj[start:end]

Control Flow:
- if/elif/else statements
- for loops (with iteration guards)
- while loops
- break, continue
- try/except/finally

Data Structures:
- Lists: [1, 2, 3], indexing, slicing, methods
- Dicts: {'key': 'value'}, indexing, methods
- Sets: {1, 2, 3}, operations
- Tuples: (1, 2, 3), unpacking
- Strings: all string methods (split, join, strip, lower, upper, format, etc.)

Comprehensions & Generators:
- List comprehensions: [x for x in items]
- Dict comprehensions: {k: v for k, v in items}
- Set comprehensions: {x for x in items}
- Generator expressions: (x for x in items)

RESTRICTED/BLOCKED FEATURES (for security):
===========================================

- File I/O: open, file operations
- Network: socket, urllib, requests
- System: os, sys modules
- Subprocesses: subprocess, os.system
- Code execution: eval, exec, compile, __import__
- Reflection on protected attributes

GRADING SCRIPT API:
==================

Scripts have access to:
- student_answers: Dict[str, str] - all student answers
- question_id: str - current question being graded
- answer: str - student's answer to current question

Scripts must set:
- points_awarded: float - points to award (0 to max_points)
- feedback: str - optional feedback message

Example:
    script = '''
    # Award points for keywords
    keywords = ['python', 'programming']
    found = sum(1 for kw in keywords if kw in answer.lower())
    points_awarded = found * 5.0
    feedback = f'Found {found}/{len(keywords)} keywords'
    '''

SECURITY NOTE:
=============

This sandbox provides basic protection but is not bulletproof. RestrictedPython
has known limitations and potential bypass techniques. For production use with
untrusted scripts, consider:
- Running in containerized environments (Docker)
- Using process isolation
- Setting strict OS-level resource limits
- Implementing additional security layers

The current implementation is suitable for:
- Trusted script authors (instructors/TAs)
- Educational environments
- Development and testing
"""

import logging
import os
import platform
import resource
import signal
from contextlib import contextmanager
from pathlib import Path

from RestrictedPython import (  # type: ignore[import-untyped]
    compile_restricted_exec,
    limited_builtins,
    safe_globals,
    utility_builtins,
)
from RestrictedPython.Guards import (  # type: ignore[import-untyped]
    full_write_guard,
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
)

logger = logging.getLogger(__name__)

# Constants
SCRIPT_MAX_SIZE_BYTES = 50_000
SCRIPT_MAX_LINES = 1_000
DEFAULT_TIMEOUT_MS = 5_000
DEFAULT_MEMORY_MB = 50
CONTAINER_INDICATORS = ["docker", "kubepods", "containerd", "lxc"]
CONTAINER_ENV_VARS = ["DOCKER_CONTAINER", "KUBERNETES_SERVICE_HOST"]

# Check platform at module import time
if platform.system() == "Windows":
    raise RuntimeError(
        "Programmable grading rules are not supported on Windows. "
        "The sandbox requires Unix-like systems (Linux, macOS) for proper security isolation. "
        "Please use Linux or macOS, or disable programmable rules."
    )


class SandboxExecutionError(Exception):
    """Raised when script execution fails."""

    pass


class SandboxTimeoutError(Exception):
    """Raised when script execution times out."""

    pass


def _is_running_in_container() -> bool:
    """
    Detect if the current process is running inside a container.

    Checks for common container indicators:
    - Docker: /.dockerenv file
    - Kubernetes/Docker: Environment variables
    - General: /proc/1/cgroup content

    Returns:
        True if running in a container, False otherwise
    """
    if platform.system() == "Windows":
        return False

    try:
        # Check for /.dockerenv file (Docker)
        if Path("/.dockerenv").exists():
            return True

        # Check for container environment variables
        if any(key in os.environ for key in CONTAINER_ENV_VARS):
            return True

        # Check /proc/1/cgroup for container indicators
        cgroup_path = Path("/proc/1/cgroup")
        if cgroup_path.exists():
            try:
                with cgroup_path.open("r", encoding="utf-8", errors="ignore") as f:
                    cgroup_content = f.read()
                    if any(indicator in cgroup_content for indicator in CONTAINER_INDICATORS):
                        return True
            except OSError:
                pass
    except Exception:
        # If detection fails, assume not in container (safer for memory limits)
        pass

    return False


def _validate_script(script: str) -> None:
    """
    Validate script content before execution.

    Args:
        script: Python script to validate

    Raises:
        ValueError: If script is invalid (empty, too large, too many lines, syntax error)
        SandboxExecutionError: If script has syntax errors
    """
    if not script or not script.strip():
        raise ValueError("Script cannot be empty")

    # Check script size
    if len(script) > SCRIPT_MAX_SIZE_BYTES:
        raise ValueError(
            f"Script exceeds maximum size of {SCRIPT_MAX_SIZE_BYTES // 1024}KB "
            f"(got {len(script)} bytes)"
        )

    # Check line count
    line_count = script.count("\n") + 1
    if line_count > SCRIPT_MAX_LINES:
        raise ValueError(
            f"Script exceeds maximum line count of {SCRIPT_MAX_LINES} (got {line_count} lines)"
        )

    # Check for basic Python syntax
    try:
        compile(script, "<syntax_check>", "exec")
    except SyntaxError as e:
        raise SandboxExecutionError(f"Script has syntax errors at line {e.lineno}: {e.msg}") from e


def _safe_iter(obj: object) -> object:
    """
    Safe iterator that allows iteration over basic Python types.

    RestrictedPython requires explicit iterator support. This function
    enables for loops, comprehensions, and iteration operations.
    
    Args:
        obj: Any iterable object (list, tuple, dict, set, range, etc.)
        
    Returns:
        Iterator for the given object
    """
    return iter(obj)


def _inplacevar(op: str, x: object, y: object) -> object:
    """
    Handler for augmented assignment operations (+=, -=, *=, etc.).

    RestrictedPython transforms augmented assignments to use this function.
    This allows scripts to use operations like `x += 1` safely.

    Args:
        op: Operation string (e.g., '+=', '-=')
        x: Left operand
        y: Right operand

    Returns:
        Result of the operation
    """
    ops = {
        "+=": lambda a, b: a + b,
        "-=": lambda a, b: a - b,
        "*=": lambda a, b: a * b,
        "/=": lambda a, b: a / b,
        "//=": lambda a, b: a // b,
        "%=": lambda a, b: a % b,
        "**=": lambda a, b: a**b,
        "&=": lambda a, b: a & b,
        "|=": lambda a, b: a | b,
        "^=": lambda a, b: a ^ b,
        ">>=": lambda a, b: a >> b,
        "<<=": lambda a, b: a << b,
    }
    return ops.get(op, lambda a, b: a)(x, y)


def _create_restricted_globals(
    student_answers: dict[str, str], question_id: str, answer: str
) -> dict[str, object]:
    """
    Create a restricted global namespace for script execution.

    Uses RestrictedPython's safe_globals as base and enhances with:
    - limited_builtins: list, tuple, range
    - utility_builtins: set, frozenset, math, random, string
    - Common functions: sum, min, max, all, any, enumerate, map, filter
    - Iteration support (for loops, comprehensions) via guards
    - Student data access (answers, question_id)

    Args:
        student_answers: All student answers
        question_id: Current question ID
        answer: Student's answer to the current question

    Returns:
        Dictionary with restricted globals and script variables
    """
    # Start with safe_globals (includes safe_builtins and basic guards)
    restricted_globals: dict[str, object] = safe_globals.copy()  # type: ignore[assignment]

    # Add limited_builtins: list, tuple, range (sequence types)
    restricted_globals["__builtins__"].update(limited_builtins)  # type: ignore[attr-defined]

    # Add utility_builtins: set, frozenset, math, random, string, etc.
    restricted_globals["__builtins__"].update(utility_builtins)  # type: ignore[attr-defined]

    # Add commonly used aggregation and iteration functions
    restricted_globals["__builtins__"].update(  # type: ignore[attr-defined]
        {
            "sum": sum,
            "min": min,
            "max": max,
            "all": all,
            "any": any,
            "enumerate": enumerate,
            "map": map,
            "filter": filter,
            "reversed": reversed,
        }
    )

    # Add RestrictedPython guards for iteration and operations
    restricted_globals.update(
        {
            # Iteration support (required for for-loops, comprehensions)
            "_getiter_": _safe_iter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_unpack_sequence_": guarded_unpack_sequence,
            # Item access (for dicts, lists)
            "_getitem_": lambda obj, index: obj[index],
            # Augmented assignments (+=, -=, *=, etc.)
            "_inplacevar_": _inplacevar,
            # Write guard (allows writes to local variables)
            "_write_": full_write_guard,
        }
    )

    # Provide student data (read-only copies)
    restricted_globals.update(
        {
            "student_answers": dict(student_answers),
            "question_id": str(question_id),
            "answer": str(answer),
            # Result variables that scripts must set
            "points_awarded": 0.0,
            "feedback": "",
        }
    )

    return restricted_globals


def _extract_and_validate_results(restricted_globals: dict[str, object]) -> tuple[float, str]:
    """
    Extract and validate grading results from script execution.

    Args:
        restricted_globals: Global namespace after script execution

    Returns:
        Tuple of (points_awarded, feedback)
    """
    points_value = restricted_globals.get("points_awarded", 0.0)
    # Object type is too generic but we know it's numeric at runtime
    points_awarded = (
        float(points_value) if points_value is not None else 0.0  # type: ignore[arg-type]
    )
    feedback = str(restricted_globals.get("feedback", ""))

    # Ensure points_awarded is non-negative
    if points_awarded < 0:
        logger.warning(f"Script returned negative points ({points_awarded}), clamping to 0")
        points_awarded = 0.0
        feedback = "Invalid negative points, defaulting to 0"

    return points_awarded, feedback


@contextmanager
def time_limit(timeout_ms: int):
    """
    Context manager for enforcing time limits on code execution.

    Uses SIGALRM to interrupt execution after the specified timeout.
    Only works on Unix-like systems (Linux, macOS).

    Args:
        timeout_ms: Timeout in milliseconds

    Raises:
        SandboxTimeoutError: If execution exceeds the timeout
        ValueError: If timeout_ms is invalid

    Example:
        >>> with time_limit(1000):  # 1 second timeout
        ...     # Code that must complete within 1 second
        ...     pass
    """
    if timeout_ms <= 0:
        raise ValueError(f"timeout_ms must be positive, got {timeout_ms}")

    def _timeout_handler(signum: int, frame) -> None:
        """Signal handler for execution timeout."""
        raise SandboxTimeoutError("Script execution timed out")

    timeout_seconds = timeout_ms / 1000.0
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout_seconds) + 1)  # Round up to nearest second
    logger.debug(f"Set timeout to {timeout_seconds}s ({timeout_ms}ms)")

    try:
        yield
    finally:
        # Restore signal handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        logger.debug("Timeout cleared")


@contextmanager
def memory_limit(memory_mb: int, strict: bool = False):
    """
    Context manager for enforcing memory limits on code execution.

    Uses resource.RLIMIT_AS to limit virtual memory allocation.
    Only works on Unix-like systems (Linux, macOS).
    
    Automatically skips memory limits in containerized environments (Docker, Kubernetes, etc.)
    where resource limits may not work properly or cause MemoryErrors.

    Args:
        memory_mb: Memory limit in megabytes
        strict: If True, raise an error if the limit cannot be set.
                If False, log a warning and continue without the limit.

    Raises:
        SandboxExecutionError: If strict=True and the limit cannot be set
        ValueError: If memory_mb is invalid

    Example:
        >>> with memory_limit(50):  # 50 MB limit
        ...     # Code that must use less than 50 MB
        ...     pass
    """
    if memory_mb <= 0:
        raise ValueError(f"memory_mb must be positive, got {memory_mb}")

    # Skip memory limits entirely in containerized environments
    # to avoid MemoryErrors and other issues in CI/CD pipelines
    if _is_running_in_container():
        logger.debug("Running in container, skipping memory limit enforcement")
        yield
        return

    memory_bytes = memory_mb * 1024 * 1024
    old_limit: tuple[int, int] | None = None
    limit_set = False

    try:
        # Get current limit
        old_limit = resource.getrlimit(resource.RLIMIT_AS)
        # Set new limit (soft and hard)
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        limit_set = True
        logger.debug(f"Set memory limit to {memory_mb}MB ({memory_bytes} bytes)")
    except (ValueError, OSError) as e:
        # Resource limits may fail in some environments (e.g., containers)
        if strict:
            raise SandboxExecutionError(
                f"Cannot enforce memory limit of {memory_mb}MB: {e}. "
                "This may be due to running in a restricted environment. "
                "Set strict=False to allow execution without memory limits."
            ) from e
        logger.warning(f"Failed to set memory limit: {e}. Continuing without memory limit.")

    try:
        yield
    finally:
        # Restore old limit if we successfully set a new one
        if limit_set and old_limit is not None:
            try:
                resource.setrlimit(resource.RLIMIT_AS, old_limit)
                logger.debug(f"Restored memory limit to {old_limit}")
            except (ValueError, OSError) as e:
                # Critical: If we can't restore the limit, we must raise an error
                # Otherwise the entire process continues with restricted memory
                logger.error(f"CRITICAL: Failed to restore memory limit: {e}")
                raise SandboxExecutionError(
                    f"Failed to restore memory limit after script execution: {e}. "
                    "This is a critical error that may affect subsequent operations."
                ) from e


def execute_programmable_rule(
    script: str,
    student_answers: dict[str, str],
    question_id: str,
    answer: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    memory_mb: int = DEFAULT_MEMORY_MB,
    strict_limits: bool = False,
) -> tuple[float, str]:
    """
    Execute a programmable grading script in a restricted environment.

    Uses RestrictedPython to provide a sandboxed execution environment with
    time and memory limits.
    
    Note: Memory limits are automatically skipped in containerized environments
    (Docker, Kubernetes, CI/CD) where they can cause MemoryErrors or fail to work properly.

    Args:
        script: Python script to execute
        student_answers: All student answers (dict of question_id -> answer)
        question_id: Current question being graded
        answer: Student's answer to the current question
        timeout_ms: Timeout in milliseconds (default: 5000)
        memory_mb: Memory limit in megabytes (default: 50, skipped in containers)
        strict_limits: If True, fail if resource limits cannot be set (default: False)

    Returns:
        Tuple of (points_awarded, feedback)

    Raises:
        SandboxExecutionError: If script compilation or execution fails
        SandboxTimeoutError: If script exceeds timeout
        ValueError: If timeout_ms or memory_mb are invalid

    Security:
        - RestrictedPython limits available builtins and operations
        - SIGALRM timeout (Unix/Linux/macOS only)
        - Memory limit via resource.RLIMIT_AS (Unix/Linux/macOS only, skipped in containers)
        - No file system or network access

    Script Variables Available:
        - student_answers: Dict[str, str] - Read-only copy of all answers
        - question_id: str - Current question ID
        - answer: str - Student's current answer
        - points_awarded: float - Set this to award points (default: 0.0)
        - feedback: str - Set this for feedback (default: '')
    """
    # Validate inputs
    if timeout_ms <= 0:
        raise ValueError(f"timeout_ms must be positive, got {timeout_ms}")
    if memory_mb <= 0:
        raise ValueError(f"memory_mb must be positive, got {memory_mb}")

    # Validate script
    _validate_script(script)

    logger.debug(f"Executing programmable rule for question {question_id}")

    # Compile the script with RestrictedPython (before entering resource limits)
    compile_result = compile_restricted_exec(script, filename="<grading_script>")

    if compile_result.errors:
        error_msg = "; ".join(compile_result.errors)
        logger.error(f"Script compilation failed: {error_msg}")
        raise SandboxExecutionError(f"Script compilation failed: {error_msg}")

    byte_code = compile_result.code

    # Set up restricted globals
    restricted_globals = _create_restricted_globals(student_answers, question_id, answer)

    # Execute with sandboxing (memory_limit handles container detection internally)
    try:
        with memory_limit(memory_mb, strict=strict_limits):
            with time_limit(timeout_ms):
                logger.debug("Executing restricted script")
                exec(byte_code, restricted_globals)

        # Extract and validate results
        points_awarded, feedback = _extract_and_validate_results(restricted_globals)

        logger.debug(f"Script completed: {points_awarded} points, feedback: {feedback[:50]}")
        return points_awarded, feedback

    except SandboxTimeoutError:
        logger.error(f"Script execution timed out after {timeout_ms}ms")
        raise
    except SandboxExecutionError:
        raise
    except Exception as e:
        logger.exception(f"Script execution failed: {e}")
        raise SandboxExecutionError(f"Script execution failed: {str(e)}") from e
