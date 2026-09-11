from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


FontStyle = Literal["normal", "italic"]

_STANDARD_VARIANT_WORDS = {
    "black",
    "bold",
    "book",
    "demibold",
    "extralight",
    "extrabold",
    "hairline",
    "heavy",
    "light",
    "medium",
    "normal",
    "regular",
    "semibold",
    "thin",
}
_STYLE_WORDS = {"italic", "oblique"}


@dataclass(frozen=True)
class FontIntent:
    """Output-agnostic normalized font request carried by Design IR."""

    family: str
    weight: int
    style: FontStyle = "normal"
    flavor: str | None = None
    postscript_name: str | None = None
    source_style: str | None = None


def normalize_font_intent(
    *,
    family: str | None,
    weight: int | None,
    source_style: str | None = None,
    postscript_name: str | None = None,
) -> FontIntent | None:
    """Normalize source typography labels without consulting the font registry."""

    if not family or weight is None:
        return None

    words = _variant_words(source_style)
    style: FontStyle = "italic" if any(word in _STYLE_WORDS for word in words) else "normal"
    flavor_words = [
        word
        for word in words
        if word not in _STYLE_WORDS and word not in _STANDARD_VARIANT_WORDS
    ]
    flavor = " ".join(flavor_words) or None

    return FontIntent(
        family=family,
        weight=weight,
        style=style,
        flavor=flavor,
        postscript_name=postscript_name,
        source_style=source_style,
    )


def _variant_words(value: str | None) -> list[str]:
    if not value:
        return []
    expanded = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return [word.casefold() for word in re.findall(r"[A-Za-z0-9]+", expanded)]
