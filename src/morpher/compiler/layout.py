from __future__ import annotations

from copy import deepcopy
from statistics import median

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _has_box(node: DesignNode) -> bool:
    style = node.style
    return all(value is not None for value in (style.x, style.y, style.width, style.height))


def _bounds(node: DesignNode) -> tuple[float, float, float, float]:
    style = node.style
    assert style.x is not None and style.y is not None
    assert style.width is not None and style.height is not None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _overlap_area(a: DesignNode, b: DesignNode) -> float:
    ax1, ay1, ax2, ay2 = _bounds(a)
    bx1, by1, bx2, by2 = _bounds(b)
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    return width * height


def _has_real_overlap(children: list[DesignNode]) -> bool:
    for index, child in enumerate(children):
        area = (child.style.width or 0) * (child.style.height or 0)
        if area <= 0:
            continue
        for other in children[index + 1 :]:
            other_area = (other.style.width or 0) * (other.style.height or 0)
            if other_area <= 0:
                continue
            overlap = _overlap_area(child, other)
            if overlap / min(area, other_area) > 0.2:
                return True
    return False


def _vertical_overlap(a: DesignNode, b: DesignNode) -> float:
    _, ay1, _, ay2 = _bounds(a)
    _, by1, _, by2 = _bounds(b)
    return max(0.0, min(ay2, by2) - max(ay1, by1))


def _same_band(a: DesignNode, b: DesignNode) -> bool:
    overlap = _vertical_overlap(a, b)
    shorter = min(a.style.height or 0, b.style.height or 0)
    return shorter > 0 and overlap / shorter >= 0.25


def _bands(children: list[DesignNode]) -> list[list[DesignNode]]:
    ordered = sorted(children, key=lambda node: (node.style.y or 0, node.style.x or 0))
    bands: list[list[DesignNode]] = []
    for child in ordered:
        for band in bands:
            if any(_same_band(child, existing) for existing in band):
                band.append(child)
                break
        else:
            bands.append([child])

    for band in bands:
        band.sort(key=lambda node: node.style.x or 0)
    bands.sort(key=lambda band: min(node.style.y or 0 for node in band))
    return bands


def _positive_median(values: list[float]) -> float | None:
    positive = [value for value in values if value > 0]
    return float(median(positive)) if positive else None


def _flow_style(style: DesignStyle, *, width_percent: float | None = None) -> DesignStyle:
    result = deepcopy(style)
    result.x = None
    result.y = None
    result.width_percent = width_percent
    result.width_mode = "fill" if width_percent is None else None
    if result.height_mode == "fixed":
        result.height_mode = "hug"
    return result


def _compile_free_layout(node: DesignNode) -> DesignNode:
    children = node.children
    if len(children) < 2 or not all(_has_box(child) for child in children):
        return node
    if _has_real_overlap(children):
        # Overlap is a signal that the design may genuinely require layering.
        # Keep the raw free-layout geometry instead of fabricating a flow layout.
        return node

    parent_style = node.style
    if not _has_box(node):
        return node

    bands = _bands(children)
    if not bands:
        return node

    px, py, pr, pb = _bounds(node)
    child_bounds = [_bounds(child) for child in children]
    min_x = min(box[0] for box in child_bounds)
    min_y = min(box[1] for box in child_bounds)
    max_x = max(box[2] for box in child_bounds)
    max_y = max(box[3] for box in child_bounds)

    compiled_children: list[DesignNode] = []
    band_boxes: list[tuple[float, float, float, float]] = []

    for band_index, band in enumerate(bands):
        boxes = [_bounds(child) for child in band]
        bx1 = min(box[0] for box in boxes)
        by1 = min(box[1] for box in boxes)
        bx2 = max(box[2] for box in boxes)
        by2 = max(box[3] for box in boxes)
        band_boxes.append((bx1, by1, bx2, by2))

        if len(band) == 1:
            child = band[0]
            child.style = _flow_style(child.style)
            compiled_children.append(child)
            continue

        widths = [child.style.width or 0 for child in band]
        total_width = sum(widths)
        gaps = []
        for left, right in zip(band, band[1:]):
            assert left.style.x is not None and left.style.width is not None and right.style.x is not None
            gaps.append(right.style.x - (left.style.x + left.style.width))

        row_children: list[DesignNode] = []
        for child, width in zip(band, widths):
            percent = (width / total_width * 100.0) if total_width > 0 else None
            child.style = _flow_style(child.style, width_percent=percent)
            row_children.append(child)

        row = DesignNode(
            kind="container",
            name=f"{node.name or 'section'} row {band_index + 1}",
            source_id=f"{node.source_id or 'node'}::row-{band_index + 1}",
            style=DesignStyle(
                layout_direction="horizontal",
                width_mode="fill",
                height_mode="hug",
                gap=_positive_median(gaps),
                counter_axis_align="min",
            ),
            children=row_children,
        )
        compiled_children.append(row)

    vertical_gaps = [
        current[1] - previous[3]
        for previous, current in zip(band_boxes, band_boxes[1:])
    ]

    compiled_style = deepcopy(parent_style)
    compiled_style.x = None
    compiled_style.y = None
    compiled_style.width = None
    compiled_style.height = None
    compiled_style.layout_direction = "vertical"
    compiled_style.width_mode = "fill"
    compiled_style.height_mode = "hug"
    compiled_style.gap = _positive_median(vertical_gaps)
    compiled_style.padding_left = max(0.0, min_x - px)
    compiled_style.padding_top = max(0.0, min_y - py)
    compiled_style.padding_right = max(0.0, pr - max_x)
    compiled_style.padding_bottom = max(0.0, pb - max_y)

    node.style = compiled_style
    node.children = compiled_children
    return node


def _compile_node(node: DesignNode) -> DesignNode:
    node.children = [_compile_node(child) for child in node.children]
    if node.kind == "container" and node.style.layout_direction is None:
        node = _compile_free_layout(node)
    return node


def compile_responsive_layout(root: DesignNode) -> DesignNode:
    """Compile non-overlapping Figma free-layout geometry into responsive flow.

    Auto Layout is already semantic and passes through unchanged. Free-layout
    containers are converted only when sibling geometry can be represented as
    vertical bands and horizontal rows without overlap. Ambiguous/layered
    containers deliberately remain free layout for a later specialized rule.
    """
    return _compile_node(deepcopy(root))
