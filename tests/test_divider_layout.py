from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def test_divider_keeps_spatial_order_in_compiled_flow():
    root = DesignNode(
        kind="container",
        name="Section",
        source_id="section",
        style=DesignStyle(x=0, y=0, width=1920, height=960),
        children=[
            DesignNode(kind="text", source_id="label", text="Offers.", style=DesignStyle(x=179, y=50, width=104, height=36)),
            DesignNode(kind="text", source_id="nav", text="STAY", style=DesignStyle(x=179, y=107, width=188, height=60)),
            DesignNode(kind="divider", source_id="line", style=DesignStyle(x=0, y=183, width=1920, height=0, stroke_color="rgba(255, 255, 255, 0.5)", stroke_weight=1)),
            DesignNode(kind="text", source_id="title", text="Staycation", style=DesignStyle(x=1129, y=258, width=617, height=85)),
        ],
    )

    compiled = compile_responsive_layout(root)
    ordered_ids = [child.source_id for child in compiled.children if child.kind != "container"]

    assert "line" in ordered_ids
    assert ordered_ids.index("nav") < ordered_ids.index("line") < ordered_ids.index("title")
    divider = next(child for child in compiled.children if child.source_id == "line")
    assert divider.style.position_mode is None
    assert divider.style.x is None
    assert divider.style.y is None
