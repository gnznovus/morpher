from morpher.compiler.contact_elementor import apply_contact_elementor_intent
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor_overrides import render_elementor_with_ir_overrides


def test_contact_owner_centers_items_while_pair_keeps_start_alignment():
    item = DesignNode(
        kind="container",
        source_id="contact::contact-item-1",
        style=DesignStyle(
            width=200,
            height=30,
            layout_direction="horizontal",
            width_mode="hug",
            counter_axis_align="min",
        ),
    )
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(width=1000, height=600, layout_direction="vertical", counter_axis_align="min"),
        children=[item],
    )

    apply_contact_elementor_intent(root)
    elementor = render_elementor_with_ir_overrides(root)
    rendered_root = elementor["content"][0]
    rendered_item = rendered_root["elements"][0]

    assert root.style.counter_axis_align == "center"
    assert item.style.counter_axis_align == "min"
    assert item.style.layout_align is None
    assert rendered_root["settings"]["flex_align_items"] == "center"
    assert rendered_item["settings"]["flex_align_items"] == "flex-start"
    assert "align_self" not in rendered_item["settings"]


def test_submit_box_omits_only_bottom_border():
    border = DesignNode(
        kind="shape",
        source_id="submit-border",
        style=DesignStyle(
            x=500,
            y=200,
            width=150,
            height=50,
            stroke_color="rgba(255, 255, 255, 1)",
            stroke_weight=2,
        ),
    )
    submit = DesignNode(
        kind="text",
        source_id="submit",
        text="SUBMIT",
        style=DesignStyle(x=535, y=212, width=80, height=24),
    )
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=0, y=0, width=1000, height=600),
        children=[border, submit],
    )

    apply_contact_elementor_intent(root)
    elementor = render_elementor_with_ir_overrides(root)
    rendered_border = elementor["content"][0]["elements"][0]
    width = rendered_border["settings"]["_border_width"]

    assert border.style.border_top_width == 2
    assert border.style.border_right_width == 2
    assert border.style.border_bottom_width == 0
    assert border.style.border_left_width == 2
    assert width == {
        "unit": "px",
        "top": "2",
        "right": "2",
        "bottom": "0.0",
        "left": "2",
        "isLinked": False,
    }
