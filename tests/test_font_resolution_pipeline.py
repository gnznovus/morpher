from pathlib import Path

from morpher.fonts import (
    FontFace,
    FontMetadata,
    FontRegistry,
    FontSource,
    font_request_from_intent,
    resolve_font_intent,
    resolve_font_with_cache,
    save_font_registry_cache,
    set_current_font_registry,
)
from morpher.fonts.resolver import FontRequest
from morpher.ir.typography import FontIntent


def _face(weight: int, *, style: str = "normal", flavor: str | None = None) -> FontFace:
    return FontFace(
        family="HK Grotesk",
        weight=weight,
        style=style,
        flavor=flavor,
        sources=(FontSource(Path(f"HK-{weight}-{style}-{flavor or 'modern'}.woff2"), "woff2"),),
    )


def test_converts_design_ir_font_intent_to_request() -> None:
    intent = FontIntent(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
        postscript_name="HKGrotesk-BoldLegacy",
        source_style="Bold Legacy",
    )

    request = font_request_from_intent(intent)

    assert request == FontRequest("HK Grotesk", 700, "normal", "legacy")


def test_exact_cache_hit_does_not_refresh(tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    cache_path = root / "font-registry.json"
    registry = FontRegistry(faces=(_face(700, flavor="legacy"),))
    save_font_registry_cache(cache_path, registry)
    set_current_font_registry(FontRegistry())

    calls = 0

    def metadata_reader(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        raise AssertionError("gatherer should not run on an exact cache hit")

    result = resolve_font_with_cache(
        root,
        cache_path,
        FontRequest("HK Grotesk", 700, "normal", "legacy"),
        metadata_reader=metadata_reader,
    )

    assert result.status == "exact"
    assert result.provenance == "cache_hit"
    assert calls == 0


def test_cache_miss_refreshes_once_and_finds_exact_face(tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    root.mkdir()
    font_path = root / "HKGrotesk-BoldLegacy.woff2"
    font_path.write_bytes(b"")
    cache_path = root / "font-registry.json"
    set_current_font_registry(FontRegistry())

    calls = 0

    def metadata_reader(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        assert path == font_path
        return FontMetadata(
            family="HK Grotesk",
            subfamily="Bold Legacy",
            weight=700,
            style="normal",
            flavor="legacy",
        )

    intent = FontIntent(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
    )
    result = resolve_font_intent(
        root,
        cache_path,
        intent,
        metadata_reader=metadata_reader,
    )

    assert result.status == "exact"
    assert result.provenance == "resolved_after_refresh"
    assert result.face is not None
    assert result.face.flavor == "legacy"
    assert calls == 1
    assert cache_path.exists()


def test_refresh_then_uses_deterministic_fallback(tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    root.mkdir()
    font_path = root / "HKGrotesk-Bold.woff2"
    font_path.write_bytes(b"")
    cache_path = root / "font-registry.json"
    set_current_font_registry(FontRegistry())

    calls = 0

    def metadata_reader(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        return FontMetadata(
            family="HK Grotesk",
            subfamily="Bold",
            weight=700,
            style="normal",
        )

    result = resolve_font_with_cache(
        root,
        cache_path,
        FontRequest("HK Grotesk", 600, "normal"),
        metadata_reader=metadata_reader,
    )

    assert result.status == "fallback"
    assert result.provenance == "fallback_after_refresh"
    assert result.face is not None
    assert result.face.weight == 700
    assert calls == 1


def test_refresh_then_reports_missing_family(tmp_path: Path) -> None:
    root = tmp_path / "fonts"
    root.mkdir()
    cache_path = root / "font-registry.json"
    set_current_font_registry(FontRegistry())

    result = resolve_font_with_cache(
        root,
        cache_path,
        FontRequest("Not Existed Font", 700, "normal"),
    )

    assert result.status == "missing"
    assert result.provenance == "missing_after_refresh"
    assert result.face is None
    assert cache_path.exists()
