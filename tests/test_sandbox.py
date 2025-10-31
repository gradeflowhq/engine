"""
Comprehensive tests for the sandbox module.

Tests the sandboxed execution environment including:
- Script validation
- Time limits
- Memory limits
- RestrictedPython security
- Error handling
- Platform detection

Run with: pytest tests/test_sandbox.py -v
"""

import platform
import resource
import signal
from unittest.mock import MagicMock, patch

import pytest

from gradeflow_engine.sandbox import (
    SCRIPT_MAX_LINES,
    SandboxExecutionError,
    SandboxTimeoutError,
    _create_restricted_globals,
    _extract_and_validate_results,
    _is_running_in_container,
    _validate_script,
    execute_programmable_rule,
    memory_limit,
    time_limit,
)

# Skip all tests on Windows
pytestmark = pytest.mark.skipif(
    platform.system() == "Windows", reason="Sandbox not supported on Windows"
)


class TestScriptValidation:
    """Test script validation before execution."""

    def test_validate_valid_script(self):
        """Test validation of a valid script."""
        script = """
points_awarded = 5.0
feedback = "Good answer"
"""
        # Should not raise
        _validate_script(script)

    def test_validate_empty_script(self):
        """Test validation rejects empty script."""
        with pytest.raises(ValueError, match="Script cannot be empty"):
            _validate_script("")

    def test_validate_whitespace_only_script(self):
        """Test validation rejects whitespace-only script."""
        with pytest.raises(ValueError, match="Script cannot be empty"):
            _validate_script("   \n\n  \t  ")

    def test_validate_script_too_large(self):
        """Test validation rejects scripts exceeding size limit."""
        # Create a script larger than SCRIPT_MAX_SIZE_BYTES but under line limit
        # Use longer lines to hit size limit before line limit
        large_script = ("x = " + "1" * 100 + "\n") * 600  # ~60KB, 600 lines

        with pytest.raises(ValueError, match="exceeds maximum size"):
            _validate_script(large_script)

    def test_validate_script_too_many_lines(self):
        """Test validation rejects scripts with too many lines."""
        # Create a script with more than SCRIPT_MAX_LINES
        many_lines_script = "x = 1\n" * (SCRIPT_MAX_LINES + 10)

        with pytest.raises(ValueError, match="exceeds maximum line count"):
            _validate_script(many_lines_script)

    def test_validate_script_syntax_error(self):
        """Test validation detects syntax errors."""
        invalid_script = """
points_awarded = 5.0
if True
    feedback = "Missing colon"
"""
        with pytest.raises(SandboxExecutionError, match="syntax errors"):
            _validate_script(invalid_script)

    def test_validate_script_complex_syntax_error(self):
        """Test validation detects complex syntax errors."""
        invalid_script = "def foo(: pass"

        with pytest.raises(SandboxExecutionError):
            _validate_script(invalid_script)

    def test_validate_script_at_size_limit(self):
        """Test validation accepts script exactly at size limit."""
        # Create a script right at the limit (should pass)
        # Use lines that are under 100 chars and under 1000 lines
        script = ("x = " + "1" * 45 + "\n") * 900  # ~45KB, 900 lines - well under both limits

        # Should not raise
        _validate_script(script)


class TestRestrictedGlobals:
    """Test creation of restricted global namespace."""

    def test_create_restricted_globals_basic(self):
        """Test basic restricted globals creation."""
        student_answers = {"Q1": "Paris", "Q2": "9.8"}
        question_id = "Q1"
        answer = "Paris"

        globals_dict = _create_restricted_globals(student_answers, question_id, answer)

        assert "__builtins__" in globals_dict
        assert globals_dict["student_answers"] == student_answers
        assert globals_dict["question_id"] == question_id
        assert globals_dict["answer"] == answer
        assert globals_dict["points_awarded"] == 0.0
        assert globals_dict["feedback"] == ""

    def test_create_restricted_globals_read_only(self):
        """Test that student data is copied (read-only)."""
        student_answers = {"Q1": "Paris"}
        question_id = "Q1"
        answer = "Paris"

        globals_dict = _create_restricted_globals(student_answers, question_id, answer)

        # Modify the returned dict's student_answers
        globals_dict["student_answers"]["Q1"] = "Modified"

        # Original should be unchanged
        assert student_answers["Q1"] == "Paris"

    def test_create_restricted_globals_safe_builtins(self):
        """Test that only safe builtins are available."""
        globals_dict = _create_restricted_globals({}, "Q1", "answer")

        builtins = globals_dict["__builtins__"]

        # Safe builtins should be present
        assert "len" in builtins
        assert "str" in builtins
        assert "int" in builtins
        assert "float" in builtins

        # Unsafe builtins should NOT be present
        assert "open" not in builtins
        assert "compile" not in builtins
        assert "__import__" not in builtins


class TestResultExtraction:
    """Test extraction and validation of grading results."""

    def test_extract_valid_results(self):
        """Test extraction of valid results."""
        globals_dict = {"points_awarded": 5.0, "feedback": "Great answer!"}

        points, feedback = _extract_and_validate_results(globals_dict)

        assert points == 5.0
        assert feedback == "Great answer!"

    def test_extract_results_default_values(self):
        """Test extraction when variables not set."""
        globals_dict = {}

        points, feedback = _extract_and_validate_results(globals_dict)

        assert points == 0.0
        assert feedback == ""

    def test_extract_results_negative_points(self):
        """Test extraction clamps negative points to zero."""
        globals_dict = {"points_awarded": -5.0, "feedback": "Negative points"}

        points, feedback = _extract_and_validate_results(globals_dict)

        assert points == 0.0
        assert "Invalid negative points" in feedback

    def test_extract_results_type_conversion(self):
        """Test extraction converts types properly."""
        globals_dict = {
            "points_awarded": 5,  # int instead of float
            "feedback": 123,  # int instead of str
        }

        points, feedback = _extract_and_validate_results(globals_dict)

        assert isinstance(points, float)
        assert points == 5.0
        assert isinstance(feedback, str)
        assert feedback == "123"

    def test_extract_results_with_extra_variables(self):
        """Test extraction ignores extra variables."""
        globals_dict = {
            "points_awarded": 3.5,
            "feedback": "OK",
            "extra_var": "ignored",
            "another_var": 42,
        }

        points, feedback = _extract_and_validate_results(globals_dict)

        assert points == 3.5
        assert feedback == "OK"


class TestTimeLimitContextManager:
    """Test the time_limit context manager."""

    def test_time_limit_within_timeout(self):
        """Test code that completes within timeout."""
        with time_limit(1000):  # 1 second
            # Quick operation
            x = sum(range(100))

        # Should complete without error
        assert x == 4950

    def test_time_limit_exceeds_timeout(self):
        """Test code that exceeds timeout."""
        with pytest.raises(SandboxTimeoutError, match="timed out"):
            with time_limit(100):  # 100ms
                # Infinite loop
                while True:
                    pass

    def test_time_limit_invalid_timeout(self):
        """Test invalid timeout value."""
        with pytest.raises(ValueError, match="timeout_ms must be positive"):
            with time_limit(0):
                pass

        with pytest.raises(ValueError):
            with time_limit(-100):
                pass

    def test_time_limit_restores_signal_handler(self):
        """Test that signal handler is restored after context."""
        # Save original handler
        original_handler = signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.signal(signal.SIGALRM, original_handler)

        with time_limit(1000):
            pass

        # Handler should be restored
        current_handler = signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.signal(signal.SIGALRM, current_handler)

        assert current_handler == original_handler

    def test_time_limit_alarm_cleared(self):
        """Test that alarm is cleared after context."""
        with time_limit(1000):
            pass

        # Alarm should be cleared (0)
        remaining = signal.alarm(0)
        assert remaining == 0


class TestMemoryLimitContextManager:
    """Test the memory_limit context manager."""

    def test_memory_limit_within_limit(self):
        """Test code that stays within memory limit."""
        try:
            with memory_limit(100):  # 100 MB
                # Small allocation
                data = [0] * 1000

            # Should complete without error
            assert len(data) == 1000
        except (SandboxExecutionError, ValueError, OSError):
            # May fail in restricted environments (containers, etc.)
            pytest.skip("Cannot set/restore memory limits in this environment")

    def test_memory_limit_invalid_memory(self):
        """Test invalid memory value."""
        with pytest.raises(ValueError, match="memory_mb must be positive"):
            with memory_limit(0):
                pass

        with pytest.raises(ValueError):
            with memory_limit(-50):
                pass

    def test_memory_limit_restores_limit(self):
        """Test that memory limit is restored after context."""
        old_limit = resource.getrlimit(resource.RLIMIT_AS)

        try:
            with memory_limit(100):
                pass

            # Limit should be restored
            current_limit = resource.getrlimit(resource.RLIMIT_AS)
            assert current_limit == old_limit
        except (ValueError, OSError):
            # May fail in restricted environments
            pytest.skip("Cannot set resource limits in this environment")

    def test_memory_limit_strict_mode_failure(self):
        """Test strict mode raises error when limit cannot be set."""
        # Try to set an invalid limit with strict mode
        with patch("resource.setrlimit", side_effect=OSError("Cannot set limit")):
            with pytest.raises(SandboxExecutionError, match="Cannot enforce memory limit"):
                with memory_limit(50, strict=True):
                    pass

    def test_memory_limit_non_strict_mode_failure(self):
        """Test non-strict mode continues when limit cannot be set."""
        with patch("resource.setrlimit", side_effect=OSError("Cannot set limit")):
            # Should not raise in non-strict mode
            with memory_limit(50, strict=False):
                x = 42

            assert x == 42


class TestContainerDetection:
    """Test container environment detection."""

    def test_is_running_in_container_dockerenv(self):
        """Test detection via .dockerenv file."""
        with patch("pathlib.Path.exists", return_value=True):
            assert _is_running_in_container() is True

    def test_is_running_in_container_env_vars(self):
        """Test detection via environment variables."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict("os.environ", {"DOCKER_CONTAINER": "true"}):
                assert _is_running_in_container() is True

    @pytest.mark.skip(reason="Complex mocking of Path.exists - tested via integration")
    def test_is_running_in_container_cgroup(self):
        """Test detection via cgroup file."""
        with patch("pathlib.Path.exists") as mock_exists:

            def exists_side_effect(self):
                # Return True only for /proc/1/cgroup path
                return str(self) == "/proc/1/cgroup"

            mock_exists.side_effect = exists_side_effect

            with patch.dict("os.environ", {}, clear=True):  # Clear env vars
                with patch("pathlib.Path.open", create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value.read.return_value = "docker"
                    mock_open.return_value = mock_file
                    assert _is_running_in_container() is True

    def test_is_running_in_container_not_in_container(self):
        """Test detection when not in container."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict("os.environ", {}, clear=True):
                assert _is_running_in_container() is False

    @pytest.mark.skipif(platform.system() == "Windows", reason="Skip on Windows")
    def test_is_running_in_container_windows(self):
        """Test detection returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert _is_running_in_container() is False


class TestExecuteProgrammableRule:
    """Test the main execute_programmable_rule function."""

    def test_execute_simple_script(self):
        """Test executing a simple grading script."""
        script = """
points_awarded = 10.0
feedback = "Correct answer!"
"""
        student_answers = {"Q1": "Paris"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="Paris"
        )

        assert points == 10.0
        assert feedback == "Correct answer!"

    def test_execute_script_with_logic(self):
        """Test executing script with conditional logic."""
        script = """
if answer.lower() == 'paris':
    points_awarded = 10.0
    feedback = "Correct!"
else:
    points_awarded = 0.0
    feedback = "Incorrect"
"""
        student_answers = {"Q1": "Paris"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="Paris"
        )

        assert points == 10.0
        assert feedback == "Correct!"

    def test_execute_script_access_all_answers(self):
        """Test script can access all student answers."""
        script = """
if student_answers['Q1'] == 'Paris' and student_answers['Q2'] == '9.8':
    points_awarded = 5.0
    feedback = "Both answers considered"
else:
    points_awarded = 0.0
    feedback = "Not both correct"
"""
        student_answers = {"Q1": "Paris", "Q2": "9.8"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="Paris"
        )

        assert points == 5.0
        assert feedback == "Both answers considered"

    def test_execute_script_with_math(self):
        """Test script can perform mathematical operations."""
        script = """
try:
    numeric_answer = float(answer)
    if abs(numeric_answer - 9.81) <= 0.1:
        points_awarded = 10.0
        feedback = "Within tolerance"
    else:
        points_awarded = 0.0
        feedback = f"Too far from 9.81: {numeric_answer}"
except ValueError:
    points_awarded = 0.0
    feedback = "Not a number"
"""
        student_answers = {"Q2": "9.8"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q2", answer="9.8"
        )

        assert points == 10.0
        assert feedback == "Within tolerance"

    def test_execute_script_timeout(self):
        """Test script execution timeout."""
        script = """
while True:
    pass
"""
        student_answers = {"Q1": "Paris"}

        with pytest.raises(SandboxTimeoutError, match="timed out"):
            execute_programmable_rule(
                script=script,
                student_answers=student_answers,
                question_id="Q1",
                answer="Paris",
                timeout_ms=100,
            )

    def test_execute_script_compilation_error(self):
        """Test script with compilation errors."""
        script = """
if True
    points_awarded = 5.0
"""
        student_answers = {"Q1": "Paris"}

        with pytest.raises(SandboxExecutionError, match="syntax errors"):
            execute_programmable_rule(
                script=script, student_answers=student_answers, question_id="Q1", answer="Paris"
            )

    def test_execute_script_runtime_error(self):
        """Test script with runtime errors."""
        script = """
x = 1 / 0  # Division by zero
points_awarded = 5.0
"""
        student_answers = {"Q1": "Paris"}

        with pytest.raises(SandboxExecutionError, match="execution failed"):
            execute_programmable_rule(
                script=script, student_answers=student_answers, question_id="Q1", answer="Paris"
            )

    def test_execute_script_restricted_builtins(self):
        """Test that dangerous builtins are not available."""
        script = """
# Try to use dangerous operations
try:
    f = open('/etc/passwd', 'r')
    points_awarded = 0.0
    feedback = "File access should fail"
except NameError:
    points_awarded = 10.0
    feedback = "File access blocked"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 10.0
        assert "blocked" in feedback

    def test_execute_script_no_import(self):
        """Test that imports are restricted."""
        script = """
try:
    import os
    points_awarded = 0.0
    feedback = "Import should fail"
except ImportError:
    points_awarded = 10.0
    feedback = "Import blocked"
"""
        student_answers = {"Q1": "test"}

        # Import is blocked, so the except clause should execute
        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 10.0
        assert "blocked" in feedback.lower()

    def test_execute_script_custom_timeout(self):
        """Test custom timeout parameter."""
        script = """
points_awarded = 5.0
feedback = "Completed"
"""
        student_answers = {"Q1": "test"}

        # Should work with a reasonable timeout
        points, feedback = execute_programmable_rule(
            script=script,
            student_answers=student_answers,
            question_id="Q1",
            answer="test",
            timeout_ms=10000,  # 10 seconds
        )

        assert points == 5.0
        assert feedback == "Completed"

    def test_execute_script_custom_memory_limit(self):
        """Test custom memory limit parameter."""
        script = """
points_awarded = 5.0
feedback = "Within memory limit"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script,
            student_answers=student_answers,
            question_id="Q1",
            answer="test",
            memory_mb=100,
        )

        assert points == 5.0

    def test_execute_script_invalid_timeout(self):
        """Test invalid timeout value."""
        script = "points_awarded = 5.0"
        student_answers = {"Q1": "test"}

        with pytest.raises(ValueError, match="timeout_ms must be positive"):
            execute_programmable_rule(
                script=script,
                student_answers=student_answers,
                question_id="Q1",
                answer="test",
                timeout_ms=0,
            )

    def test_execute_script_invalid_memory(self):
        """Test invalid memory limit value."""
        script = "points_awarded = 5.0"
        student_answers = {"Q1": "test"}

        with pytest.raises(ValueError, match="memory_mb must be positive"):
            execute_programmable_rule(
                script=script,
                student_answers=student_answers,
                question_id="Q1",
                answer="test",
                memory_mb=-10,
            )

    def test_execute_script_negative_points_clamped(self):
        """Test that negative points are clamped to zero."""
        script = """
points_awarded = -5.0
feedback = "Negative points"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 0.0
        assert "Invalid negative points" in feedback

    def test_execute_script_partial_credit(self):
        """Test script awarding partial credit."""
        script = """
words = answer.split()
if len(words) >= 3:
    points_awarded = 10.0
    feedback = "Full credit"
elif len(words) >= 1:
    points_awarded = 5.0
    feedback = "Partial credit"
else:
    points_awarded = 0.0
    feedback = "No credit"
"""
        student_answers = {"Q1": "short answer"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="short answer"
        )

        assert points == 5.0
        assert feedback == "Partial credit"

    def test_execute_script_string_operations(self):
        """Test script using string operations."""
        script = """
if 'key phrase' in answer.lower():
    points_awarded = 10.0
    feedback = "Contains key phrase"
else:
    points_awarded = 0.0
    feedback = "Missing key phrase"
"""
        student_answers = {"Q1": "The KEY PHRASE is important"}

        points, feedback = execute_programmable_rule(
            script=script,
            student_answers=student_answers,
            question_id="Q1",
            answer="The KEY PHRASE is important",
        )

        assert points == 10.0
        assert feedback == "Contains key phrase"

    @patch("gradeflow_engine.sandbox._is_running_in_container", return_value=True)
    def test_execute_script_in_container(self, mock_container):
        """Test execution in container skips memory limits."""
        script = """
points_awarded = 5.0
feedback = "Running in container"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 5.0
        assert feedback == "Running in container"

    @patch("gradeflow_engine.sandbox._is_running_in_container", return_value=False)
    def test_execute_script_not_in_container(self, mock_container):
        """Test execution outside container uses memory limits."""
        script = """
points_awarded = 7.5
feedback = "Not in container"
"""
        student_answers = {"Q1": "test"}

        try:
            points, feedback = execute_programmable_rule(
                script=script, student_answers=student_answers, question_id="Q1", answer="test"
            )

            assert points == 7.5
            assert feedback == "Not in container"
        except SandboxExecutionError:
            # May fail if memory limits cannot be set
            pytest.skip("Cannot set memory limits in this environment")


class TestSandboxEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_execute_empty_answer(self):
        """Test script with empty answer."""
        script = """
if answer == "":
    points_awarded = 0.0
    feedback = "Empty answer"
else:
    points_awarded = 10.0
    feedback = "Has answer"
"""
        student_answers = {"Q1": ""}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer=""
        )

        assert points == 0.0
        assert feedback == "Empty answer"

    def test_execute_unicode_content(self):
        """Test script with Unicode content."""
        script = """
if "café" in answer:
    points_awarded = 10.0
    feedback = "Found café ☕"
else:
    points_awarded = 0.0
    feedback = "No café 😞"
"""
        student_answers = {"Q1": "I like café"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="I like café"
        )

        assert points == 10.0
        assert "café" in feedback

    def test_execute_multiline_feedback(self):
        """Test script setting multiline feedback."""
        script = """
points_awarded = 8.0
feedback = '''Line 1
Line 2
Line 3'''
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 8.0
        assert "Line 1" in feedback
        assert "Line 2" in feedback
        assert "Line 3" in feedback

    def test_execute_very_small_timeout(self):
        """Test with very small timeout."""
        script = """
# Infinite loop to trigger timeout
while True:
    x = 1 + 1
"""
        student_answers = {"Q1": "test"}

        # Small timeout should cause timeout
        with pytest.raises(SandboxTimeoutError):
            execute_programmable_rule(
                script=script,
                student_answers=student_answers,
                question_id="Q1",
                answer="test",
                timeout_ms=100,  # 100ms
            )

    def test_execute_default_parameters(self):
        """Test execution with default timeout and memory parameters."""
        script = """
points_awarded = 6.0
feedback = "Using defaults"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script,
            student_answers=student_answers,
            question_id="Q1",
            answer="test",
            # Using default timeout_ms and memory_mb
        )

        assert points == 6.0
        assert feedback == "Using defaults"

    def test_execute_script_with_comments(self):
        """Test script with comments."""
        script = """
# This is a comment
points_awarded = 9.0  # Inline comment
# Another comment
feedback = "Script with comments"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 9.0
        assert feedback == "Script with comments"


class TestSandboxSecurity:
    """Test security restrictions of the sandbox."""

    def test_no_file_system_access(self):
        """Test that file system access is blocked."""
        script = """
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    points_awarded = 0.0
    feedback = "Should not reach here"
except (NameError, AttributeError):
    points_awarded = 10.0
    feedback = "File access blocked"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 10.0
        assert "blocked" in feedback

    def test_no_subprocess_access(self):
        """Test that subprocess execution is blocked."""
        script = """
try:
    import subprocess
    subprocess.run(['ls'])
    points_awarded = 0.0
    feedback = "Subprocess should be blocked"
except (NameError, ImportError):
    points_awarded = 10.0
    feedback = "Subprocess blocked"
"""
        student_answers = {"Q1": "test"}

        # Import is blocked, so subprocess is also blocked
        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 10.0
        assert "blocked" in feedback.lower()

    def test_no_eval_access(self):
        """Test that eval/exec are restricted."""
        script = """
try:
    eval("print('hello')")
    points_awarded = 0.0
except NameError:
    points_awarded = 10.0
    feedback = "eval blocked"
"""
        student_answers = {"Q1": "test"}

        # eval() is caught at compilation time by RestrictedPython
        with pytest.raises(SandboxExecutionError, match="Eval calls are not allowed"):
            execute_programmable_rule(
                script=script, student_answers=student_answers, question_id="Q1", answer="test"
            )

    def test_safe_builtins_available(self):
        """Test that safe builtins are available."""
        script = """
# These should all work
x = len("hello")
y = int("42")
z = float("3.14")
s = str(123)
r = range(5)
tup = tuple(r)

points_awarded = 10.0 if x == 5 else 0.0
feedback = f"len={x}, int={y}, float={z}, str={s}, range={r}, tuple={tup}"
"""
        student_answers = {"Q1": "test"}

        points, feedback = execute_programmable_rule(
            script=script, student_answers=student_answers, question_id="Q1", answer="test"
        )

        assert points == 10.0
        assert "len=5" in feedback
