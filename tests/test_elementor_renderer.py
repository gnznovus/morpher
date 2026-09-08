from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_renders_container_with_heading():
    root = DesignNode(
        kind="container",
        name="Morpher Elementor Test",
        source_id="1:1",
        children=[
            DesignNode(
                kind="text",
                name="Heading",
                source_id="1:2",
                text="Morpher Elementor Test",
            )
        ],
    )

    result = render_elementor(root)

    assert result["version"] == "0.4"
    assert result["type"] == "container"
    assert result["title"] == "Morpher Elementor Test"
    assert result["page_settings"] == []

    container = result["content"][0]
    assert container["elType"] == "container"
    assert container["settings"] == []
    assert container["isInner"] is False

    heading = container["elements"][0]
    assert heading["elType"] == "widget"
    assert heading["widgetType"] == "heading"
    assert heading["settings"] == {"title": "Morpher Elementor Test"}
    assert heading["elements"] == []
    assert heading["isInner"] is False


def test_renders_auto_layout_container_text_and_shape_settings():
    root = DesignNode(
        kind="container",
        name="Auto Layout Test",
        source_id="1:1",
        style=DesignStyle(
            width=600,
            height=262,
            layout_direction="vertical",
            gap=24,
            padding_top=48,
            padding_right=40,
            padding_bottom=56,
            padding_left=32,
            width_mode="fixed",
            height_mode="hug",
            primary_axis_align="CENTER",
            counter_axis_align="CENTER",
        ),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="Morpher Auto Layout",
                style=DesignStyle(
                    width_mode="hug",
                    height_mode="hug",
                    layout_align="INHERIT",
                    font_family="Arial",
                    font_weight=400,
                    font_size=12,
                    line_height=15,
                    text_color="rgba(0, 0, 0, 1)",
                ),
            ),
            DesignNode(
                kind="text",
                source_id="1:3",
                text="Testing real Figma layout data.",
                style=DesignStyle(
                    width_mode="fill",
                    height_mode="hug",
                    layout_align="STRETCH",
                    font_family="Arial",
                    font_weight=400,
                    font_size=12,
                    line_height=15,
                    text_color="rgba(0, 0, 0, 1)",
                ),
            ),
            DesignNode(
                kind="shape",
                source_id="1:4",
                style=DesignStyle(
                    width_mode="fill",
                    height_mode="fixed",
                    layout_align="STRETCH",
                    height=80,
                    background="rgba(217, 217, 217, 1)",
                ),
            ),
        ],
    )

    result = render_elementor(root)
    container = result["content"][0]
    settings = container["settings"]

    assert settings["flex_direction"] == "column"
    assert settings["flex_justify_content"] == "center"
    assert settings["flex_align_items"] == "center"
    assert settings["width"] == {"unit": "px", "size": 600, "sizes": []}
    assert settings["flex_gap"]["column"] == "24"
    assert settings["flex_gap"]["row"] == "24"
    assert settings["padding"] == {
        "unit": "px",
        "top": "48",
        "right": "40",
        "bottom": "56",
        "left": "32",
        "isLinked": False,
    }

    first_heading = container["elements"][0]
    assert first_heading["settings"]["_element_width"] == "auto"
    assert first_heading["settings"]["_element_align"] == "center"
    assert first_heading["settings"]["typography_typography"] == "custom"
    assert first_heading["settings"]["typography_font_size"]["size"] == 12

    second_heading = container["elements"][1]
    assert second_heading["settings"]["_element_width"] == "initial"
    assert second_heading["settings"]["_element_custom_width"] == {
        "unit": "%",
        "size": 100,
        "sizes": [],
    }

    shape = container["elements"][2]
    assert shape["elType"] == "container"
    assert shape["settings"]["width"] == {"unit": "%", "size": 100, "sizes": []}
    assert shape["settings"]["min_height"] == {"unit": "px", "size": 80, "sizes": []}
    assert shape["settings"]["background_background"] == "classic"
    assert shape["settings"]["background_color"] == "rgba(217, 217, 217, 1)"


def test_elementor_ids_are_deterministic_and_valid_length():
    root = DesignNode(
        kind="container",
        name="Test",
        source_id="45:12",
        children=[DesignNode(kind="text", source_id="45:18", text="Hello")],
    )

    first = render_elementor(root)
    second = render_elementor(root)

    first_container = first["content"][0]
    second_container = second["content"][0]
    first_heading = first_container["elements"][0]
    second_heading = second_container["elements"][0]

    assert first_container["id"] == second_container["id"]
    assert first_heading["id"] == second_heading["id"]
    assert len(first_container["id"]) == 8
    assert len(first_heading["id"]) == 8
    assert first_container["id"] != first_heading["id"]
