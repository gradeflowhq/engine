from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """
    A simple string-keyed registry for pluggable components (e.g., loaders/savers).

    Features:
    - Register callable or object under a unique name
    - Retrieve by name
    - List available keys
    - Unregister entries
    - Optional decorator-based registration

    Example:
        question_set_loaders.register("yaml", load_question_set_yaml)
        loader = question_set_loaders.get("yaml")
        qs = loader(yaml_str)
    """

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T, *, overwrite: bool = False) -> None:
        """
        Register an item under a given name.

        Args:
            name: Unique name for the item.
            item: The object or callable to register.
            overwrite: If False, raises KeyError when name already exists.
        """
        if not overwrite and name in self._items:
            raise KeyError(f"{self._kind} '{name}' is already registered")
        self._items[name] = item

    def unregister(self, name: str) -> None:
        """Remove an item from the registry. Raises KeyError if not found."""
        if name not in self._items:
            raise KeyError(f"{self._kind} '{name}' is not registered")
        del self._items[name]

    def get(self, name: str) -> T:
        """Retrieve a registered item by name. Raises KeyError if not found."""
        try:
            return self._items[name]
        except KeyError as e:
            available = ", ".join(sorted(self._items.keys())) or "<none>"
            raise KeyError(
                f"{self._kind} '{name}' not found. Available {self._kind}s: {available}"
            ) from e

    def try_get(self, name: str) -> T | None:
        """Retrieve a registered item by name, returning None if not found."""
        return self._items.get(name)

    def keys(self) -> Iterable[str]:
        """Return an iterable of registered names."""
        return self._items.keys()

    def items(self) -> Iterable[tuple[str, T]]:
        """Return an iterable of (name, item) pairs."""
        return self._items.items()

    def available(self) -> list[str]:
        """Return a sorted list of available names."""
        return sorted(self._items.keys())

    def register_decorator(self, name: str, *, overwrite: bool = False) -> Callable[[T], T]:
        """
        Decorator to register a function/class under a name.

        Usage:
            @question_set_loaders.register_decorator("yaml")
            def load_qs(...): ...
        """

        def _wrap(item: T) -> T:
            self.register(name, item, overwrite=overwrite)
            return item

        return _wrap


# Registries for different component types
if TYPE_CHECKING:
    from .question_sets.loaders import BaseQuestionSetLoader
    from .question_sets.savers import BaseQuestionSetSaver
    from .rubrics.loaders import BaseRubricLoader
    from .submissions.loaders import BaseSubmissionsLoader
    from .submissions.savers import BaseSubmissionsSaver

question_set_loader_registry: Registry[type["BaseQuestionSetLoader"]] = Registry(
    "question_set_loader_registry"
)
question_set_saver_registry: Registry[type["BaseQuestionSetSaver"]] = Registry(
    "question_set_saver_registry"
)
rubric_loader_registry: Registry[type["BaseRubricLoader"]] = Registry("rubric_loader_registry")
submissions_loader_registry: Registry[type["BaseSubmissionsLoader"]] = Registry(
    "submissions_loader_registry"
)
submissions_saver_registry: Registry[type["BaseSubmissionsSaver"]] = Registry(
    "submissions_saver_registry"
)


# Public API
__all__ = [
    "Registry",
    "question_set_loader_registry",
    "question_set_saver_registry",
    "rubric_loader_registry",
    "submissions_loader_registry",
    "submissions_saver_registry",
]
