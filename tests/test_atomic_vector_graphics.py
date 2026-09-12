from morpher.inputs.figma_json import FigmaJsonAdapter


def _vector(index: int) -> dict:
    return {"id": f"2:{index}", "name": "Vector", "type": "VECTOR"}


def test_vector_dominant_mark_with_short_annotation_is_one_icon() -> None:
    mark = {
        "id": "2:1",
        "name": "Brand mark",
        "type": "FRAME",
        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 194, "height": 152},
        "children": [
            {
                "id": "2:2",
                "name": "TM",
                "type": "TEXT",
                "characters": "TM",
            },
            *[_vector(index) for index in range(3, 23)],
        ],
    }
    result = FigmaJsonAdapter().from_data(
        {"document": {"id": "1:1", "name": "Root", "type": "FRAME", "children": [mark]}}
    )

    graphic = result.root.children[0]
    assert graphic.kind == "icon"
    assert graphic.source_id == "2:1"
    assert graphic.children == []
    assert graphic.style.width == 194
    assert graphic.style.height == 152


def test_regular_icon_and_text_row_stays_a_container() -> None:
    row = {
        "id": "3:1",
        "name": "Contact row",
        "type": "FRAME",
        "children": [
            _vector(2),
            {"id": "3:3", "name": "Phone", "type": "TEXT", "characters": "+66 (0)2 090 9000"},
        ],
    }
    result = FigmaJsonAdapter().from_data(
        {"document": {"id": "1:1", "name": "Root", "type": "FRAME", "children": [row]}}
    )

    assert result.root.children[0].kind == "container"


def test_vector_group_with_meaningful_text_stays_a_container() -> None:
    group = {
        "id": "4:1",
        "name": "Feature group",
        "type": "FRAME",
        "children": [
            *[_vector(index) for index in range(2, 10)],
            {"id": "4:10", "name": "Label", "type": "TEXT", "characters": "Learn more about our hotel"},
        ],
    }
    result = FigmaJsonAdapter().from_data(
        {"document": {"id": "1:1", "name": "Root", "type": "FRAME", "children": [group]}}
    )

    assert result.root.children[0].kind == "container"
