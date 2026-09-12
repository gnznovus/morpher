from pathlib import Path

from morpher.fonts.model import FontMetadata
from morpher.fonts.registry import current_font_registry, gather_fonts, refresh_font_registry


def _touch(root: Path, name: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"font")
    return path


def test_gather_groups_formats_into_one_logical_face(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    for extension in ("woff2", "woff", "eot"):
        _touch(fonts, f"HKGrotesk-Bold.{extension}")

    def metadata_reader(path: Path) -> FontMetadata:
        if path.suffix == ".eot":
            raise ValueError("EOT parser unavailable")
        return FontMetadata(
            family="HK Grotesk",
            subfamily="Bold",
            weight=700,
            style="normal",
        )

    registry = gather_fonts(fonts, metadata_reader=metadata_reader)

    assert registry.source_count == 3
    assert len(registry.faces) == 1
    assert registry.unresolved_sources == ()
    face = registry.faces[0]
    assert face.family == "HK Grotesk"
    assert face.weight == 700
    assert face.style == "normal"
    assert [source.format for source in face.web_sources()] == ["woff2", "woff", "eot"]


def test_gather_keeps_legacy_variant_as_separate_face(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    _touch(fonts, "HKGrotesk-Bold.woff2")
    _touch(fonts, "HKGrotesk-BoldLegacy.woff2")
    _touch(fonts, "HKGrotesk-BoldLegacy.woff")

    def metadata_reader(path: Path) -> FontMetadata:
        legacy = "legacy" in path.stem.casefold()
        return FontMetadata(
            family="HK Grotesk",
            subfamily="Bold Legacy" if legacy else "Bold",
            weight=700,
            style="normal",
            flavor="legacy" if legacy else None,
        )

    registry = gather_fonts(fonts, metadata_reader=metadata_reader)

    assert len(registry.faces) == 2
    normal = next(face for face in registry.faces if face.flavor is None)
    legacy = next(face for face in registry.faces if face.flavor == "legacy")
    assert [source.format for source in normal.sources] == ["woff2"]
    assert {source.format for source in legacy.sources} == {"woff", "woff2"}


def test_gather_preserves_unreadable_font_as_unresolved(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    broken = _touch(fonts, "MysteryFont.eot")

    def metadata_reader(path: Path) -> FontMetadata:
        raise ValueError("cannot read font metadata")

    registry = gather_fonts(fonts, metadata_reader=metadata_reader)

    assert registry.faces == ()
    assert registry.source_count == 1
    assert len(registry.unresolved_sources) == 1
    assert registry.unresolved_sources[0].source.path == broken


def test_gather_ignores_non_font_files(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    _touch(fonts, "notes.txt")

    registry = gather_fonts(fonts, metadata_reader=lambda path: None)  # type: ignore[arg-type]

    assert registry.source_count == 0
    assert registry.faces == ()


def test_refresh_replaces_current_registry(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    _touch(fonts, "HKGrotesk-Light.woff2")

    def metadata_reader(path: Path) -> FontMetadata:
        return FontMetadata(
            family="HK Grotesk",
            subfamily="Light",
            weight=300,
            style="normal",
        )

    refreshed = refresh_font_registry(fonts, metadata_reader=metadata_reader)

    assert current_font_registry() is refreshed
    assert refreshed.families() == ("HK Grotesk",)
