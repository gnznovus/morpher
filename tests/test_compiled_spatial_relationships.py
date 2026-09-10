from morpher.compiler.overlays import resolve_compiled_spatial_relationships
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x=None, y=None, width=None, height=None, text=None, position=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            position_mode=position,
        ),
    )


def test_full_bleed_image_returns_to_relative_flow_and_pulls_content_over_it():
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node("image", "bg", x=0, y=0, width=1920, height=1080),
            _node("text", "title", x=179, y=50, width=104, height=36, text="Offers."),
        ],
    )
    compiled_title = _node("text", "title", width=104, height=36, text="Offers.")
    compiled_title.style.margin_top_percent = 2.5
    compiled_bg = _node("image", "bg", x=0, y=0, width=1920, height=1080, position="absolute")
    compiled_bg.style.offset_x = 0
    compiled_bg.style.offset_y = 0
    compiled = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(width=1920, layout_direction="vertical"),
        children=[compiled_title, compiled_bg],
    )

    result = resolve_compiled_spatial_relationships(compiled, source, 1920)

    assert result.children[0].source_id == "bg"
    assert compiled_bg.style.position_mode is None
    assert compiled_bg.style.offset_x is None
    assert compiled_bg.style.offset_y is None
    assert compiled_bg.style.width_mode == "fill"
    assert compiled_title.style.margin_top_percent < 0


def test_overlapping_contact_text_and_icons_become_vertical_owned_group():
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node("text", "contact", x=1131, y=656, width=413, height=148, text="reservation\nmuuhotels\n+66"),
            _node("text", "enquiry", x=1129, y=791, width=278, height=24, text="SPECIAL OFFER ENQUIRY"),
            _node("icon", "mail", x=1130, y=658, width=25, height=20),
            _node("icon", "instagram", x=1130, y=697, width=25, height=25),
            _node("icon", "phone", x=1134, y=737, width=17, height=25),
        ],
    )

    contact = _node("text", "contact", width=413, height=148, text="reservation\nmuuhotels\n+66")
    enquiry = _node("text", "enquiry", width=278, height=24, text="SPECIAL OFFER ENQUIRY")
    row = DesignNode(
        kind="container",
        source_id="root::row-contact",
        style=DesignStyle(layout_direction="horizontal", width_mode="fill", height_mode="hug", margin_top_percent=2, margin_left_percent=58.8),
        children=[enquiry, contact],
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

    group = result.children[0]
    assert group.kind == "container"
    assert group.style.layout_direction == "vertical"
    assert [child.source_id for child in group.children] == ["contact", "mail", "instagram", "phone"]
    assert result.children[1].source_id == "enquiry"
    assert all(child.style.position_mode is None for child in group.children[1:])
    assert all(child.style.margin_top_percent < 0 for child in group.children[1:])
    assert all(child.style.margin_bottom_percent > 0 for child in group.children[1:])
