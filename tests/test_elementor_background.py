from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_container_background_image_uses_cover_and_source_opacity():
    root = DesignNode(
        kind="container",
        name="Offers",
        source_id="offers:root",
        style=DesignStyle(
            width=1920,
            layout_direction="vertical",
            background="rgba(0, 0, 0, 1)",
            background_image_ref="offer-bg",
            background_image_opacity=0.5,
        ),
        children=[DesignNode(kind="text", source_id="offers:title", text="Offers.")],
    )

    result = render_elementor(
        root,
        asset_sources={"offer-bg": "assets/Offers/offers-background.jpg"},
    )

    settings = result["content"][0]["settings"]
    assert settings["background_background"] == "classic"
    assert settings["background_image"]["url"] == "assets/Offers/offers-background.jpg"
    assert settings["background_position"] == "center center"
    assert settings["background_repeat"] == "no-repeat"
    assert settings["background_size"] == "cover"
    assert settings["background_overlay_background"] == "classic"
    assert settings["background_overlay_color"] == "rgba(0, 0, 0, 0.5)"
    assert all(element.get("widgetType") != "image" for element in result["content"][0]["elements"])
