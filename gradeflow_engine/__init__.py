from . import adapters as adapters
from . import serializations as serializations


def register_builtins() -> None:
    adapters.register_builtins()
    serializations.register_builtins()


register_builtins()
