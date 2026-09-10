from morpher.inputs.figma_json import FigmaJsonAdapter


def test_normalizes_realistic_figma_payload():
    payload = {
        "document": {
            "id": "45:5300",
            "name": "Homepage Hide",
            "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 960},
            "children": [
                {
                    "id": "45:5303",
                    "name": "HOME PAGE_Original000 1",
                    "type": "RECTANGLE",
                    "fills": [
                        {
                            "type": "IMAGE",
                            "imageRef": "45efa85b024993bd904050e0cd9b9dd5a51925b3",
                        }
                    ],
                    "absoluteBoundingBox": {"x": 1, "y": -50, "width": 1920, "height": 1080},
                    "constraints": {"vertical": "TOP", "horizontal": "LEFT"},
                },
                {
                    "id": "45:5310",
                    "name": "OFFERS",
                    "type": "TEXT",
                    "characters": "OFFERS",
                    "fills": [
                        {
                            "type": "SOLID",
                            "color": {"r": 1, "g": 1, "b": 1, "a": 1},
                        }
                    ],
                    "absoluteBoundingBox": {"x": 1286, "y": 32, "width": 69, "height": 19},
                    "style": {
                        "fontFamily": "HK Grotesk",
                        "fontStyle": "SemiBold",
                        "fontWeight": 600,
                        "fontSize": 16,
                        "letterSpacing": 1.6,
                        "lineHeightPx": 19.203125,
                        "textAlignHorizontal": "LEFT",
                        "textAlignVertical": "TOP",
                    },
                },
                {
                    "id": "45:5306",
                    "name": "Vector",
                    "type": "VECTOR",
                },
            ],
        },
        "schemaVersion": 0,
    }

    result = FigmaJsonAdapter().from_data(payload)

    assert result.root.kind == "container"
    assert result.root.source_id == "45:5300"
    assert result.root.style.width == 1920
    assert result.root.style.height == 960

    image = result.root.children[0]
    assert image.kind == "image"
    assert image.image_ref == "45efa85b024993bd904050e0cd9b9dd5a51925b3"
    assert image.style.x == 1
    assert image.style.y == -50
    assert image.style.constraint_horizontal == "LEFT"

    text = result.root.children[1]
    assert text.kind == "text"
    assert text.text == "OFFERS"
    assert text.style.font_family == "HK Grotesk"
    assert text.style.font_weight == 600
    assert text.style.font_size == 16
    assert text.style.letter_spacing == 1.6
    assert text.style.text_color == "rgba(255, 255, 255, 1)"
    assert text.style.background is None

    vector = result.root.children[2]
    assert vector.kind == "icon"
    assert not any("VECTOR" in warning and "45:5306" in warning for warning in result.warnings)


def test_prunes_hidden_figma_subtrees():
    payload = {
        "document": {
            "id": "1:1",
            "name": "Root",
            "type": "FRAME",
            "children": [
                {
                    "id": "1:2",
                    "name": "Visible",
                    "type": "FRAME",
                    "children": [],
                },
                {
                    "id": "1:3",
                    "name": "Hidden",
                    "type": "FRAME",
                    "visible": False,
                    "children": [
                        {
                            "id": "1:4",
                            "name": "Hidden Text",
                            "type": "TEXT",
                            "characters": "should not participate in layout",
                        }
                    ],
                },
            ],
        }
    }

    result = FigmaJsonAdapter().from_data(payload)

    assert [child.source_id for child in result.root.children] == ["1:2"]


def test_prunes_hidden_children_from_auto_layout():
    payload = {
        "document": {
            "id": "2:1",
            "name": "Auto Layout",
            "type": "FRAME",
            "layoutMode": "HORIZONTAL",
            "children": [
                {
                    "id": "2:2",
                    "name": "Visible",
                    "type": "TEXT",
                    "characters": "VISIBLE",
                },
                {
                    "id": "2:3",
                    "name": "Hidden",
                    "type": "TEXT",
                    "visible": False,
                    "characters": "HIDDEN",
                },
            ],
        }
    }

    result = FigmaJsonAdapter().from_data(payload)

    assert result.root.style.layout_direction == "horizontal"
    assert [child.text for child in result.root.children] == ["VISIBLE"]


def test_normalizes_auto_layout_fields_when_present():
    payload = {
        "document": {
            "id": "1:1",
            "name": "Auto Layout",
            "type": "FRAME",
            "layoutMode": "VERTICAL",
            "itemSpacing": 24,
            "paddingTop": 10,
            "paddingRight": 20,
            "paddingBottom": 30,
            "paddingLeft": 40,
            "layoutSizingHorizontal": "FILL",
            "layoutSizingVertical": "HUG",
            "children": [],
        }
    }

    result = FigmaJsonAdapter().from_data(payload)
    style = result.root.style

    assert style.layout_direction == "vertical"
    assert style.gap == 24
    assert style.padding_top == 10
    assert style.padding_right == 20
    assert style.padding_bottom == 30
    assert style.padding_left == 40
    assert style.width_mode == "fill"
    assert style.height_mode == "hug"


def test_rejects_non_figma_json():
    adapter = FigmaJsonAdapter()

    try:
        adapter.from_data({"hello": "world"})
    except ValueError as error:
        assert "document" in str(error)
    else:
        raise AssertionError("expected ValueError")
