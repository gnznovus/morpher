from morpher.ir.nodes import DesignNode
from morpher.renderers.elementor import render_elementor


def test_renders_container_with_heading():
    root = DesignNode(
        kind="container",
        name="Morpher Elementor Test",
        source_id="1:1",
        children=[
            DesignNode(
                kind="text",
                name="Heading",
                source_id="1:2",
                text="Morpher Elementor Test",
            )
        ],
    )

    result = render_elementor(root)

    assert result["version"] == "0.4"
    assert result["type"] == "container"
    assert result["title"] == "Morpher Elementor Test"
    assert result["page_settings"] == []

    container = result["content"][0]
    assert container["elType"] == "container"
    assert container["settings"] == []
    assert container["isInner"] is False

    heading = container["elements"][0]
    assert heading["elType"] == "widget"
    assert heading["widgetType"] == "heading"
    assert heading["settings"] == {"title": "Morpher Elementor Test"}
    assert heading["elements"] == []
    assert heading["isInner"] is False


def test_elementor_ids_are_deterministic_and_valid_length():
    root = DesignNode(
        kind="container",
        name="Test",
        source_id="45:12",
        children=[DesignNode(kind="text", source_id="45:18", text="Hello")],
    )

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
