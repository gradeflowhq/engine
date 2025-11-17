import signal
from contextlib import contextmanager


class TimeoutError(Exception):
    pass


@contextmanager
def time_limit(timeout_s: int):
    if timeout_s <= 0:
        raise ValueError(f"timeout_s must be positive, got {timeout_s}")

    def _timeout_handler(signum: int, frame) -> None:
        """Signal handler for execution timeout."""
        raise TimeoutError("Script execution timed out")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_s)

    try:
        yield
    finally:
        # Restore signal handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
