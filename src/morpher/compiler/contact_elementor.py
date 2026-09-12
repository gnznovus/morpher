from __future__ import annotations

from morpher.ir.nodes import DesignNode


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _contains_center(container: DesignNode, child: DesignNode) -> bool:
    outer = _box(container)
    inner = _box(child)
    if outer is None or inner is None:
        return False
    center_x = (inner[0] + inner[2]) / 2.0
    center_y = (inner[1] + inner[3]) / 2.0
    return outer[0] <= center_x <= outer[2] and outer[1] <= center_y <= outer[3]


def _area(node: DesignNode) -> float:
    box = _box(node)
    if box is None:
        return float("inf")
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _mark_submit_border(parent: DesignNode) -> None:
    submits = [
        child
        for child in parent.children
        if child.kind == "text" and (child.text or "").strip().upper() == "SUBMIT"
    ]
    if not submits:
        return

    for submit in submits:
        candidates = [
            child
            for child in parent.children
            if child.kind == "shape"
            and child.style.stroke_color
            and _contains_center(child, submit)
        ]
        if not candidates:
            continue
        border = min(candidates, key=_area)
        weight = border.style.stroke_weight if border.style.stroke_weight is not None else 1.0
        border.style.border_top_width = weight
        border.style.border_right_width = weight
        border.style.border_bottom_width = 0.0
        border.style.border_left_width = weight


def apply_contact_elementor_intent(root: DesignNode) -> DesignNode:
    """Attach narrow Elementor intent recovered by Contact normalization.

    Contact/icon rows keep their inner Alignment at Start while centering the row
    itself in its owning column. Newsletter submit borders preserve the authored
    top/right/left stroke but intentionally omit the bottom edge.
    """

    def visit(node: DesignNode) -> None:
        if node.kind == "container" and "::contact-item-" in (node.source_id or ""):
            node.style.layout_align = "center"

        if node.children:
            _mark_submit_border(node)
            for child in node.children:
                visit(child)

    visit(root)
    return root
