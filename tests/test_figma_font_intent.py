from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.typography import FontIntent


def test_figma_text_carries_normalized_font_intent_into_ir():
    payload = {
        "document": {
            "id": "45:5216",
            "name": "Newsletter",
            "type": "FRAME",
            "children": [
                {
                    "id": "45:5221",
                    "name": "STAY TUNE - SUBSCRIBE TO OUR NEWSLETTER",
                    "type": "TEXT",
                    "characters": "STAY TUNE - SUBSCRIBE TO OUR NEWSLETTER",
                    "style": {
                        "fontFamily": "HK Grotesk",
                        "fontPostScriptName": "HKGrotesk-BoldLegacy",
                        "fontStyle": "Bold Legacy",
                        "fontWeight": 700,
                        "fontSize": 30,
                    },
                }
            ],
        }
    }

    result = FigmaJsonAdapter().from_data(payload)
    text = result.root.children[0]

    assert text.style.font == FontIntent(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
        postscript_name="HKGrotesk-BoldLegacy",
        source_style="Bold Legacy",
    )

    # Preserve source typography too, so Fidelity/debugging never loses Figma truth.
    assert text.style.font_family == "HK Grotesk"
    assert text.style.font_postscript_name == "HKGrotesk-BoldLegacy"
    assert text.style.font_style == "Bold Legacy"
    assert text.style.font_weight == 700
