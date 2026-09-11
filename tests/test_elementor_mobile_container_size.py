from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_fluid_absolute_container_repeats_composition_size_on_mobile() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(x=0, y=0, width=1920, height=465),
        children=[
            DesignNode(
                kind="shape",
                source_id="1:2",
                style=DesignStyle(
                    x=1120,
                    y=260,
                    width=176,
                    height=55,
                    stroke_color="rgba(255, 255, 255, 1)",
                    stroke_weight=1,
                ),
            )
        ],
    )

    settings = render_elementor(root)["content"][0]["elements"][0]["settings"]

    expected_width = {"unit": "vw", "size": 176 / 1920 * 100, "sizes": []}
    expected_height = {"unit": "vw", "size": 55 / 1920 * 100, "sizes": []}

    assert settings["width"] == expected_width
    assert settings["width_mobile"] == expected_width
    assert settings["min_height"] == expected_height
    assert settings["min_height_mobile"] == expected_height
