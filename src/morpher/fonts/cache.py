from __future__ import annotations

import json
from pathlib import Path

from morpher.fonts.model import FontFace, FontSource, UnresolvedFontSource


CACHE_VERSION = 1


def save_font_registry_cache(path: Path, registry: "FontRegistry") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cache_version": CACHE_VERSION,
        "faces": [
            {
                "family": face.family,
                "weight": face.weight,
                "style": face.style,
                "flavor": face.flavor,
                "sources": [
                    {
                        "path": str(source.path),
                        "format": source.format,
                    }
                    for source in face.sources
                ],
            }
            for face in registry.faces
        ],
        "unresolved_sources": [
            {
                "path": str(item.source.path),
                "format": item.source.format,
                "error": item.error,
            }
            for item in registry.unresolved_sources
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_font_registry_cache(path: Path) -> "FontRegistry | None":
    from morpher.fonts.registry import FontRegistry

    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("cache_version") != CACHE_VERSION:
            return None

        faces = tuple(
            FontFace(
                family=item["family"],
                weight=int(item["weight"]),
                style=item["style"],
                flavor=item.get("flavor"),
                sources=tuple(
                    FontSource(path=Path(source["path"]), format=source["format"])
                    for source in item.get("sources", [])
                ),
            )
            for item in payload.get("faces", [])
        )
        unresolved = tuple(
            UnresolvedFontSource(
                source=FontSource(path=Path(item["path"]), format=item["format"]),
                error=item.get("error", ""),
            )
            for item in payload.get("unresolved_sources", [])
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None

    return FontRegistry(faces=faces, unresolved_sources=unresolved)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from morpher.fonts.registry import FontRegistry
