from pathlib import Path
from collections.abc import Iterable


def scan_sources(paths: Iterable[Path], supported_extensions: tuple[str, ...]) -> list[Path]:
    """Return supported files in source-priority order."""
    supported = {ext.lower() for ext in supported_extensions}
    found: list[Path] = []

    for root in paths:
        if not root.exists():
            continue
        found.extend(
            sorted(
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.lower() in supported
            )
        )

    return found
