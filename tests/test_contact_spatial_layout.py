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


def test_contact_text_is_split_into_absolute_rows_using_icon_spacing():
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

    assert root.children[0].source_id == "contact"
    lines = [child for child in result.children if (child.source_id or "").startswith("contact::contact-line-")]
    assert [line.text for line in lines] == ["first", "second", "third", "continuation"]
    assert [line.style.y for line in lines] == [3537, 3576, 3616, 3637.6]
    assert lines[0].style.x > 1131
    assert lines[3].style.x == 1131
    assert all(line.style.width_mode == "hug" for line in lines)
    assert all(line.style.text_auto_resize == "WIDTH_AND_HEIGHT" for line in lines)

    icons = [child for child in result.children if child.kind == "icon"]
    assert [(icon.source_id, icon.style.x, icon.style.y, icon.style.width) for icon in icons] == [
        ("mail", 1130, 3539, 25),
        ("instagram", 1130, 3578, 25),
        ("phone", 1134, 3618, 17),
    ]


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
