from __future__ import annotations

from pathlib import Path

from morpher.fonts.registry import FontRegistry, gather_fonts
from morpher.storage.paths import StoragePaths


def format_registry(registry: FontRegistry, *, root: Path) -> str:
    lines = [
        "MORPHER FONT REGISTRY",
        f"ROOT: {root}",
        f"FAMILIES: {len(registry.families())}",
        f"FACES: {len(registry.faces)}",
        f"SOURCES: {registry.source_count}",
        f"UNRESOLVED: {len(registry.unresolved_sources)}",
        "",
    ]

    for family in registry.families():
        lines.append(f"[{family}]")
        family_faces = [face for face in registry.faces if face.family == family]
        for face in family_faces:
            flavor = f" flavor={face.flavor}" if face.flavor else ""
            lines.append(
                f"  weight={face.weight} style={face.style}{flavor}"
            )
            for source in face.web_sources():
                lines.append(f"    - {source.format}: {source.path}")
        lines.append("")

    if registry.unresolved_sources:
        lines.append("[UNRESOLVED]")
        for unresolved in registry.unresolved_sources:
            lines.append(
                f"  - {unresolved.source.path}: {unresolved.error or 'metadata unavailable'}"
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    storage = StoragePaths()
    storage.ensure()
    registry = gather_fonts(storage.fonts)
    print(format_registry(registry, root=storage.fonts), end="")


if __name__ == "__main__":
    main()
