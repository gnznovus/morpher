from pathlib import Path

from morpher.fonts.cache import load_font_registry_cache
from morpher.fonts.model import FontMetadata
from morpher.fonts.registry import ensure_font_face, refresh_font_registry, set_current_font_registry


def _touch(root: Path, name: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"font")
    return path


def _metadata(path: Path) -> FontMetadata:
    return FontMetadata(
        family="HK Grotesk",
        subfamily="Bold",
        weight=700,
        style="normal",
    )


def test_refresh_persists_registry_cache(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    cache = tmp_path / "font-registry.json"
    source = _touch(fonts, "HKGrotesk-Bold.woff2")

    registry = refresh_font_registry(
        fonts,
        metadata_reader=_metadata,
        cache_path=cache,
    )
    loaded = load_font_registry_cache(cache)

    assert loaded is not None
    assert loaded.families() == ("HK Grotesk",)
    assert loaded.faces[0].sources[0].path == source
    assert loaded.source_count == registry.source_count


def test_ensure_font_face_uses_cache_without_gathering(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    cache = tmp_path / "font-registry.json"
    _touch(fonts, "HKGrotesk-Bold.woff2")

    refresh_font_registry(
        fonts,
        metadata_reader=_metadata,
        cache_path=cache,
    )
    set_current_font_registry(type(load_font_registry_cache(cache))())  # empty in-memory registry

    calls = 0

    def should_not_run(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        raise AssertionError("gatherer should not run on a registry cache hit")

    face, refreshed = ensure_font_face(
        fonts,
        cache,
        family="HK Grotesk",
        weight=700,
        style="normal",
        metadata_reader=should_not_run,
    )

    assert face is not None
    assert face.family == "HK Grotesk"
    assert refreshed is False
    assert calls == 0


def test_ensure_font_face_refreshes_once_after_cache_miss(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    cache = tmp_path / "font-registry.json"
    _touch(fonts, "HKGrotesk-Bold.woff2")
    set_current_font_registry(type(load_font_registry_cache(cache) or refresh_font_registry(tmp_path / "empty"))())

    calls = 0

    def counted_reader(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        return _metadata(path)

    face, refreshed = ensure_font_face(
        fonts,
        cache,
        family="HK Grotesk",
        weight=700,
        style="normal",
        metadata_reader=counted_reader,
    )

    assert face is not None
    assert refreshed is True
    assert calls == 1
    assert cache.exists()


def test_ensure_font_face_stops_after_refresh_when_face_still_missing(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    cache = tmp_path / "font-registry.json"
    _touch(fonts, "HKGrotesk-Bold.woff2")
    set_current_font_registry(type(load_font_registry_cache(cache) or refresh_font_registry(tmp_path / "empty"))())

    calls = 0

    def counted_reader(path: Path) -> FontMetadata:
        nonlocal calls
        calls += 1
        return _metadata(path)

    face, refreshed = ensure_font_face(
        fonts,
        cache,
        family="Font That Does Not Exist",
        weight=700,
        style="normal",
        metadata_reader=counted_reader,
    )

    assert face is None
    assert refreshed is True
    assert calls == 1
