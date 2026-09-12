from morpher.compiler.contact import compile_contact_spatial_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x=None, y=None, width=None, height=None, text=None, font_size=None, line_height=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            font_size=font_size,
            line_height=line_height,
        ),
    )


def _contact_items(root: DesignNode) -> list[DesignNode]:
    return [child for child in root.children if "::contact-item-" in (child.source_id or "")]


def test_contact_text_wall_is_normalized_into_icon_text_items():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node(
                "text",
                "contact",
                x=1131,
                y=3537,
                width=413,
                height=148,
                text="       first\n       second\n       third\ncontinuation",
                font_size=18,
                line_height=21.6,
            ),
            _node("icon", "mail", x=1130, y=3539, width=25, height=20),
            _node("icon", "instagram", x=1130, y=3578, width=25, height=25),
            _node("icon", "phone", x=1134, y=3618, width=17, height=25),
        ],
    )

    result = compile_contact_spatial_layout(root)
    items = _contact_items(result)

    assert root.children[0].source_id == "contact"
    assert len(items) == 3
    assert [item.children[1].text for item in items] == ["first", "second", "third\ncontinuation"]
    assert [item.children[0].source_id for item in items] == ["mail", "instagram", "phone"]
    assert all(item.style.layout_direction == "horizontal" for item in items)
    assert all(item.style.counter_axis_align == "center" for item in items)
    assert all(item.style.gap is not None and item.style.gap >= 0 for item in items)
    assert [item.style.y for item in items] == [3537, 3576, 3616]
    assert all(item.children[0].style.x is None for item in items)
    assert all(item.children[1].style.x is None for item in items)
    assert items[-1].children[1].style.text_auto_resize == "WIDTH_AND_HEIGHT"


def test_wrapped_icon_is_stripped_before_pairing():
    fax_icon = _node("icon", "fax-glyph", x=1288, y=5534, width=25, height=26)
    fax_frame = DesignNode(
        kind="container",
        source_id="fax-frame",
        style=DesignStyle(x=1286, y=5531, width=28, height=31),
        children=[fax_icon],
    )
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=907),
        children=[
            _node(
                "text",
                "contact",
                x=1340,
                y=5491,
                width=348,
                height=106,
                text=": phone\n: fax\n: email",
                font_size=20,
                line_height=24,
            ),
            _node("icon", "phone", x=1288, y=5493, width=17, height=25),
            fax_frame,
            _node("icon", "mail", x=1286, y=5573, width=25, height=20),
        ],
    )

    result = compile_contact_spatial_layout(root)
    items = _contact_items(result)

    assert [item.children[1].text for item in items] == [": phone", ": fax", ": email"]
    assert [item.children[0].source_id for item in items] == ["phone", "fax-glyph", "mail"]
    assert all(child.source_id != "fax-frame" for child in result.children)
    assert items[1].children[0].kind == "icon"
    assert all(item.style.counter_axis_align == "center" for item in items)


def test_non_contact_multiline_text_is_left_alone():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1000, height=600),
        children=[
            _node("text", "copy", x=100, y=100, width=400, height=80, text="ordinary\nmultiline copy", font_size=20, line_height=24),
        ],
    )

    result = compile_contact_spatial_layout(root)

    assert len(result.children) == 1
    assert result.children[0].source_id == "copy"
    assert result.children[0].text == "ordinary\nmultiline copy"
