from pathlib import Path

from morpher.fonts import FontFace, FontRegistry, FontRequest, FontSource, resolve_font


def _face(weight: int, style: str = "normal", flavor: str | None = None) -> FontFace:
    return FontFace(
        family="HK Grotesk",
        weight=weight,
        style=style,
        flavor=flavor,
        sources=(FontSource(Path(f"HK-{weight}-{style}-{flavor or 'modern'}.woff2"), "woff2"),),
    )


def test_resolve_exact_face() -> None:
    registry = FontRegistry(faces=(_face(400), _face(700)))

    result = resolve_font(registry, FontRequest("HK Grotesk", 700, "normal"))

    assert result.status == "exact"
    assert result.face == _face(700)
    assert result.reason is None


def test_resolve_family_case_insensitively() -> None:
    registry = FontRegistry(faces=(_face(700),))

    result = resolve_font(registry, FontRequest("hk grotesk", 700, "normal"))

    assert result.status == "exact"


def test_resolve_nearest_weight_as_fallback() -> None:
    registry = FontRegistry(faces=(_face(400), _face(700)))

    result = resolve_font(registry, FontRequest("HK Grotesk", 600, "normal"))

    assert result.status == "fallback"
    assert result.face == _face(700)
    assert "requested face unavailable" in (result.reason or "")


def test_resolve_prefers_requested_style_before_nearest_weight() -> None:
    registry = FontRegistry(faces=(_face(400, "italic"), _face(700, "normal")))

    result = resolve_font(registry, FontRequest("HK Grotesk", 400, "normal"))

    assert result.status == "fallback"
    assert result.face == _face(700, "normal")


def test_resolve_prefers_non_legacy_face_by_default() -> None:
    registry = FontRegistry(faces=(_face(700, flavor="legacy"), _face(400)))

    result = resolve_font(registry, FontRequest("HK Grotesk", 700, "normal"))

    assert result.status == "fallback"
    assert result.face == _face(400)


def test_resolve_explicit_legacy_flavor() -> None:
    registry = FontRegistry(faces=(_face(700), _face(700, flavor="legacy")))

    result = resolve_font(registry, FontRequest("HK Grotesk", 700, "normal", "legacy"))

    assert result.status == "exact"
    assert result.face == _face(700, flavor="legacy")


def test_resolve_missing_family_does_not_choose_random_face() -> None:
    registry = FontRegistry(faces=(_face(700),))

    result = resolve_font(registry, FontRequest("Does Not Exist", 700, "normal"))

    assert result.status == "missing"
    assert result.face is None
    assert result.reason == "font family not found in registry"
