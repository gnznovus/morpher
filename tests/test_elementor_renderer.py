from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_renders_container_with_heading():
    root = DesignNode(kind="container", name="Morpher Elementor Test", source_id="1:1", children=[DesignNode(kind="text", name="Heading", source_id="1:2", text="Morpher Elementor Test")])
    result = render_elementor(root)
    assert result["version"] == "0.4"
    assert result["type"] == "container"
    assert result["title"] == "Morpher Elementor Test"
    assert result["page_settings"] == []
    container = result["content"][0]
    assert container["elType"] == "container"
    assert container["settings"] == {"content_width": "full"}
    assert container["isInner"] is False
    heading = container["elements"][0]
    assert heading["elType"] == "widget"
    assert heading["widgetType"] == "heading"
    assert heading["settings"] == {"title": "Morpher Elementor Test"}
    assert heading["elements"] == []
    assert heading["isInner"] is False


def test_renders_auto_layout_container_text_and_shape_settings():
    root = DesignNode(kind="container", name="Auto Layout Test", source_id="1:1", style=DesignStyle(width=600, height=262, layout_direction="vertical", gap=24, padding_top=48, padding_right=40, padding_bottom=56, padding_left=32, width_mode="fixed", height_mode="hug", primary_axis_align="center", counter_axis_align="center"), children=[DesignNode(kind="text", source_id="1:2", text="Morpher Auto Layout", style=DesignStyle(width_mode="hug", height_mode="hug", layout_align="inherit", font_family="Arial", font_weight=400, font_size=12, line_height=15, text_color="rgba(0, 0, 0, 1)")), DesignNode(kind="text", source_id="1:3", text="Testing real Figma layout data.", style=DesignStyle(width_mode="fill", height_mode="hug", layout_align="stretch", font_family="Arial", font_weight=400, font_size=12, line_height=15, text_color="rgba(0, 0, 0, 1)")), DesignNode(kind="shape", source_id="1:4", style=DesignStyle(width_mode="fill", height_mode="fixed", layout_align="stretch", height=80, background="rgba(217, 217, 217, 1)"))])
    result = render_elementor(root)
    container = result["content"][0]
    settings = container["settings"]
    assert settings["content_width"] == "full"
    assert settings["flex_direction"] == "column"
    assert settings["flex_justify_content"] == "center"
    assert settings["flex_align_items"] == "center"
    assert settings["width"] == {"unit": "px", "size": 600, "sizes": []}
    assert settings["flex_gap"]["column"] == "24"
    assert settings["flex_gap"]["row"] == "24"
    assert settings["padding"] == {"unit": "px", "top": "48", "right": "40", "bottom": "56", "left": "32", "isLinked": False}
    first_heading = container["elements"][0]
    assert first_heading["settings"]["_element_width"] == "auto"
    assert first_heading["settings"]["align"] == "center"
    assert first_heading["settings"]["typography_typography"] == "custom"
    assert first_heading["settings"]["typography_font_size"]["size"] == 12
    second_heading = container["elements"][1]
    assert second_heading["settings"]["_element_width"] == "initial"
    assert second_heading["settings"]["_element_custom_width"] == {"unit": "%", "size": 100, "sizes": []}
    shape = container["elements"][2]
    assert shape["elType"] == "container"
    assert shape["settings"]["content_width"] == "full"
    assert shape["settings"]["width"] == {"unit": "%", "size": 100, "sizes": []}
    assert shape["settings"]["min_height"] == {"unit": "px", "size": 80, "sizes": []}
    assert shape["settings"]["background_background"] == "classic"
    assert shape["settings"]["background_color"] == "rgba(217, 217, 217, 1)"


def test_nested_hug_container_uses_figma_width_and_full_content_width():
    root = DesignNode(kind="container", source_id="1:1", style=DesignStyle(layout_direction="horizontal", width_mode="fixed", width=536), children=[DesignNode(kind="text", source_id="1:2", text="Morpher", style=DesignStyle(width_mode="fill")), DesignNode(kind="container", source_id="1:3", style=DesignStyle(width=88, width_mode="hug", height_mode="hug", layout_direction="horizontal", padding_top=12, padding_right=20, padding_bottom=12, padding_left=20), children=[DesignNode(kind="text", source_id="1:4", text="Continue", style=DesignStyle(width_mode="hug"))])])
    result = render_elementor(root)
    root_container = result["content"][0]
    button_container = root_container["elements"][1]
    assert root_container["settings"]["content_width"] == "full"
    assert button_container["settings"]["width"] == {"unit": "px", "size": 88, "sizes": []}
    assert button_container["settings"]["content_width"] == "full"


def test_free_layout_uses_absolute_figma_geometry():
    root = DesignNode(kind="container", name="Free Layout", source_id="45:1", style=DesignStyle(x=100, y=200, width=600, height=400), children=[DesignNode(kind="text", source_id="45:2", text="OFFERS", style=DesignStyle(x=132, y=224, width=69, height=19)), DesignNode(kind="shape", source_id="45:3", style=DesignStyle(x=300, y=260, width=120, height=80, background="rgba(0, 0, 0, 1)"))])
    result = render_elementor(root)
    container = result["content"][0]
    root_settings = container["settings"]
    assert root_settings["width"] == {"unit": "px", "size": 600, "sizes": []}
    assert root_settings["min_height"] == {"unit": "px", "size": 400, "sizes": []}
    heading_settings = container["elements"][0]["settings"]
    assert heading_settings["_position"] == "absolute"
    assert heading_settings["_offset_orientation_h"] == "start"
    assert heading_settings["_offset_orientation_v"] == "start"
    assert heading_settings["_offset_x"] == {"unit": "px", "size": 32, "sizes": []}
    assert heading_settings["_offset_y"] == {"unit": "px", "size": 24, "sizes": []}
    assert heading_settings["_element_custom_width"] == {"unit": "px", "size": 69, "sizes": []}
    shape_settings = container["elements"][1]["settings"]
    assert shape_settings["position"] == "absolute"
    assert shape_settings["_offset_x"] == {"unit": "px", "size": 200, "sizes": []}
    assert shape_settings["_offset_y"] == {"unit": "px", "size": 60, "sizes": []}
    assert shape_settings["width"] == {"unit": "px", "size": 120, "sizes": []}
    assert shape_settings["min_height"] == {"unit": "px", "size": 80, "sizes": []}


def test_elementor_ids_are_deterministic_and_valid_length():
    root = DesignNode(kind="container", name="Test", source_id="45:12", children=[DesignNode(kind="text", source_id="45:18", text="Hello")])
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


def test_renders_image_and_icon_from_elementor_asset_package():
    root = DesignNode(kind="container", name="Discovery", source_id="45:5267", children=[DesignNode(kind="image", name="Rectangle 1", source_id="45:5272", image_ref="image-hash"), DesignNode(kind="icon", name="Play Icon", source_id="45:5273")])
    result = render_elementor(root, asset_sources={"image-hash": "assets/Discovery/discovery-rectangle-1.jpg", "45-5273": "assets/Discovery/discovery-play-icon.svg"})
    image, icon = result["content"][0]["elements"]
    assert image["widgetType"] == "image"
    assert image["settings"]["image"]["url"] == "assets/Discovery/discovery-rectangle-1.jpg"
    assert icon["widgetType"] == "image"
    assert icon["settings"]["image"]["url"] == "assets/Discovery/discovery-play-icon.svg"


def test_preserves_decorative_vector_inside_content_wrapper():
    backdrop = DesignNode(kind="icon", name="Vector", source_id="45:5270", style=DesignStyle(width=1233, height=1412))
    body = DesignNode(kind="text", name="Body", source_id="45:5271", text="Hotel copy")
    wrapper = DesignNode(kind="container", name="Frame", source_id="45:5269", style=DesignStyle(width=1327, height=1520), children=[backdrop, body])
    root = DesignNode(kind="container", name="Discovery", source_id="45:5267", children=[wrapper])
    result = render_elementor(root, asset_sources={"45-5270": "assets/Discovery/discovery-vector.svg"})
    wrapper_result = result["content"][0]["elements"][0]
    assert [element.get("widgetType") for element in wrapper_result["elements"]] == ["image", "heading"]
    assert wrapper_result["elements"][0]["settings"]["image"]["url"] == "assets/Discovery/discovery-vector.svg"


def test_authored_break_is_preserved_without_overriding_bounded_width():
    root = DesignNode(
        kind="container",
        source_id="break:root",
        style=DesignStyle(layout_direction="vertical"),
        children=[
            DesignNode(
                kind="text",
                source_id="break:text",
                text="WELCOME TO MUU\nTHIS SECOND LINE IS STILL ALLOWED TO WRAP NATURALLY",
                style=DesignStyle(width_percent=42.5),
            )
        ],
    )
    heading = render_elementor(root)["content"][0]["elements"][0]
    assert heading["settings"]["title"] == "WELCOME TO MUU<br>THIS SECOND LINE IS STILL ALLOWED TO WRAP NATURALLY"
    assert heading["settings"]["_element_custom_width"] == {"unit": "vw", "size": 42.5, "sizes": []}


def test_compiled_width_is_viewport_relative_and_independent_of_authored_breaks():
    bounded = DesignNode(
        kind="container",
        source_id="break:bounded",
        style=DesignStyle(layout_direction="vertical"),
        children=[DesignNode(kind="text", source_id="break:child", text="FIRST\nSECOND", style=DesignStyle(width_percent=38.125))],
    )
    natural = DesignNode(
        kind="container",
        source_id="break:natural",
        style=DesignStyle(layout_direction="vertical"),
        children=[DesignNode(kind="text", source_id="break:child-natural", text="FIRST SECOND", style=DesignStyle(width_percent=38.125))],
    )
    bounded_settings = render_elementor(bounded)["content"][0]["elements"][0]["settings"]
    natural_settings = render_elementor(natural)["content"][0]["elements"][0]["settings"]
    assert bounded_settings["_element_custom_width"] == natural_settings["_element_custom_width"]
    assert bounded_settings["_element_custom_width"] == {"unit": "vw", "size": 38.125, "sizes": []}
