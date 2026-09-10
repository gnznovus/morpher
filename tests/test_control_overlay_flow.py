from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _find(node: DesignNode, source_id: str) -> DesignNode:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def test_full_bleed_background_does_not_make_controls_absolute():
    root = DesignNode(
        kind="container",
        name="Offers",
        source_id="offers:root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(kind="image", source_id="offers:bg", style=DesignStyle(x=0, y=0, width=1920, height=1080)),
            DesignNode(kind="text", source_id="offers:counter", text="01 / 03", style=DesignStyle(x=921, y=871, width=80, height=36, text_auto_resize="WIDTH_AND_HEIGHT")),
            DesignNode(kind="icon", source_id="offers:left-arrow", style=DesignStyle(x=608, y=880, width=156.86, height=18.44)),
            DesignNode(kind="icon", source_id="offers:right-arrow", style=DesignStyle(x=1155, y=880, width=156.86, height=18.44)),
        ],
    )

    compiled = compile_responsive_layout(root)
    left = _find(compiled, "offers:left-arrow")
    right = _find(compiled, "offers:right-arrow")

    assert left.style.position_mode is None
    assert right.style.position_mode is None
    assert left.style.x is None
    assert right.style.x is None


def test_icon_overlapping_multiline_text_becomes_flow_overlay_not_same_row():
    root = DesignNode(
        kind="container",
        name="Contact",
        source_id="contact:root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(kind="image", source_id="contact:bg", style=DesignStyle(x=0, y=0, width=1920, height=1080)),
            DesignNode(kind="text", source_id="contact:text", text="reservation\nmuuhotels\n+66", style=DesignStyle(x=1131, y=656, width=413, height=148)),
            DesignNode(kind="icon", source_id="contact:mail", style=DesignStyle(x=1130, y=658, width=25.46, height=20)),
            DesignNode(kind="icon", source_id="contact:instagram", style=DesignStyle(x=1130, y=697, width=25, height=25)),
            DesignNode(kind="icon", source_id="contact:phone", style=DesignStyle(x=1134, y=737, width=17.49, height=25)),
        ],
    )

    compiled = compile_responsive_layout(root)
    text = _find(compiled, "contact:text")
    mail = _find(compiled, "contact:mail")
    instagram = _find(compiled, "contact:instagram")
    phone = _find(compiled, "contact:phone")

    assert all(node.style.position_mode is None for node in (mail, instagram, phone))
    assert mail.style.margin_top_percent is not None
    assert mail.style.margin_top_percent < 0
    assert text.style.x is None


def test_content_media_still_owns_true_visual_overlay():
    root = DesignNode(
        kind="container",
        name="Destination",
        source_id="destination:root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(kind="image", source_id="destination:image", style=DesignStyle(x=1129, y=94, width=486, height=865)),
            DesignNode(kind="icon", source_id="destination:play", style=DesignStyle(x=1280, y=455, width=144, height=144)),
            DesignNode(kind="text", source_id="destination:title", text="Destination", style=DesignStyle(x=179, y=171, width=716, height=120)),
            DesignNode(kind="text", source_id="destination:body", text="Body", style=DesignStyle(x=179, y=313, width=768, height=246)),
        ],
    )

    compiled = compile_responsive_layout(root)
    play = _find(compiled, "destination:play")

    assert play.style.position_mode == "absolute"
