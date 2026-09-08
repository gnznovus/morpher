from pathlib import Path
from typing import Protocol


class InputAdapter(Protocol):
    """Contract for source-format adapters."""

    extensions: tuple[str, ...]

    def supports(self, path: Path) -> bool: ...

    def load(self, path: Path): ...
