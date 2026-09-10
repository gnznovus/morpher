from morpher.compiler.flow_groups import stabilize_compiled_flow_groups
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _node(kind, source_id, *, x=None, y=None, width=None, height=None, text=None):
    return DesignNode(kind=kind, source_id=source_id, text=text, style=DesignStyle(x=x, y=y, width=width, height=height))


def _find(node, source_id):
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found:
            return found
    return None


def test_contact_group_does_not_repeat_wrapper_offset():
    group = DesignNode(
        kind="container",
        source_id="contact::contact-group",
        style=DesignStyle(layout_direction="vertical", width_mode="fill", margin_left_percent=58.8, margin_top_percent=2.0),
        children=[],
    )
    wrapper = DesignNode(
        kind="container",
        source_id="root::row-contact",
        style=DesignStyle(layout_direction="horizontal", width_mode="fill", margin_left_percent=58.8),
        children=[group, _node("text", "enquiry", text="SPECIAL")],
    )
    compiled = DesignNode(kind="container", source_id="root", style=DesignStyle(width=1920), children=[wrapper])
    source = DesignNode(kind="container", source_id="root", style=DesignStyle(x=0, y=2881, width=1920, height=960))

    stabilize_compiled_flow_groups(compiled, source, 1920)

    assert wrapper.style.layout_direction == "vertical"
    assert group.style.margin_left_percent is None
    assert group.style.margin_top_percent is None
    assert group.style.width_mode == "fill"


def test_bottom_icon_text_icon_row_is_kept_at_section_level():
    source = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=2881, width=1920, height=960),
        children=[
            _node("icon", "left", x=608, y=3761, width=156.86, height=18.44),
            _node("text", "count", x=921, y=3752, width=80, height=36, text="01 / 03"),
            _node("icon", "right", x=1155, y=3761, width=156.86, height=18.44),
        ],
    )
    row = DesignNode(
        kind="container",
        source_id="root::row-pagination",
        style=DesignStyle(layout_direction="horizontal", width_mode="fill", margin_left_percent=10),
        children=[_node("icon", "left"), _node("text", "count", text="01 / 03"), _node("icon", "right")],
    )
    nested = DesignNode(kind="container", source_id="root::region-1", style=DesignStyle(layout_direction="vertical"), children=[row])
    compiled = DesignNode(kind="container", source_id="root", style=DesignStyle(width=1920), children=[nested])

    stabilize_compiled_flow_groups(compiled, source, 1920)

    assert row in compiled.children
    assert row.style.primary_axis_align == "space_between"
    assert row.style.gap is None
    assert round(row.style.margin_left_percent, 3) == round(608 / 1920 * 100, 3)
    assert round(row.style.width_percent, 3) == round((1311.86 - 608) / 1920 * 100, 3)
