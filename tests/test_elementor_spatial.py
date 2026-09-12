import math

from morpher.compiler.elementor_spatial import compile_elementor_spatial_structure
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_rotated_label_remains_sibling_and_recovers_pretransform_box():
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

    normalized = result.children[1]
    assert normalized.style.width == 192
    assert normalized.style.height == 24
    assert normalized.style.x == -58
    assert normalized.style.y == 446
    assert normalized.style.text_auto_resize is None
    assert normalized.style.width_mode == "fixed"

    rendered = render_elementor(result)["content"][0]
    rail_result, label_result = rendered["elements"]
    settings = label_result["settings"]
    assert rail_result["elType"] == "container"
    assert label_result["widgetType"] == "heading"
    assert settings["_element_width"] == "auto"
    assert "_element_custom_width" not in settings
    assert abs(settings["_offset_x"]["size"] - (-50 / 1928 * 100)) < 1e-9
    assert abs(settings["_offset_y"]["size"] - (450 / 1928 * 100)) < 1e-9
    assert settings["_transform_rotate_popover"] == "transform"
    assert abs(settings["_transform_rotateZ_effect"]["size"] + 90) < 1e-6


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


def test_compact_graphics_and_short_label_become_atomic_layout_group():
    line = DesignNode(
        kind="icon",
        source_id="line",
        style=DesignStyle(x=10212, y=1970.587, width=156, height=0),
    )
    arrow = DesignNode(
        kind="icon",
        source_id="arrow",
        style=DesignStyle(x=10211.140625, y=1963.1255, width=9.72, height=14.923),
    )
    label = DesignNode(
        kind="text",
        source_id="label",
        text="BACK TO STAY",
        style=DesignStyle(x=10383, y=1958.9102, width=157, height=22.8496, font_size=20),
    )
    control = DesignNode(
        kind="container",
        source_id="control",
        style=DesignStyle(x=10211.140625, y=1958.9101, width=328.8594, height=22.8497),
        children=[line, arrow, label],
    )

    result = compile_elementor_spatial_structure(control)

    assert result.style.layout_direction == "horizontal"
    assert result.style.counter_axis_align == "center"
    assert len(result.children) == 2
    graphic, normalized_label = result.children
    assert graphic.kind == "container"
    assert [child.source_id for child in graphic.children] == ["line", "arrow"]
    assert normalized_label.source_id == "label"
    assert normalized_label.style.width_mode == "fixed"
    assert normalized_label.style.text_auto_resize is None
    assert normalized_label.style.width == 167
    assert abs(result.style.width - 338.8594) < 1e-6


def test_large_content_region_is_not_collapsed_as_atomic_layout_group():
    icon = DesignNode(
        kind="icon",
        source_id="icon",
        style=DesignStyle(x=0, y=0, width=40, height=40),
    )
    label = DesignNode(
        kind="text",
        source_id="label",
        text="A short heading",
        style=DesignStyle(x=80, y=20, width=180, height=24, font_size=20),
    )
    region = DesignNode(
        kind="container",
        source_id="region",
        style=DesignStyle(x=0, y=0, width=600, height=300),
        children=[icon, label],
    )

    result = compile_elementor_spatial_structure(region)

    assert result.style.layout_direction is None
    assert [child.source_id for child in result.children] == ["icon", "label"]
