from morpher.compiler.overlays import resolve_compiled_spatial_relationships
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x=None, y=None, width=None, height=None, text=None, position=None, image_ref=None, font_size=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        image_ref=image_ref,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            position_mode=position,
            font_size=font_size,
        ),
    )


def _find(node: DesignNode, source_id: str) -> DesignNode | None:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def test_full_bleed_image_promotes_to_container_background():
    source_bg = _node("image", "bg", x=0, y=0, width=1920, height=1080, image_ref="offer-bg")
    source_bg.style.image_opacity = 0.5
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960, background="rgba(0, 0, 0, 1)"),
        children=[
            source_bg,
            _node("text", "title", x=179, y=50, width=104, height=36, text="Offers."),
        ],
    )
    compiled_title = _node("text", "title", width=104, height=36, text="Offers.")
    compiled_bg = _node("image", "bg", width=1920, height=1080, image_ref="offer-bg")
    compiled = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(width=1920, layout_direction="vertical", background="rgba(0, 0, 0, 1)"),
        children=[compiled_title, compiled_bg],
    )

    result = resolve_compiled_spatial_relationships(compiled, source, 1920)

    assert _find(result, "bg") is None
    assert result.style.background_image_ref == "offer-bg"
    assert result.style.background_image_opacity == 0.5
    assert result.children[0].source_id == "title"
    assert result.children[0].style.margin_top_percent is None


def test_multiline_contact_with_icon_gutter_becomes_normal_rows():
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node(
                "text",
                "contact",
                x=1131,
                y=656,
                width=413,
                height=148,
                text="       reservation.bangkok@muuhotels.com\n       muuhotels\n       +66 (0)2 090 9000\n",
                font_size=18,
            ),
            _node("text", "enquiry", x=1129, y=791, width=278, height=24, text="SPECIAL OFFER ENQUIRY"),
            _node("icon", "mail", x=1130, y=658, width=25, height=20),
            _node("icon", "instagram", x=1130, y=697, width=25, height=25),
            _node("icon", "phone", x=1134, y=737, width=17, height=25),
        ],
    )

    contact = _node(
        "text",
        "contact",
        width=413,
        height=148,
        text="       reservation.bangkok@muuhotels.com\n       muuhotels\n       +66 (0)2 090 9000\n",
        font_size=18,
    )
    enquiry = _node("text", "enquiry", width=278, height=24, text="SPECIAL OFFER ENQUIRY")
    row = DesignNode(
        kind="container",
        source_id="root::row-contact",
        style=DesignStyle(layout_direction="horizontal", width_mode="fill", height_mode="hug", margin_top_percent=2, margin_left_percent=58.8),
        children=[contact, enquiry],
    )
    mail = _node("icon", "mail", width=25, height=20)
    instagram = _node("icon", "instagram", width=25, height=25)
    phone = _node("icon", "phone", width=17, height=25)
    compiled = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(width=1920, layout_direction="vertical"),
        children=[row, mail, instagram, phone],
    )

    result = resolve_compiled_spatial_relationships(compiled, source, 1920)

    group = _find(result, "contact::contact-group")
    assert group is not None
    assert group.style.layout_direction == "vertical"
    assert group.style.margin_left_percent == 58.8
    assert len(group.children) == 3

    expected = [
        ("mail", "reservation.bangkok@muuhotels.com"),
        ("instagram", "muuhotels"),
        ("phone", "+66 (0)2 090 9000"),
    ]
    for index, (icon_id, text) in enumerate(expected, start=1):
        contact_row = _find(group, f"contact::contact-row-{index}")
        assert contact_row is not None
        assert contact_row.style.layout_direction == "horizontal"
        assert contact_row.style.gap is not None
        assert contact_row.style.gap >= 0
        assert contact_row.children[0].source_id == icon_id
        assert contact_row.children[0].style.position_mode is None
        assert contact_row.children[1].text == text
        assert contact_row.children[1].style.width_mode == "hug"

    enquiry_node = _find(result, "enquiry")
    assert enquiry_node is not None
    assert enquiry_node.style.margin_top_percent is not None
    assert enquiry_node.style.margin_top_percent > 0
