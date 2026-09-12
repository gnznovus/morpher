import math

from morpher.compiler.elementor_spatial import compile_elementor_spatial_structure
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_rotated_label_remains_sibling_of_side_rail():
    rail = DesignNode(
        kind="shape",
        source_id="rail",
        style=DesignStyle(x=1, y=0, width=74, height=960, background="rgba(0, 0, 0, 0.5)"),
    )
    label = DesignNode(
        kind="text",
        source_id="label",
        text="LOREM IPSUM DO",
        style=DesignStyle(
            x=26,
            y=362,
            width=24,
            height=192,
            rotation=-math.pi / 2,
            text_auto_resize="WIDTH_AND_HEIGHT",
            font_size=20,
        ),
    )
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=-8, y=-4, width=1928, height=964),
        children=[rail, label],
    )

    result = compile_elementor_spatial_structure(root)

    assert [child.source_id for child in result.children] == ["rail", "label"]
    assert result.children[0].kind == "shape"
    assert result.children[1].style.width == 24
    assert result.children[1].style.height == 192
    assert result.children[1].style.text_auto_resize == "WIDTH_AND_HEIGHT"

    rendered = render_elementor(result)["content"][0]
    rail_result, label_result = rendered["elements"]
    assert rail_result["elType"] == "container"
    assert label_result["widgetType"] == "heading"
    assert label_result["settings"]["_element_width"] == "auto"
    assert label_result["settings"]["_transform_rotate_popover"] == "transform"
    assert abs(label_result["settings"]["_transform_rotateZ_effect"]["size"] + 90) < 1e-6


def test_rotated_vertical_line_is_normalized_for_divider_widget():
    divider = DesignNode(
        kind="divider",
        source_id="nav-divider",
        style=DesignStyle(
            x=1580,
            y=-4,
            width=0.000004,
            height=87,
            rotation=math.pi / 2,
            stroke_color="rgba(255, 255, 255, 0.5)",
            stroke_weight=1,
        ),
    )
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=-8, y=-4, width=1928, height=964),
        children=[divider],
    )

    result = compile_elementor_spatial_structure(root)
    normalized = result.children[0]

    assert normalized.style.width == 87
    assert normalized.style.height == 1
    assert normalized.style.x == 1537
    assert normalized.style.y == 39

    rendered = render_elementor(result)["content"][0]["elements"][0]
    settings = rendered["settings"]
    assert rendered["widgetType"] == "divider"
    assert settings["_transform_rotate_popover"] == "transform"
    assert abs(settings["_transform_rotateZ_effect"]["size"] - 90) < 1e-6
    assert settings["_element_custom_width"]["size"] == 87 / 1928 * 100
