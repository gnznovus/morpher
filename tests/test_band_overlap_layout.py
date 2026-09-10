from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _text(source_id: str, *, x: float, y: float, width: float, height: float) -> DesignNode:
    return DesignNode(
        kind="text",
        source_id=source_id,
        text=source_id,
        style=DesignStyle(x=x, y=y, width=width, height=height),
    )


def test_overlapping_text_columns_do_not_form_horizontal_band():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1200, height=700),
        children=[
            _text("p1", x=200, y=200, width=700, height=120),
            _text("p2", x=220, y=300, width=720, height=220),
        ],
    )

    compiled = compile_responsive_layout(root)

    assert compiled.style.layout_direction == "vertical"
    assert [child.source_id for child in compiled.children] == ["p1", "p2"]
    assert all(child.kind == "text" for child in compiled.children)


def test_side_by_side_text_still_forms_horizontal_band():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1200, height=700),
        children=[
            _text("left", x=100, y=220, width=400, height=220),
            _text("right", x=650, y=240, width=420, height=180),
        ],
    )

    compiled = compile_responsive_layout(root)

    assert compiled.style.layout_direction == "vertical"
    assert len(compiled.children) == 1
    row = compiled.children[0]
    assert row.kind == "container"
    assert row.style.layout_direction == "horizontal"
    assert [child.source_id for child in row.children] == ["left", "right"]


def test_thin_vertical_icon_cannot_bridge_text_into_horizontal_band():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1200, height=700),
        children=[
            _text("p1", x=200, y=180, width=700, height=160),
            _text("p2", x=210, y=320, width=720, height=220),
            DesignNode(
                kind="icon",
                source_id="rail",
                style=DesignStyle(x=960, y=150, width=4, height=420),
            ),
        ],
    )

    compiled = compile_responsive_layout(root)

    assert compiled.style.layout_direction == "vertical"
    assert [child.source_id for child in compiled.children[:2]] == ["p1", "p2"]
    rail = next(child for child in compiled.children if child.source_id == "rail")
    assert rail.style.position_mode == "absolute"
