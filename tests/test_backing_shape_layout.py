from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x, y, width, height, text=None, background=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            background=background,
        ),
    )


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_large_backing_shape_defines_content_region_without_entering_flow():
    root = DesignNode(
        kind="container",
        name="Two Column Section",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node("image", "photo", x=0, y=0, width=770, height=960),
            _node(
                "shape",
                "right-surface",
                x=771,
                y=0,
                width=1149,
                height=960,
                background="rgba(230, 230, 230, 1)",
            ),
            _node("text", "food", x=177, y=78, width=74, height=29, text="FOOD"),
            _node("text", "label", x=974, y=72, width=185, height=36, text="Happenings."),
            _node("text", "title", x=974, y=129, width=619, height=180, text="Title"),
            _node("text", "body", x=974, y=341, width=674, height=80, text="Body"),
            _node("text", "more", x=974, y=760, width=64, height=24, text="MORE"),
        ],
    )

    result = compile_responsive_layout(root)

    assert result.style.layout_direction == "vertical"
    assert result.children
    composition = result.children[0]
    assert composition.style.layout_direction == "horizontal"
    assert len(composition.children) == 2

    left_region, right_region = composition.children
    assert left_region.style.width == 770
    assert right_region.style.width == 1149
    assert right_region.style.background == "rgba(230, 230, 230, 1)"

    left_ids = {node.source_id for node in _walk(left_region)}
    right_ids = {node.source_id for node in _walk(right_region)}
    assert {"photo", "food"}.issubset(left_ids)
    assert {"label", "title", "body", "more"}.issubset(right_ids)
    assert "right-surface" not in {node.source_id for node in _walk(result)}

    semantic_ids = {"food", "label", "title", "body", "more"}
    for node in _walk(result):
        if node.source_id in semantic_ids:
            assert node.style.position_mode != "absolute"


def test_foreground_shape_overlap_still_preserves_overlap_safety_fallback():
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1000, height=600),
        children=[
            _node("shape", "card", x=100, y=100, width=240, height=120, background="rgba(255, 255, 255, 1)"),
            _node("text", "overlap-a", x=110, y=110, width=200, height=60, text="A"),
            _node("text", "overlap-b", x=115, y=115, width=190, height=55, text="B"),
            _node("text", "other", x=600, y=400, width=100, height=30, text="Other"),
        ],
    )

    result = compile_responsive_layout(root)

    # This small foreground shape does not qualify as a backing surface, so
    # the existing heavy-overlap safety guard still prevents flow inference.
    assert result.style.layout_direction is None
    assert result.style.width == 1000
    assert result.style.height == 600
