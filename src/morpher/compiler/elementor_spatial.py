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
    """Recover the pre-transform box Elementor needs for 90-degree text."""
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


def _atomic_layout_score(node: DesignNode) -> int:
    """Score a compact Figma group that should move as one layout object.

    This intentionally uses structure + geometry only. It does not inspect names or
    label text, so the rule can recover arrow labels, compact CTAs, badges, and other
    small authored controls without page-specific knowledge.
    """
    if node.kind != "container" or node.style.layout_direction is not None:
        return 0
    if node.style.width in (None, 0) or node.style.height in (None, 0):
        return 0
    if not 2 <= len(node.children) <= 5:
        return 0

    texts = [child for child in node.children if child.kind == "text"]
    visuals = [child for child in node.children if child.kind in {"icon", "divider", "shape"}]
    if len(texts) != 1 or len(texts) + len(visuals) != len(node.children):
        return 0

    label = texts[0]
    label_box = _box(label)
    visual_boxes = [_box(child) for child in visuals]
    if label_box is None or not visual_boxes or any(box is None for box in visual_boxes):
        return 0

    text = (label.text or "").strip()
    if not text or "\n" in text or len(text) > 48:
        return 0

    left = min(box[0] for box in visual_boxes if box is not None)
    top = min(box[1] for box in visual_boxes if box is not None)
    right = max(box[2] for box in visual_boxes if box is not None)
    bottom = max(box[3] for box in visual_boxes if box is not None)
    visual_width = right - left
    visual_height = bottom - top

    score = 0

    # Same immediate Figma parent is implicit here because we only inspect children.
    score += 2

    # One short editable label plus only small graphic primitives.
    score += 1
    if len(visuals) <= 3:
        score += 1

    # The visual cluster should lead the text, not overlap or surround it.
    if right <= label_box[0] + 1.0:
        score += 2
    else:
        return 0

    gap = label_box[0] - right
    font_size = label.style.font_size or label.style.height or node.style.height
    if -1.0 <= gap <= max(font_size * 1.5, node.style.height * 1.5):
        score += 2
    else:
        return 0

    # Their vertical centers should read as one row.
    label_center = (label_box[1] + label_box[3]) / 2.0
    visual_center = (top + bottom) / 2.0
    center_tolerance = max(label.style.height or 0.0, visual_height, font_size) * 0.75
    if abs(label_center - visual_center) <= center_tolerance:
        score += 2

    # Reject general-purpose content regions. Atomic controls should be compact.
    content_height = max(label.style.height or 0.0, visual_height)
    if node.style.height <= max(content_height * 2.0, font_size * 2.0):
        score += 1
    else:
        return 0

    if visual_width <= node.style.width * 0.75:
        score += 1

    return score


def _normalize_atomic_layout_group(node: DesignNode) -> None:
    """Keep a compact multi-part Figma control together as one Elementor row.

    The outer group becomes the atomic layout participant. Its internals remain native
    and editable: the visual pieces stay graphics and the label stays text. We give the
    single-line label a small font-metric allowance because browser/Elementor metrics
    can be slightly wider than Figma's measured text box.
    """
    if _atomic_layout_score(node) < 9:
        return

    label = next(child for child in node.children if child.kind == "text")
    visuals = [child for child in node.children if child.kind in {"icon", "divider", "shape"}]
    label_box = _box(label)
    visual_boxes = [_box(child) for child in visuals]
    if label_box is None or any(box is None for box in visual_boxes):
        return

    visual_left = min(box[0] for box in visual_boxes if box is not None)
    visual_top = min(box[1] for box in visual_boxes if box is not None)
    visual_right = max(box[2] for box in visual_boxes if box is not None)
    visual_bottom = max(box[3] for box in visual_boxes if box is not None)
    visual_width = visual_right - visual_left
    visual_height = visual_bottom - visual_top
    gap = max(0.0, label_box[0] - visual_right)

    graphic = DesignNode(
        kind="container",
        name="Atomic leading graphic",
        source_id=f"{node.source_id or 'control'}:atomic-leading-graphic",
        source_type="MORPHER_COMPOSITE",
        style=DesignStyle(
            x=visual_left,
            y=visual_top,
            width=visual_width,
            height=visual_height,
            width_mode="fixed",
            height_mode="fixed",
        ),
        children=visuals,
    )

    # Figma and browser font metrics are not pixel-identical. A half-em allowance is
    # enough to preserve the authored single line without materially changing layout.
    font_size = label.style.font_size or label.style.height or 0.0
    width_allowance = font_size * 0.5
    if label.style.width is not None:
        label.style.width += width_allowance
    label.style.width_mode = "fixed"
    label.style.text_auto_resize = None

    if node.style.width is not None:
        node.style.width += width_allowance
    node.style.layout_direction = "horizontal"
    node.style.counter_axis_align = "center"
    node.style.gap = gap
    node.children = [graphic, label]


def compile_elementor_spatial_structure(root: DesignNode) -> DesignNode:
    """Prepare authored spatial details that need Elementor-specific normalization.

    Rotated labels and lines recover their pre-transform geometry. Compact groups made
    from a short label plus nearby visual primitives are treated as atomic layout
    objects: they move as one unit while keeping their internal text editable.
    """
    compiled = deepcopy(root)

    def visit(node: DesignNode) -> None:
        _normalize_quarter_turn_text(node)
        _normalize_vertical_divider(node)
        _normalize_atomic_layout_group(node)
        for child in node.children:
            visit(child)

    visit(compiled)
    return compiled
