from __future__ import annotations

import math
from copy import deepcopy

from morpher.ir.nodes import DesignNode


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
    """Prepare authored spatial details that need Elementor-specific normalization.

    Rotated labels intentionally remain siblings of nearby decorative surfaces.
    Elementor applies transforms after layout, so nesting those labels inside narrow
    rails constrains or clips their pre-transform box. Rotated Figma LINE nodes are
    converted back to their pre-rotation horizontal geometry so Elementor's divider
    widget can render the line and then apply the authored rotation reliably.
    """
    compiled = deepcopy(root)

    def visit(node: DesignNode) -> None:
        for child in node.children:
            _normalize_vertical_divider(child)
            visit(child)

    _normalize_vertical_divider(compiled)
    visit(compiled)
    return compiled
