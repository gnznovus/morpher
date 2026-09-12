from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_absolute_group_keeps_children_on_fluid_composition_scale():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(
                kind="container",
                source_id="contact::item",
                style=DesignStyle(
                    x=1200,
                    y=300,
                    position_mode="absolute",
                    offset_x=1200,
                    offset_y=300,
                    height=25,
                    layout_direction="horizontal",
                    width_mode="hug",
                    height_mode="fixed",
                    gap=24,
                    counter_axis_align="center",
                ),
                children=[
                    DesignNode(
                        kind="icon",
                        source_id="phone-icon",
                        style=DesignStyle(width=25, height=25, width_mode="fixed", height_mode="fixed"),
                    ),
                    DesignNode(
                        kind="text",
                        source_id="contact::wording",
                        text=": +66 (0) 2 090 9000",
                        style=DesignStyle(
                            font_size=20,
                            line_height=24,
                            letter_spacing=2,
                            width_mode="hug",
                            height_mode="hug",
                            text_auto_resize="WIDTH_AND_HEIGHT",
                        ),
                    ),
                ],
            )
        ],
    )

    result = render_elementor(root, asset_sources={"phone-icon": "assets/phone.svg"})
    item = result["content"][0]["elements"][0]
    icon = item["elements"][0]["settings"]
    wording = item["elements"][1]["settings"]

    assert item["settings"]["position"] == "absolute"
    assert item["settings"]["_offset_x"] == {"unit": "vw", "size": 62.5, "sizes": []}
    assert item["settings"]["flex_align_items"] == "center"
    assert item["settings"]["flex_gap"] == {
        "column": "1.25",
        "row": "1.25",
        "isLinked": True,
        "unit": "vw",
        "size": 1.25,
    }
    assert icon["_element_custom_width"] == {"unit": "vw", "size": 1.3020833333333335, "sizes": []}
    assert wording["typography_font_size"] == {
        "unit": "custom",
        "size": "clamp(0rem, 1.0417vw, 1.25rem)",
        "sizes": [],
    }


def test_full_bleed_image_widget_is_kept_at_background_z_index():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(
                kind="image",
                source_id="background",
                image_ref="background",
                style=DesignStyle(x=0, y=0, width=1920, height=960),
            )
        ],
    )

    result = render_elementor(root, asset_sources={"background": "assets/background.jpg"})
    settings = result["content"][0]["elements"][0]["settings"]

    assert settings["_z_index"] == 0
