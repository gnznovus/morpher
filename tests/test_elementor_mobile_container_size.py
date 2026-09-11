from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_outlined_fluid_absolute_shape_uses_exact_spacer_height_on_mobile() -> None:
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

    shape = render_elementor(root)["content"][0]["elements"][0]
    settings = shape["settings"]

    expected_width = {"unit": "vw", "size": 176 / 1920 * 100, "sizes": []}
    expected_space = {"unit": "custom", "size": f"{55 / 1920 * 100:g}vw", "sizes": []}

    assert shape["elType"] == "widget"
    assert shape["widgetType"] == "spacer"
    assert settings["_element_custom_width"] == expected_width
    assert settings["space"] == expected_space
    assert settings["space_mobile"] == expected_space
    assert settings["_border_border"] == "solid"
    assert settings["_border_color"] == "rgba(255, 255, 255, 1)"
