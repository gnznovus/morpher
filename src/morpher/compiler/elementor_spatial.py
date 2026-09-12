from __future__ import annotations

import math
from copy import deepcopy

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


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


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _normalize_compact_leading_graphic_control(node: DesignNode) -> None:
    """Recover a simple inline control authored as overlapping vectors plus text.

    A common Figma pattern builds a leading mark from multiple overlapping VECTOR
    nodes (for example, a chevron drawn over a horizontal rule) beside one label.
    Keeping every child absolute makes the label width depend on the remaining parent
    space and can wrap an authored single-line control. Preserve the graphic as one
    small local composition, then let the label participate in one horizontal row.
    """
    if node.kind != "container" or node.style.layout_direction is not None:
        return
    if node.style.width in (None, 0) or node.style.height in (None, 0):
        return

    texts = [child for child in node.children if child.kind == "text"]
    graphics = [child for child in node.children if child.kind == "icon"]
    if len(texts) != 1 or len(graphics) < 2 or len(texts) + len(graphics) != len(node.children):
        return

    label = texts[0]
    label_box = _box(label)
    graphic_boxes = [_box(child) for child in graphics]
    if label_box is None or any(box is None for box in graphic_boxes):
        return

    graphic_left = min(box[0] for box in graphic_boxes if box is not None)
    graphic_top = min(box[1] for box in graphic_boxes if box is not None)
    graphic_right = max(box[2] for box in graphic_boxes if box is not None)
    graphic_bottom = max(box[3] for box in graphic_boxes if box is not None)
    graphic_width = graphic_right - graphic_left
    graphic_height = graphic_bottom - graphic_top

    if graphic_right > label_box[0] + 1.0:
        return
    gap = label_box[0] - graphic_right
    font_size = label.style.font_size or label.style.height or node.style.height
    if gap < -1.0 or gap > max(font_size * 1.5, node.style.height * 1.5):
        return

    # Keep this intentionally narrow: the parent should itself look like one compact
    # control, not a general-purpose icon/text layout region.
    if node.style.height > max(label.style.height or 0.0, graphic_height) * 2.0:
        return

    graphic = DesignNode(
        kind="container",
        name="Leading graphic",
        source_id=f"{node.source_id or 'control'}:leading-graphic",
        source_type="MORPHER_COMPOSITE",
        style=DesignStyle(
            x=graphic_left,
            y=graphic_top,
            width=graphic_width,
            height=graphic_height,
            width_mode="fixed",
            height_mode="fixed",
        ),
        children=graphics,
    )

    label.style.width_mode = "hug"
    label.style.text_auto_resize = "WIDTH_AND_HEIGHT"
    node.style.layout_direction = "horizontal"
    node.style.counter_axis_align = "center"
    node.style.gap = gap
    node.children = [graphic, label]


def compile_elementor_spatial_structure(root: DesignNode) -> DesignNode:
    """Prepare authored spatial details that need Elementor-specific normalization.

    Rotated labels remain siblings of nearby decorative surfaces, matching the Figma
    structure. Their already-rotated Figma bounds are converted back to Elementor's
    pre-transform geometry. Rotated Figma LINE nodes get the same treatment so the
    divider widget can apply the authored transform without shifting its visual box.
    Compact vector-built leading marks beside a single label are reconstructed as one
    inline control so authored single-line labels do not wrap arbitrarily.
    """
    compiled = deepcopy(root)

    def visit(node: DesignNode) -> None:
        _normalize_quarter_turn_text(node)
        _normalize_vertical_divider(node)
        _normalize_compact_leading_graphic_control(node)
        for child in node.children:
            visit(child)

    visit(compiled)
    return compiled
