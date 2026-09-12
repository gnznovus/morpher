from pathlib import Path

from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor
from morpher.renderers.native_css import render_native_css


def test_figma_text_case_reaches_design_ir() -> None:
    document = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "1:1",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "children": [
                    {
                        "id": "1:2",
                        "type": "TEXT",
                        "characters": "Kodawari Tsukiji",
                        "absoluteBoundingBox": {"x": 900, "y": 120, "width": 520, "height": 72},
                        "style": {
                            "fontSize": 60,
                            "lineHeightPx": 72,
                            "textCase": "UPPER",
                        },
                    }
                ],
            }
        }
    )

    assert document.root.children[0].style.text_case == "UPPER"


def test_elementor_renders_figma_uppercase_intent() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=1080),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="Kodawari Tsukiji",
                style=DesignStyle(
                    x=900,
                    y=120,
                    width=520,
                    height=72,
                    font_size=60,
                    line_height=72,
                    text_case="UPPER",
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["typography_text_transform"] == "uppercase"


def test_native_css_renders_figma_uppercase_intent(tmp_path: Path) -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="Kodawari Tsukiji",
                style=DesignStyle(text_case="UPPER"),
            )
        ],
    )

    css = render_native_css(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        font_asset_dir=tmp_path / "native" / "assets" / "fonts",
        css_dir=tmp_path / "native",
    )

    assert "text-transform: uppercase;" in css


def test_authored_single_line_spatial_text_keeps_natural_width() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=1080),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="01 / 02",
                style=DesignStyle(
                    x=1180,
                    y=980,
                    width=74,
                    height=36,
                    font_size=30,
                    line_height=36,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["_element_width"] == "auto"
    assert "_element_custom_width" not in settings


def test_authored_multiline_spatial_text_keeps_bounded_width() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=1080),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="A long heading that wraps in the source design",
                style=DesignStyle(
                    x=900,
                    y=120,
                    width=520,
                    height=216,
                    font_size=60,
                    line_height=72,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["_element_width"] == "initial"
    assert settings["_element_custom_width"] == {"unit": "vw", "size": 27.083333333333332, "sizes": []}
