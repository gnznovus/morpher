from __future__ import annotations

import math
from copy import deepcopy

from morpher.ir.nodes import DesignNode


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _contains(outer: DesignNode, inner: DesignNode, tolerance: float = 1.0) -> bool:
    outer_box = _box(outer)
    inner_box = _box(inner)
    if outer_box is None or inner_box is None:
        return False
    return (
        inner_box[0] >= outer_box[0] - tolerance
        and inner_box[1] >= outer_box[1] - tolerance
        and inner_box[2] <= outer_box[2] + tolerance
        and inner_box[3] <= outer_box[3] + tolerance
    )


def _is_narrow_vertical_surface(node: DesignNode, parent: DesignNode) -> bool:
    if node.kind != "shape" or not node.style.background:
        return False
    if any(value in (None, 0) for value in (node.style.width, node.style.height, parent.style.width, parent.style.height)):
        return False
    return (
        node.style.width <= parent.style.width * 0.12
        and node.style.height >= parent.style.height * 0.6
    )


def _is_rotated_rail_text(node: DesignNode) -> bool:
    if node.kind != "text" or node.style.rotation is None:
        return False
    return abs(abs(node.style.rotation) - math.pi / 2) <= 0.05


def _own_rail_text(parent: DesignNode) -> None:
    consumed: set[int] = set()
    for surface in parent.children:
        if not _is_narrow_vertical_surface(surface, parent):
            continue
        owned = [
            child
            for child in parent.children
            if child is not surface
            and _is_rotated_rail_text(child)
            and _contains(surface, child)
        ]
        if not owned:
            continue
        surface.kind = "container"
        surface.children.extend(deepcopy(child) for child in owned)
        consumed.update(id(child) for child in owned)

    if consumed:
        parent.children = [child for child in parent.children if id(child) not in consumed]


def _normalize_vertical_divider(node: DesignNode) -> None:
    if node.kind != "divider":
        return
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height, style.rotation)):
        return
    if abs(abs(style.rotation) - math.pi / 2) > 0.05:
        return
    weight = style.stroke_weight or 1.0
    if style.width > max(weight * 2.0, 2.0) or style.height <= max(style.width * 4.0, 8.0):
        return

    length = style.height
    half_delta = (length - weight) / 2.0
    style.x -= half_delta
    style.y += half_delta
    style.width = length
    style.height = weight


def compile_elementor_spatial_structure(root: DesignNode) -> DesignNode:
    """Prepare a small set of authored spatial relationships for Elementor.

    Narrow side-rail surfaces can own rotated labels that are visually contained
    by them, giving Elementor the same ownership the design implies. Rotated Figma
    LINE nodes are also converted back to their pre-rotation horizontal geometry so
    Elementor's divider widget can render the line and then apply the authored
    rotation reliably in preview mode.
    """
    compiled = deepcopy(root)

    def visit(node: DesignNode) -> None:
        _own_rail_text(node)
        for child in node.children:
            _normalize_vertical_divider(child)
            visit(child)

    _normalize_vertical_divider(compiled)
    visit(compiled)
    return compiled
