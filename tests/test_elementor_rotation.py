import math

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_rotated_text_preserves_figma_rotation_in_elementor():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(
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
                    line_height=24,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["_transform_rotate_popover"] == "yes"
    assert settings["_transform_rotateZ_effect"]["unit"] == "deg"
    assert abs(settings["_transform_rotateZ_effect"]["size"] + 90) < 1e-6
    assert settings["_element_width"] == "auto"


def test_vertical_figma_line_renders_as_vertical_elementor_surface():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=-8, y=-4, width=1928, height=964),
        children=[
            DesignNode(
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
        ],
    )

    divider = render_elementor(root)["content"][0]["elements"][0]
    settings = divider["settings"]

    assert divider["elType"] == "container"
    assert "widgetType" not in divider
    assert settings["position"] == "absolute"
    assert settings["width"] == {"unit": "px", "size": 1, "sizes": []}
    assert settings["min_height"] == {"unit": "vw", "size": 4.511410788381743, "sizes": []}
    assert settings["background_color"] == "rgba(255, 255, 255, 0.5)"
