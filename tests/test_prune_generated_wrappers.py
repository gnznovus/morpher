from morpher.compiler.prune import prune_empty_generated_wrappers
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def test_prunes_only_empty_generated_wrappers():
    figma_empty = DesignNode(kind="container", source_id="45:empty")
    empty_region = DesignNode(kind="container", source_id="root::region-empty")
    empty_row = DesignNode(kind="container", source_id="root::row-empty")
    visual_generated = DesignNode(
        kind="container",
        source_id="root::region-background",
        style=DesignStyle(background="rgba(0, 0, 0, 1)"),
    )
    populated_region = DesignNode(
        kind="container",
        source_id="root::region-content",
        children=[DesignNode(kind="text", source_id="title", text="Title")],
    )
    nested_empty = DesignNode(kind="container", source_id="root::region-outer", children=[empty_row])
    root = DesignNode(
        kind="container",
        source_id="root",
        children=[figma_empty, empty_region, visual_generated, populated_region, nested_empty],
    )

    result = prune_empty_generated_wrappers(root)

    assert [child.source_id for child in result.children] == [
        "45:empty",
        "root::region-background",
        "root::region-content",
    ]
