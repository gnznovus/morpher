from pathlib import Path

from .base import InputAdapter


class InputRegistry:
    """Resolve source files to registered input adapters."""

    def __init__(self) -> None:
        self._adapters: list[InputAdapter] = []

    def register(self, adapter: InputAdapter) -> None:
        self._adapters.append(adapter)

    @property
    def extensions(self) -> tuple[str, ...]:
        values = {ext.lower() for adapter in self._adapters for ext in adapter.extensions}
        return tuple(sorted(values))

    def resolve(self, path: Path) -> InputAdapter | None:
        for adapter in self._adapters:
            if adapter.supports(path):
                return adapter
        return None
