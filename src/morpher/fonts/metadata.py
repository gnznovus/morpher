from __future__ import annotations

import re
from pathlib import Path

from fontTools.ttLib import TTFont

from morpher.fonts.model import FontMetadata


_WEIGHT_WORDS = {
    "thin",
    "extralight",
    "ultralight",
    "light",
    "regular",
    "normal",
    "book",
    "medium",
    "semibold",
    "demibold",
    "bold",
    "extrabold",
    "ultrabold",
    "black",
    "heavy",
}
_STYLE_WORDS = {"italic", "oblique"}


def _name_value(font: TTFont, *name_ids: int) -> str | None:
    name_table = font["name"]
    for name_id in name_ids:
        records = [record for record in name_table.names if record.nameID == name_id]
        for record in records:
            try:
                value = record.toUnicode().strip()
            except (UnicodeDecodeError, AttributeError):
                continue
            if value:
                return value
    return None


def _normalize_words(value: str) -> list[str]:
    # Font packages often use compact names such as BoldLegacyItalic.
    # Split lower→upper boundaries before tokenizing so variant words survive.
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return [word.casefold() for word in re.findall(r"[A-Za-z0-9]+", expanded)]


def _infer_flavor(subfamily: str, path: Path) -> str | None:
    words = _normalize_words(subfamily)
    extras = [word for word in words if word not in _WEIGHT_WORDS and word not in _STYLE_WORDS]
    if extras:
        return "-".join(extras)

    # Some packages encode compatibility variants in filenames even when the
    # internal subfamily name is identical. Preserve the known variant rather
    # than grouping it into the normal face accidentally.
    stem_words = _normalize_words(path.stem)
    if "legacy" in stem_words:
        return "legacy"
    return None


def read_font_metadata(path: Path) -> FontMetadata:
    font = TTFont(path, lazy=True)
    try:
        # Prefer typographic family/subfamily names when supplied, then fall
        # back to the older family/subfamily records.
        family = _name_value(font, 16, 1)
        subfamily = _name_value(font, 17, 2) or "Regular"
        if not family:
            raise ValueError("font has no readable family name")

        os2 = font.get("OS/2")
        weight = int(getattr(os2, "usWeightClass", 400) or 400)

        words = set(_normalize_words(subfamily))
        italic = bool(words & _STYLE_WORDS)
        if os2 is not None:
            italic = italic or bool(getattr(os2, "fsSelection", 0) & 0x01)
        head = font.get("head")
        if head is not None:
            italic = italic or bool(getattr(head, "macStyle", 0) & 0x02)

        style = "italic" if italic else "normal"
        flavor = _infer_flavor(subfamily, path)
        return FontMetadata(
            family=family,
            subfamily=subfamily,
            weight=weight,
            style=style,
            flavor=flavor,
        )
    finally:
        font.close()
