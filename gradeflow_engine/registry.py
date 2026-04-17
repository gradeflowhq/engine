from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[str, T] = {}

    def _normalize(self, name: str) -> str:
        return name.strip().lower()

    def register(self, name: str, item: T, *, overwrite: bool = False) -> None:
        key = self._normalize(name)
        if not overwrite and key in self._items:
            raise KeyError(f"{self._kind} '{key}' is already registered")
        self._items[key] = item

    def unregister(self, name: str) -> None:
        key = self._normalize(name)
        if key not in self._items:
            raise KeyError(f"{self._kind} '{key}' is not registered")
        del self._items[key]

    def get(self, name: str) -> T:
        key = self._normalize(name)
        if key not in self._items:
            available = sorted(self._items.keys())
            raise KeyError(
                f"{self._kind} '{key}' not found. Available: {', '.join(available) or '<none>'}"
            )
        return self._items[key]

    def try_get(self, name: str) -> T | None:
        return self._items.get(self._normalize(name))

    def available(self) -> list[str]:
        return sorted(self._items.keys())

    def register_decorator(self, name: str, *, overwrite: bool = False):
        def _wrap(item: T) -> T:
            self.register(name, item, overwrite=overwrite)
            return item

        return _wrap
