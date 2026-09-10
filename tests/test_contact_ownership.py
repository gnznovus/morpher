from morpher.compiler.contact import resolve_contact_group_ownership
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x=None, y=None, width=None, height=None, text=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        style=DesignStyle(x=x, y=y, width=width, height=height),
    )


def _find(node: DesignNode, source_id: str) -> DesignNode | None:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def test_contact_group_is_owned_by_nearby_content_and_cta_follows_it():
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=2881, width=1920, height=960),
        children=[
            _node("text", "more", x=1129, y=3490, width=561, height=24, text="More about our offers"),
            # Intentionally appears before contact in source-array order even
            # though its geometry is below the contact rows.
            _node("text", "enquiry", x=1129, y=3672, width=278, height=24, text="SPECIAL OFFER ENQUIRY"),
            _node("text", "contact", x=1131, y=3537, width=413, height=148, text="contact lines"),
            _node("icon", "mail", x=1130, y=3539, width=25, height=20),
            _node("icon", "instagram", x=1130, y=3578, width=25, height=25),
            _node("icon", "phone", x=1134, y=3618, width=17, height=25),
        ],
    )

    more = _node("text", "more", text="More about our offers")
    more.style.margin_left_percent = 58.8
    enquiry = _node("text", "enquiry", text="SPECIAL OFFER ENQUIRY")
    content_region = DesignNode(
        kind="container",
        source_id="root::region-content",
        style=DesignStyle(layout_direction="vertical", width_percent=100),
        children=[more, enquiry],
    )
    contact_group = DesignNode(
        kind="container",
        source_id="contact::contact-group",
        style=DesignStyle(layout_direction="vertical", width_mode="fill", margin_left_percent=12.0),
        children=[
            DesignNode(kind="container", source_id="contact::contact-row-1", children=[_node("icon", "mail")]),
            DesignNode(kind="container", source_id="contact::contact-row-2", children=[_node("icon", "instagram")]),
            DesignNode(kind="container", source_id="contact::contact-row-3", children=[_node("icon", "phone")]),
        ],
    )
    compiled = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(layout_direction="vertical", width=1920),
        children=[content_region, contact_group],
    )

    result = resolve_contact_group_ownership(compiled, source, 1920)

    assert [child.source_id for child in content_region.children] == [
        "more",
        "contact::contact-group",
        "enquiry",
    ]
    moved_group = _find(result, "contact::contact-group")
    assert moved_group is not None
    assert moved_group.style.margin_left_percent == 58.8
    assert moved_group.style.position_mode is None
    assert moved_group.style.margin_top_percent is not None
    assert moved_group.style.margin_top_percent > 0

    moved_enquiry = _find(result, "enquiry")
    assert moved_enquiry is not None
    assert moved_enquiry.style.margin_left_percent == 58.8
    assert moved_enquiry.style.margin_top_percent is not None
    assert moved_enquiry.style.margin_top_percent > 0
