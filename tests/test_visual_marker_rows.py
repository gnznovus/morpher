from morpher.compiler.contact import compile_contact_spatial_layout
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _text(source_id: str, *, x: float, y: float, width: float, height: float, value: str, paragraph_spacing: float = 18) -> DesignNode:
    return DesignNode(
        kind="text",
        source_id=source_id,
        text=value,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            font_size=20,
            line_height=24,
            paragraph_spacing=paragraph_spacing,
        ),
    )


def _bullet(source_id: str, *, x: float, y: float) -> DesignNode:
    return DesignNode(
        kind="shape",
        source_id=source_id,
        source_type="ELLIPSE",
        style=DesignStyle(
            x=x,
            y=y,
            width=18,
            height=18,
            background="rgba(254, 80, 0, 1)",
            border_radius=9,
        ),
    )


def test_figma_ellipse_becomes_round_shape_without_warning():
    document = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "root",
                "name": "Amenities",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 960},
                "children": [
                    {
                        "id": "bullet",
                        "name": "Ellipse 1",
                        "type": "ELLIPSE",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 18, "height": 18},
                        "fills": [
                            {
                                "type": "SOLID",
                                "color": {"r": 0.9960784314, "g": 0.3137255013, "b": 0, "a": 1},
                            }
                        ],
                    }
                ],
            }
        }
    )

    bullet = document.root.children[0]
    assert bullet.kind == "shape"
    assert bullet.source_type == "ELLIPSE"
    assert bullet.style.border_radius == 9
    assert document.warnings == []


def test_figma_text_preserves_paragraph_spacing():
    document = FigmaJsonAdapter().from_data(
        {
            "document": {
                "id": "root",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1920, "height": 960},
                "children": [
                    {
                        "id": "copy",
                        "type": "TEXT",
                        "characters": "one\ntwo",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 300, "height": 66},
                        "style": {"fontSize": 20, "lineHeightPx": 24, "paragraphSpacing": 18},
                    }
                ],
            }
        }
    )

    assert document.root.children[0].style.paragraph_spacing == 18


def test_ellipse_marker_rail_preserves_middle_wrapped_item():
    # The real amenities source uses a 42px row rhythm (24px line + 18px paragraph
    # spacing). A wrapped item therefore produces an 84px marker gap.
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _text(
                "amenities",
                x=700,
                y=100,
                width=700,
                height=294,
                value=(
                    "IP telephone\n"
                    "In room safety box\n"
                    "Two LG smart TV’s with cable and IPTV\n"
                    "Scheduled free shuttle van service from hotel to Thonglor BTS\n"
                    "station and Emporium and EmQuartier Shopping malls\n"
                    "Free access to all hotel facilities\n"
                    "24 hours concierge service"
                ),
            ),
            _bullet("b1", x=660, y=102),
            _bullet("b2", x=660, y=144),
            _bullet("b3", x=660, y=186),
            _bullet("b4", x=660, y=228),
            _bullet("b5", x=660, y=312),
            _bullet("b6", x=660, y=354),
        ],
    )

    result = compile_contact_spatial_layout(root)
    items = [child for child in result.children if "::contact-item-" in (child.source_id or "")]

    assert len(items) == 6
    assert [item.children[0].source_id for item in items] == ["b1", "b2", "b3", "b4", "b5", "b6"]
    assert items[3].children[1].text == (
        "Scheduled free shuttle van service from hotel to Thonglor BTS\n"
        "station and Emporium and EmQuartier Shopping malls"
    )
    assert items[4].children[1].text == "Free access to all hotel facilities"
    assert items[5].children[1].text == "24 hours concierge service"
    assert all(item.style.counter_axis_align == "min" for item in items)


def test_two_marker_columns_do_not_claim_each_others_rails():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _text(
                "left-copy",
                x=268,
                y=100,
                width=567,
                height=276,
                value="left one\nleft two\nleft three\nleft four\nleft five\nleft six\nleft seven",
            ),
            _text(
                "right-copy",
                x=1059,
                y=100,
                width=697,
                height=294,
                value="right one\nright two\nright three\nright four\nright five\nright six\nright seven",
            ),
            *[_bullet(f"l{index + 1}", x=223, y=102 + index * 42) for index in range(7)],
            *[_bullet(f"r{index + 1}", x=1016, y=102 + index * 42) for index in range(7)],
        ],
    )

    result = compile_contact_spatial_layout(root)
    left_items = [child for child in result.children if (child.source_id or "").startswith("left-copy::contact-item-")]
    right_items = [child for child in result.children if (child.source_id or "").startswith("right-copy::contact-item-")]

    assert len(left_items) == 7
    assert len(right_items) == 7
    assert [item.children[0].source_id for item in left_items] == [f"l{index}" for index in range(1, 8)]
    assert [item.children[0].source_id for item in right_items] == [f"r{index}" for index in range(1, 8)]
