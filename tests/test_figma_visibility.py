from morpher.inputs.figma_json import FigmaJsonAdapter


def test_hidden_figma_subtree_is_ignored_by_design_ir() -> None:
    result = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "1:1",
                "name": "Page",
                "type": "FRAME",
                "children": [
                    {
                        "id": "2:1",
                        "name": "Visible content",
                        "type": "FRAME",
                        "children": [
                            {
                                "id": "2:2",
                                "name": "Visible text",
                                "type": "TEXT",
                                "characters": "Keep me",
                            }
                        ],
                    },
                    {
                        "id": "3:1",
                        "name": "Homepage Hide",
                        "type": "FRAME",
                        "visible": False,
                        "children": [
                            {
                                "id": "3:2",
                                "name": "Child still marked visible",
                                "type": "TEXT",
                                "visible": True,
                                "characters": "Do not compile me",
                            }
                        ],
                    },
                ],
            }
        }
    )

    assert [child.source_id for child in result.root.children] == ["2:1"]
    assert result.root.children[0].children[0].text == "Keep me"


def test_hidden_child_does_not_affect_vector_composite_detection() -> None:
    result = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "1:1",
                "name": "Page",
                "type": "FRAME",
                "children": [
                    {
                        "id": "4:1",
                        "name": "Icon",
                        "type": "FRAME",
                        "children": [
                            {"id": "4:2", "name": "Vector 1", "type": "VECTOR"},
                            {"id": "4:3", "name": "Vector 2", "type": "VECTOR"},
                            {
                                "id": "4:4",
                                "name": "Hidden label",
                                "type": "TEXT",
                                "visible": False,
                                "characters": "This should not change classification",
                            },
                        ],
                    }
                ],
            }
        }
    )

    assert result.root.children[0].kind == "icon"
    assert result.root.children[0].children == []
