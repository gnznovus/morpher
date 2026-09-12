from morpher.compiler.contact import compile_contact_spatial_layout
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _text(source_id: str, *, x: float, y: float, width: float, height: float, value: str) -> DesignNode:
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


def test_ellipse_marker_rail_preserves_middle_wrapped_item():
    # Normal marker rhythm is 40px. The fourth item wraps to two text lines, so
    # the gap to the fifth marker is 80px. The compiler must keep that continuation
    # line attached to item four rather than manufacturing an extra bullet row.
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
                height=240,
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
            _bullet("b2", x=660, y=142),
            _bullet("b3", x=660, y=182),
            _bullet("b4", x=660, y=222),
            _bullet("b5", x=660, y=302),
            _bullet("b6", x=660, y=342),
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
