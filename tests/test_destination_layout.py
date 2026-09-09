from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def test_destination_infers_text_and_media_regions_without_special_casing():
    root = DesignNode(
        kind="container",
        name="Destination",
        source_id="45:5282",
        style=DesignStyle(x=0, y=1920, width=1920, height=960),
        children=[
            DesignNode(kind="icon", source_id="45:5283", style=DesignStyle(x=442, y=1285, width=1233, height=1412)),
            DesignNode(kind="text", source_id="45:5284", text="Destination.", style=DesignStyle(x=179, y=2091, width=184, height=36)),
            DesignNode(kind="text", source_id="45:5285", text="– THONG LO, BANGKOK’S\nTRENDIEST DISTRICT", style=DesignStyle(x=179, y=2148, width=716, height=120)),
            DesignNode(kind="text", source_id="45:5286", text="Intro", style=DesignStyle(x=179, y=2289, width=701, height=86)),
            DesignNode(kind="text", source_id="45:5287", text="Body", style=DesignStyle(x=179, y=2413, width=768, height=246)),
            DesignNode(kind="icon", source_id="45:5288", style=DesignStyle(x=179, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="icon", source_id="45:5289", style=DesignStyle(x=726, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="text", source_id="45:5290", text="01 / 02", style=DesignStyle(x=492, y=2791, width=79, height=36)),
            DesignNode(kind="image", source_id="45:5291", style=DesignStyle(x=1129, y=2014, width=486, height=865)),
            DesignNode(kind="image", source_id="45:5292", style=DesignStyle(x=1618, y=2014, width=486, height=865)),
            DesignNode(kind="icon", source_id="45:5293", style=DesignStyle(x=1789, y=2375, width=144, height=144)),
        ],
    )

    compiled = compile_responsive_layout(root)

    assert compiled.style.layout_direction == "vertical"
    assert compiled.style.padding_top == 94
    assert len(compiled.children) == 2

    composition, backdrop = compiled.children
    assert composition.style.layout_direction == "horizontal"
    assert round(composition.style.margin_left_percent or 0, 3) == 9.323
    assert round(composition.style.gap or 0, 3) == 182
    assert len(composition.children) == 2

    left, right = composition.children
    assert round(left.style.width_percent or 0, 3) == 40.0
    assert round(right.style.width_percent or 0, 3) == 50.781
    assert round(left.style.margin_top_percent or 0, 3) == 4.01
    assert round(right.style.margin_top_percent or 0, 3) == 0

    assert left.style.layout_direction == "vertical"
    assert right.style.layout_direction == "vertical"
    pagination = next(child for child in left.children if child.kind == "container" and child.style.layout_direction == "horizontal")
    assert [child.source_id for child in pagination.children] == ["45:5288", "45:5290", "45:5289"]
    media = next(child for child in right.children if child.kind == "container" and child.style.layout_direction == "horizontal")
    assert [child.source_id for child in media.children] == ["45:5291", "45:5292"]

    assert backdrop.source_id == "45:5283"
    assert backdrop.style.position_mode == "absolute"
    play = next(child for child in right.children if child.source_id == "45:5293")
    assert play.style.position_mode == "absolute"
    assert play.style.offset_x == 660
    assert play.style.offset_y == 361
