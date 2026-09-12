import pytest

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_nested_absolute_geometry_uses_one_viewport_scale():
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=465),
        children=[
            DesignNode(
                kind="container",
                source_id="1:2",
                style=DesignStyle(x=607, y=67, width=987, height=1131),
                children=[
                    DesignNode(
                        kind="shape",
                        source_id="1:3",
                        style=DesignStyle(x=1168, y=261, width=176, height=56),
                    )
                ],
            )
        ],
    )

    result = render_elementor(root)
    outer = result["content"][0]["elements"][0]
    inner = outer["elements"][0]

    assert outer["settings"]["_offset_x"] == {"unit": "vw", "size": 31.614583333333336, "sizes": []}
    assert outer["settings"]["_offset_y"] == {"unit": "vw", "size": 3.4895833333333335, "sizes": []}
    assert outer["settings"]["width"] == {"unit": "vw", "size": 51.40625, "sizes": []}
    assert outer["settings"]["min_height"]["unit"] == "vw"
    assert outer["settings"]["min_height"]["size"] == pytest.approx(58.90625)

    assert inner["settings"]["_offset_x"] == {"unit": "vw", "size": 29.21875, "sizes": []}
    assert inner["settings"]["_offset_y"] == {"unit": "vw", "size": 10.104166666666666, "sizes": []}
    assert inner["settings"]["width"] == {"unit": "vw", "size": 9.166666666666666, "sizes": []}
    assert inner["settings"]["min_height"] == {"unit": "vw", "size": 2.9166666666666665, "sizes": []}


def test_divider_removes_elementor_default_gap():
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=465),
        children=[
            DesignNode(
                kind="divider",
                source_id="1:2",
                style=DesignStyle(
                    x=581,
                    y=316,
                    width=763,
                    height=1,
                    stroke_color="rgba(255, 255, 255, 1)",
                    stroke_weight=1,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    assert settings["gap"] == {"unit": "px", "size": 0, "sizes": []}
    assert settings["_offset_x"] == {"unit": "vw", "size": 30.260416666666668, "sizes": []}
    assert settings["_offset_y"] == {"unit": "vw", "size": 16.458333333333332, "sizes": []}
    assert settings["_element_custom_width"] == {"unit": "vw", "size": 39.739583333333336, "sizes": []}
