from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.renderers.elementor import render_elementor


def test_figma_fill_image_keeps_authored_frame_and_cover_crop_in_elementor():
    document = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "root",
                "name": "Image Frame",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "children": [
                    {
                        "id": "photo",
                        "name": "Photo",
                        "type": "RECTANGLE",
                        "absoluteBoundingBox": {"x": 100, "y": 200, "width": 425, "height": 306},
                        "fills": [
                            {
                                "type": "IMAGE",
                                "scaleMode": "FILL",
                                "imageRef": "image-ref",
                            }
                        ],
                    }
                ],
            }
        }
    )

    photo = document.root.children[0]
    assert photo.kind == "image"
    assert photo.style.image_scale_mode == "FILL"
    assert photo.style.width == 425
    assert photo.style.height == 306

    rendered = render_elementor(
        document.root,
        asset_sources={"image-ref": "assets/photo.png"},
    )["content"][0]["elements"][0]
    settings = rendered["settings"]

    authored_width_vw = 425 / 1920 * 100
    assert settings["_element_custom_width"]["unit"] == "vw"
    assert abs(settings["_element_custom_width"]["size"] - authored_width_vw) < 1e-9
    assert settings["width"]["unit"] == "vw"
    assert abs(settings["width"]["size"] - authored_width_vw) < 1e-9
    assert settings["height"] == {"unit": "custom", "size": f"{306 / 1920 * 100:g}vw", "sizes": []}
    assert settings["object-fit"] == "cover"


def test_non_fill_image_does_not_force_cover_crop():
    document = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "root",
                "name": "Image Frame",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "children": [
                    {
                        "id": "photo",
                        "name": "Photo",
                        "type": "RECTANGLE",
                        "absoluteBoundingBox": {"x": 100, "y": 200, "width": 425, "height": 306},
                        "fills": [
                            {
                                "type": "IMAGE",
                                "scaleMode": "FIT",
                                "imageRef": "image-ref",
                            }
                        ],
                    }
                ],
            }
        }
    )

    rendered = render_elementor(
        document.root,
        asset_sources={"image-ref": "assets/photo.png"},
    )["content"][0]["elements"][0]
    settings = rendered["settings"]

    assert "width" not in settings
    assert "height" not in settings
    assert "object-fit" not in settings
