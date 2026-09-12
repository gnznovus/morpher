from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


WEB_FORMAT_PRIORITY = {
    "woff2": 0,
    "woff": 1,
    "otf": 2,
    "ttf": 3,
    "eot": 4,
}


@dataclass(frozen=True)
class FontSource:
    path: Path
    format: str


@dataclass(frozen=True)
class FontFace:
    family: str
    weight: int
    style: str
    flavor: str | None
    sources: tuple[FontSource, ...]

    @property
    def key(self) -> tuple[str, int, str, str | None]:
        return (self.family.casefold(), self.weight, self.style, self.flavor)

    def web_sources(self) -> tuple[FontSource, ...]:
        return tuple(
            sorted(
                self.sources,
                key=lambda source: (
                    WEB_FORMAT_PRIORITY.get(source.format, 99),
                    str(source.path).casefold(),
                ),
            )
        )


@dataclass(frozen=True)
class FontMetadata:
    family: str
    subfamily: str
    weight: int
    style: str
    flavor: str | None = None


@dataclass(frozen=True)
class UnresolvedFontSource:
    source: FontSource
    error: str
