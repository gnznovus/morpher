from morpher.ir.typography import FontIntent, normalize_font_intent


def test_normalizes_figma_legacy_variant_to_font_intent():
    intent = normalize_font_intent(
        family="HK Grotesk",
        weight=700,
        source_style="Bold Legacy",
        postscript_name="HKGrotesk-BoldLegacy",
    )

    assert intent == FontIntent(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
        postscript_name="HKGrotesk-BoldLegacy",
        source_style="Bold Legacy",
    )


def test_normalizes_compact_italic_variant():
    intent = normalize_font_intent(
        family="HK Grotesk",
        weight=700,
        source_style="BoldLegacyItalic",
        postscript_name="HKGrotesk-BoldLegacyItalic",
    )

    assert intent is not None
    assert intent.style == "italic"
    assert intent.flavor == "legacy"


def test_standard_weight_name_is_not_treated_as_flavor():
    intent = normalize_font_intent(
        family="HK Grotesk",
        weight=500,
        source_style="Medium",
        postscript_name="HKGrotesk-Medium",
    )

    assert intent is not None
    assert intent.style == "normal"
    assert intent.flavor is None


def test_font_intent_requires_family_and_weight():
    assert normalize_font_intent(family=None, weight=700, source_style="Bold") is None
    assert normalize_font_intent(family="HK Grotesk", weight=None, source_style="Bold") is None
