from pathlib import Path

from morpher.fonts.metadata import _infer_flavor, _normalize_words


def test_normalize_words_splits_compact_variant_names() -> None:
    assert _normalize_words("BoldLegacyItalic") == ["bold", "legacy", "italic"]


def test_infer_flavor_preserves_legacy_variant_from_subfamily() -> None:
    assert _infer_flavor("Bold Legacy Italic", Path("HKGrotesk-BoldLegacyItalic.woff2")) == "legacy"


def test_infer_flavor_preserves_legacy_variant_from_filename() -> None:
    assert _infer_flavor("Bold Italic", Path("HKGrotesk-BoldLegacyItalic.woff2")) == "legacy"


def test_standard_weight_and_style_have_no_flavor() -> None:
    assert _infer_flavor("Bold Italic", Path("HKGrotesk-BoldItalic.woff2")) is None
