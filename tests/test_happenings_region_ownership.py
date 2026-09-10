from morpher.compiler.contact import resolve_contact_group_ownership
from morpher.compiler.flow_groups import stabilize_compiled_flow_groups
from morpher.compiler.layout import compile_responsive_layout
from morpher.compiler.overlays import (
    resolve_compiled_spatial_relationships,
    resolve_inferred_region_overlays,
)
from morpher.compiler.prune import prune_empty_generated_wrappers
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


def _find(node, source_id):
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def _find_parent(node, target):
    if target in node.children:
        return node
    for child in node.children:
        found = _find_parent(child, target)
        if found is not None:
            return found
    return None


def test_flat_happenings_uses_root_composition_and_keeps_pagination_in_right_region():
    source = DesignNode(
        kind="container",
        name="Happennings",
        source_id="happenings",
        style=DesignStyle(x=0, y=0, width=1920, height=962),
        children=[
            _node("shape", "right-surface", x=771, y=0, width=1149, height=962, background="#e8e8e8"),
            _node("image", "photo", x=1, y=0, width=770, height=962),
            _node("text", "eyebrow", x=974, y=70, width=185, height=36, text="Happenings."),
            _node("text", "title", x=974, y=130, width=619, height=150, text="Kodawari Tsukiji"),
            _node("text", "paragraph-1", x=974, y=320, width=674, height=86, text="First paragraph"),
            _node("text", "paragraph-2", x=974, y=440, width=699, height=246, text="Second paragraph"),
            _node("text", "more", x=974, y=720, width=64, height=24, text="MORE"),
            _node("icon", "left-arrow", x=970, y=850, width=156.86, height=18.44),
            # Happenings omits Figma textAutoResize on this counter.
            _node("text", "counter", x=1283, y=841, width=79, height=36, text="01 / 02"),
            _node("icon", "right-arrow", x=1517, y=850, width=156.86, height=18.44),
            _node("icon", "rail", x=1761, y=250, width=4, height=488),
            _node("text", "food", x=177, y=79, width=74, height=29, text="FOOD"),
        ],
    )

    compiled = compile_responsive_layout(source)
    compiled = resolve_compiled_spatial_relationships(compiled, source, 1920)
    compiled = stabilize_compiled_flow_groups(compiled, source, 1920)
    compiled = resolve_contact_group_ownership(compiled, source, 1920)
    compiled = resolve_inferred_region_overlays(compiled, 1920)
    compiled = prune_empty_generated_wrappers(compiled)

    composition = _find(compiled, "happenings::composition-row")
    left_region = _find(compiled, "happenings::region-1")
    right_region = _find(compiled, "happenings::region-2")
    pagination = _find(compiled, "happenings::bottom-controls")

    assert composition is None
    assert compiled.style.layout_direction == "horizontal"
    assert left_region is not None
    assert right_region is not None
    assert pagination is not None
    assert left_region in compiled.children
    assert right_region in compiled.children
    assert pagination in right_region.children
    assert pagination not in compiled.children
    assert _find_parent(compiled, pagination) is right_region
    assert [child.source_id for child in pagination.children] == ["left-arrow", "counter", "right-arrow"]
