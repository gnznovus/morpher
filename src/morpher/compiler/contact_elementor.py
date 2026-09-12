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


def _walk(root: DesignNode) -> list[DesignNode]:
    nodes: list[DesignNode] = []

    def visit(node: DesignNode) -> None:
        nodes.append(node)
        for child in node.children:
            visit(child)

    visit(root)
    return nodes


def _mark_submit_border(root: DesignNode) -> None:
    """Find the tightest stroked box around SUBMIT regardless of tree ownership.

    Figma frequently places the label and its stroked rectangle in different nested
    groups even though they occupy the same authored region. Geometry is the stronger
    relationship here, so compare all visible IR nodes in the final Elementor tree.
    """
    nodes = _walk(root)
    submits = [
        node
        for node in nodes
        if node.kind == "text" and (node.text or "").strip().upper() == "SUBMIT"
    ]
    shapes = [
        node
        for node in nodes
        if node.kind == "shape" and node.style.stroke_color and _box(node) is not None
    ]

    for submit in submits:
        candidates = [shape for shape in shapes if _contains_center(shape, submit)]
        if not candidates:
            continue
        border = min(candidates, key=_area)
        weight = border.style.stroke_weight if border.style.stroke_weight is not None else 1.0
        border.style.border_top_width = weight
        border.style.border_right_width = weight
        border.style.border_bottom_width = 0.0
        border.style.border_left_width = weight


def _apply_contact_pair_alignment(root: DesignNode) -> None:
    """Center generated pair containers in their owner, not inside themselves.

    The owning container gets Align Items: Center. Each generated icon/wording pair
    keeps its own Alignment at Start so the pair's children retain authored row
    behavior.
    """

    def visit(parent: DesignNode) -> None:
        contact_items = [
            child
            for child in parent.children
            if child.kind == "container"
            and "::contact-item-" in (child.source_id or "")
        ]
        if contact_items:
            parent.style.counter_axis_align = "center"
            for item in contact_items:
                item.style.counter_axis_align = "min"
                item.style.layout_align = None

        for child in parent.children:
            if child.kind == "container":
                visit(child)

    visit(root)


def apply_contact_elementor_intent(root: DesignNode) -> DesignNode:
    """Attach narrow Elementor intent to the final Contact-oriented IR tree.

    Owners of generated contact/amenity pairs use Align Items: Center. Each pair
    container itself keeps Alignment at Start. Newsletter submit borders keep the
    authored top/right/left stroke but intentionally omit the bottom edge.
    """
    _apply_contact_pair_alignment(root)
    _mark_submit_border(root)
    return root
