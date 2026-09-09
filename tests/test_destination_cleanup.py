from morpher.compiler.layout import compile_responsive_layout
from morpher.compiler.overlays import resolve_inferred_region_overlays
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _find(node: DesignNode, source_id: str) -> DesignNode:
    if node.source_id == source_id:
        return node
    for child in node.children:
        try:
            return _find(child, source_id)
        except LookupError:
            pass
    raise LookupError(source_id)


def test_destination_reanchors_media_overlay_and_preserves_intrinsic_counter():
    root = DesignNode(
        kind="container",
        name="Destination",
        source_id="45:5282",
        style=DesignStyle(x=0, y=1920, width=1920, height=960),
        children=[
            DesignNode(kind="text", source_id="45:5284", text="Destination.", style=DesignStyle(x=179, y=2091, width=184, height=36)),
            DesignNode(kind="text", source_id="45:5285", text="Heading", style=DesignStyle(x=179, y=2148, width=716, height=120)),
            DesignNode(kind="text", source_id="45:5286", text="Intro", style=DesignStyle(x=179, y=2289, width=701, height=86)),
            DesignNode(kind="text", source_id="45:5287", text="Body", style=DesignStyle(x=179, y=2413, width=768, height=246)),
            DesignNode(kind="icon", source_id="45:5288", style=DesignStyle(x=179, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="icon", source_id="45:5289", style=DesignStyle(x=726, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="text", source_id="45:5290", text="01 / 02", style=DesignStyle(x=492, y=2791, width=79, height=36, text_auto_resize="WIDTH_AND_HEIGHT")),
            DesignNode(kind="image", source_id="45:5291", style=DesignStyle(x=1129, y=2014, width=486, height=865)),
            DesignNode(kind="image", source_id="45:5292", style=DesignStyle(x=1618, y=2014, width=486, height=865)),
            DesignNode(kind="icon", source_id="45:5293", style=DesignStyle(x=1789, y=2375, width=144, height=144)),
        ],
    )

    compiled = compile_responsive_layout(root)
    compiled = resolve_inferred_region_overlays(compiled, 1920)

    counter = _find(compiled, "45:5290")
    assert counter.style.width_mode == "hug"
    assert counter.style.width_percent is None

    play = _find(compiled, "45:5293")
    assert play.style.position_mode is None
    assert play.style.offset_x is None
    assert play.style.offset_y is None
    assert round(play.style.width_percent or 0, 3) == 7.5
    assert round(play.style.margin_left_percent or 0, 3) == 67.692
    assert round(play.style.margin_top_percent or 0, 3) == -51.692
    assert round(play.style.margin_bottom_percent or 0, 3) == 36.923
