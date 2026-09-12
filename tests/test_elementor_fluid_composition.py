from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor
from morpher.typography import fluid_font_size


def test_fluid_font_size_can_drop_readability_floor_for_composition() -> None:
    scale = fluid_font_size(30, 1920, minimum_px=0)

    assert scale is not None
    assert scale.css() == "clamp(0rem, 1.5625vw, 1.875rem)"


def test_free_layout_text_uses_composition_fluid_typography_and_width() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=465),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="NEWSLETTER",
                style=DesignStyle(
                    x=580,
                    y=136,
                    width=600,
                    height=36,
                    font_size=30,
                    line_height=36,
                    letter_spacing=3,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["_position"] == "absolute"
    assert settings["_offset_x"] == {"unit": "%", "size": 30.208333333333332, "sizes": []}
    assert settings["_element_custom_width"] == {"unit": "%", "size": 31.25, "sizes": []}
    assert settings["typography_font_size"] == {
        "unit": "custom",
        "size": "clamp(0rem, 1.5625vw, 1.875rem)",
        "sizes": [],
    }
    assert settings["typography_line_height"] == {"unit": "em", "size": 1.2, "sizes": []}
    assert settings["typography_letter_spacing"] == {"unit": "em", "size": 0.1, "sizes": []}


def test_flow_text_keeps_readable_fluid_floor() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=1920, layout_direction="vertical"),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="Readable content",
                style=DesignStyle(font_size=30),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["typography_font_size"] == {
        "unit": "custom",
        "size": "clamp(1rem, 1.5625vw, 1.875rem)",
        "sizes": [],
    }
