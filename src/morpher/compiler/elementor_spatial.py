from __future__ import annotations

import math
from copy import deepcopy

from morpher.ir.nodes import DesignNode


def _is_quarter_turn_text(node: DesignNode) -> bool:
    if node.kind != "text" or node.style.rotation is None:
        return False
    return abs(abs(node.style.rotation) - math.pi / 2) <= 0.05


def _normalize_quarter_turn_text(node: DesignNode) -> None:
    """Recover the pre-transform box Elementor needs for 90-degree text.

    Figma's absoluteBoundingBox is the already-rotated visual box. Elementor lays the
    widget out first and applies rotation afterwards, so feeding the rotated 24x192
    box directly to Elementor shifts the visible label away from its authored place.
    Rebuild the unrotated 192x24 box around the same center before applying rotation.
    """
    if not _is_quarter_turn_text(node):
        return

    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return

    center_x = style.x + style.width / 2.0
    center_y = style.y + style.height / 2.0
    logical_width = style.height
    logical_height = style.width

    style.x = center_x - logical_width / 2.0
    style.y = center_y - logical_height / 2.0
    style.width = logical_width
    style.height = logical_height
    style.text_auto_resize = None
    style.width_mode = "fixed"


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

    Rotated labels remain siblings of nearby decorative surfaces, matching the Figma
    structure. Their already-rotated Figma bounds are converted back to Elementor's
    pre-transform geometry. Rotated Figma LINE nodes get the same treatment so the
    divider widget can apply the authored transform without shifting its visual box.
    """
    compiled = deepcopy(root)

    def visit(node: DesignNode) -> None:
        _normalize_quarter_turn_text(node)
        _normalize_vertical_divider(node)
        for child in node.children:
            visit(child)

    visit(compiled)
    return compiled
