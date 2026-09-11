from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from morpher.fonts.metadata import read_font_metadata
from morpher.fonts.model import FontFace, FontMetadata, FontSource, UnresolvedFontSource


SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".eot"}
MetadataReader = Callable[[Path], FontMetadata]
FaceKey = tuple[str, int, str, str | None]


def _source(path: Path) -> FontSource:
    return FontSource(path=path, format=path.suffix.lower().lstrip("."))


def _face_key(metadata: FontMetadata) -> FaceKey:
    flavor = metadata.flavor.casefold() if metadata.flavor else None
    return (metadata.family.casefold(), metadata.weight, metadata.style, flavor)


def _stem_key(path: Path) -> str:
    return path.stem.casefold()


@dataclass(frozen=True)
class FontRegistry:
    faces: tuple[FontFace, ...] = ()
    unresolved_sources: tuple[UnresolvedFontSource, ...] = ()

    @property
    def source_count(self) -> int:
        return sum(len(face.sources) for face in self.faces) + len(self.unresolved_sources)

    def families(self) -> tuple[str, ...]:
        return tuple(sorted({face.family for face in self.faces}, key=str.casefold))


_CURRENT_REGISTRY = FontRegistry()


def gather_fonts(
    root: Path,
    *,
    metadata_reader: MetadataReader = read_font_metadata,
) -> FontRegistry:
    if not root.exists():
        return FontRegistry()

    paths = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_FONT_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )

    grouped: dict[FaceKey, list[FontSource]] = defaultdict(list)
    metadata_by_key: dict[FaceKey, FontMetadata] = {}
    stem_to_key: dict[str, FaceKey] = {}
    failed: list[tuple[FontSource, str]] = []

    for path in paths:
        source = _source(path)
        try:
            metadata = metadata_reader(path)
        except Exception as exc:  # One unreadable font must not abort the whole gather pass.
            failed.append((source, str(exc)))
            continue

        key = _face_key(metadata)
        grouped[key].append(source)
        metadata_by_key.setdefault(key, metadata)
        stem_to_key.setdefault(_stem_key(path), key)

    unresolved: list[UnresolvedFontSource] = []
    for source, error in failed:
        sibling_key = stem_to_key.get(_stem_key(source.path))
        if sibling_key is not None:
            grouped[sibling_key].append(source)
            continue
        unresolved.append(UnresolvedFontSource(source=source, error=error))

    faces: list[FontFace] = []
    for key, sources in grouped.items():
        metadata = metadata_by_key[key]
        ordered_sources = tuple(sorted(sources, key=lambda item: str(item.path).casefold()))
        faces.append(
            FontFace(
                family=metadata.family,
                weight=metadata.weight,
                style=metadata.style,
                flavor=metadata.flavor.casefold() if metadata.flavor else None,
                sources=ordered_sources,
            )
        )

    faces.sort(
        key=lambda face: (
            face.family.casefold(),
            face.weight,
            face.style,
            face.flavor or "",
        )
    )
    unresolved.sort(key=lambda item: str(item.source.path).casefold())
    return FontRegistry(faces=tuple(faces), unresolved_sources=tuple(unresolved))


def refresh_font_registry(
    root: Path,
    *,
    metadata_reader: MetadataReader = read_font_metadata,
) -> FontRegistry:
    global _CURRENT_REGISTRY
    _CURRENT_REGISTRY = gather_fonts(root, metadata_reader=metadata_reader)
    return _CURRENT_REGISTRY


def current_font_registry() -> FontRegistry:
    return _CURRENT_REGISTRY
