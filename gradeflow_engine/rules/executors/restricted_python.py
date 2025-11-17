from typing import Any

from RestrictedPython import (
    compile_restricted,  # type: ignore[import]
    limited_builtins,  # type: ignore[import]
    safe_builtins,  # type: ignore[import]
    utility_builtins,  # type: ignore[import]
)

from .utils import time_limit as time_limit_context


def safe_exec(
    source_code: str,
    local_variables: dict[str, Any] | None = None,
    memory_limit=1000,
    time_limit=5,
) -> None:
    """
    Execute source_code with RestrictedPython. Mutates local_variables in place.
    """
    # Compile to restricted bytecode
    byte_code = compile_restricted(source_code, filename="<inline code>", mode="exec")

    # Merge the allowed builtins
    allowed_builtins = {
        **safe_builtins,
        **limited_builtins,
        **utility_builtins,
    }

    # Prepare globals and locals
    globals_dict: dict[str, Any] = {"__builtins__": allowed_builtins}
    locals_dict: dict[str, Any] = local_variables if local_variables is not None else {}

    with time_limit_context(time_limit):
        # Execute the restricted code
        exec(byte_code, globals_dict, locals_dict)

    # If the caller provided a dict, it’s already mutated; otherwise nothing to return
    if local_variables is not None:
        # Ensure the caller’s dict reflects any changes
        local_variables.update(locals_dict)
