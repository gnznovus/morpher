from morpher.compiler.overlays import resolve_compiled_spatial_relationships
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x, y, width, height, text=None, auto_resize=None):
    return DesignNode(
        kind=kind,
        source_id=source_id,
        text=text,
        style=DesignStyle(
            x=x,
            y=y,
            width=width,
            height=height,
            text_auto_resize=auto_resize,
        ),
    )


def _find(node, source_id):
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def test_bottom_control_trio_is_detached_from_content_region():
    source = DesignNode(
        kind="container",
        source_id="section",
        style=DesignStyle(x=0, y=2881, width=1920, height=960),
        children=[
            _node("text", "content", x=1129, y=3490, width=561, height=24, text="More about"),
            _node("text", "cta", x=1129, y=3672, width=278, height=24, text="SPECIAL OFFER ENQUIRY"),
            _node("icon", "left", x=608, y=3761, width=156.86, height=18.44),
            _node("text", "counter", x=921, y=3752, width=80, height=36, text="01 / 03", auto_resize="WIDTH_AND_HEIGHT"),
            _node("icon", "right", x=1155, y=3761, width=156.86, height=18.44),
        ],
    )

    content_region = DesignNode(
        kind="container",
        source_id="section::region-content",
        style=DesignStyle(layout_direction="vertical", width_percent=40, margin_left_percent=58),
        children=[
            DesignNode(kind="text", source_id="content", text="More about"),
            DesignNode(kind="text", source_id="cta", text="SPECIAL OFFER ENQUIRY"),
            DesignNode(kind="icon", source_id="left"),
            DesignNode(kind="text", source_id="counter", text="01 / 03"),
            DesignNode(kind="icon", source_id="right"),
        ],
    )
    compiled = DesignNode(
        kind="container",
        source_id="section",
        style=DesignStyle(width=1920, layout_direction="vertical"),
        children=[content_region],
    )

    result = resolve_compiled_spatial_relationships(compiled, source, 1920)

    pagination = _find(result, "section::bottom-controls")
    assert pagination is not None
    assert pagination in result.children
    assert pagination.style.layout_direction == "horizontal"
    assert pagination.style.primary_axis_align == "space_between"
    assert [child.source_id for child in pagination.children] == ["left", "counter", "right"]
    assert _find(content_region, "left") is None
    assert _find(content_region, "counter") is None
    assert _find(content_region, "right") is None


def test_bottom_control_trio_stays_inside_shared_inferred_region_without_auto_resize_metadata():
    source = DesignNode(
        kind="container",
        source_id="section",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            _node("text", "body", x=974, y=340, width=700, height=240, text="Body"),
            _node("icon", "left", x=970, y=850, width=156.86, height=18.44),
            _node("text", "counter", x=1283, y=841, width=79, height=36, text="01 / 02"),
            _node("icon", "right", x=1517, y=850, width=156.86, height=18.44),
        ],
    )

    left_region = DesignNode(
        kind="container",
        source_id="section::region-1",
        style=DesignStyle(layout_direction="vertical", width_percent=770 / 1920 * 100),
        children=[DesignNode(kind="image", source_id="photo")],
    )
    right_region = DesignNode(
        kind="container",
        source_id="section::region-2",
        style=DesignStyle(layout_direction="vertical", width_percent=1149 / 1920 * 100),
        children=[
            DesignNode(kind="text", source_id="body", text="Body"),
            DesignNode(kind="icon", source_id="left"),
            DesignNode(kind="text", source_id="counter", text="01 / 02"),
            DesignNode(kind="icon", source_id="right"),
        ],
    )
    composition = DesignNode(
        kind="container",
        source_id="section::composition-row",
        style=DesignStyle(layout_direction="horizontal", width_mode="fill", gap=1),
        children=[left_region, right_region],
    )
    compiled = DesignNode(
        kind="container",
        source_id="section",
        style=DesignStyle(width=1920, layout_direction="vertical"),
        children=[composition],
    )

    result = resolve_compiled_spatial_relationships(compiled, source, 1920)

    pagination = _find(result, "section::bottom-controls")
    assert pagination is not None
    assert pagination in right_region.children
    assert pagination not in result.children
    assert pagination.style.layout_direction == "horizontal"
    assert pagination.style.primary_axis_align == "space_between"
    assert [child.source_id for child in pagination.children] == ["left", "counter", "right"]
    assert round(pagination.style.width_percent or 0, 3) == round((1673.86 - 970) / 1149 * 100, 3)
    assert round(pagination.style.margin_left_percent or 0, 3) == round((970 - 771) / 1149 * 100, 3)
