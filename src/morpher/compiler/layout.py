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


def _union_bounds(boxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _participates_in_flow(node: DesignNode) -> bool:
    if node.kind in {"text", "shape"}:
        return True
    if node.kind == "container":
        return any(_participates_in_flow(child) for child in node.children)
    return False


def _inside_parent(node: DesignNode, parent: DesignNode) -> bool:
    if not _has_box(node) or not _has_box(parent):
        return False
    nx1, ny1, nx2, ny2 = _bounds(node)
    px1, py1, px2, py2 = _bounds(parent)
    return nx1 >= px1 and ny1 >= py1 and nx2 <= px2 and ny2 <= py2


def _is_primary_visual(node: DesignNode, parent: DesignNode) -> bool:
    """Return True for visual assets that should participate in desktop flow.

    Raster/image nodes are primary content by default. Large in-bounds vector
    assets can also anchor the composition. Small icons remain deferred so play
    controls and similar overlays do not distort band inference.
    """
    if node.kind == "image":
        return _has_box(node)
    if node.kind != "icon" or not _inside_parent(node, parent):
        return False

    nx1, ny1, nx2, ny2 = _bounds(node)
    px1, py1, px2, py2 = _bounds(parent)
    parent_area = max(0.0, px2 - px1) * max(0.0, py2 - py1)
    node_area = max(0.0, nx2 - nx1) * max(0.0, ny2 - ny1)
    return parent_area > 0 and node_area / parent_area >= 0.03


def _layout_bounds(node: DesignNode) -> tuple[float, float, float, float]:
    if node.kind == "container" and not node.style.background:
        descendant_boxes = [
            _layout_bounds(child)
            for child in node.children
            if _participates_in_flow(child) and _has_box(child)
        ]
        if descendant_boxes:
            return _union_bounds(descendant_boxes)
    return _bounds(node)


def _overlap_area(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    return width * height


def _has_real_overlap(
    children: list[DesignNode],
    boxes: dict[int, tuple[float, float, float, float]],
) -> bool:
    for index, child in enumerate(children):
        box = boxes[id(child)]
        area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
        if area <= 0:
            continue
        for other in children[index + 1 :]:
            other_box = boxes[id(other)]
            other_area = max(0.0, other_box[2] - other_box[0]) * max(0.0, other_box[3] - other_box[1])
            if other_area <= 0:
                continue
            overlap = _overlap_area(box, other_box)
            if overlap / min(area, other_area) > 0.8:
                return True
    return False


def _vertical_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    _, ay1, _, ay2 = a
    _, by1, _, by2 = b
    return max(0.0, min(ay2, by2) - max(ay1, by1))


def _same_band(
    a: DesignNode,
    b: DesignNode,
    boxes: dict[int, tuple[float, float, float, float]],
) -> bool:
    # Visual assets keep their own flow block so source overlap becomes negative
    # margin instead of an artificial side-by-side row.
    if a.kind in {"image", "icon"} or b.kind in {"image", "icon"}:
        return False
    a_box = boxes[id(a)]
    b_box = boxes[id(b)]
    overlap = _vertical_overlap(a_box, b_box)
    shorter = min(a_box[3] - a_box[1], b_box[3] - b_box[1])
    return shorter > 0 and overlap / shorter >= 0.25


def _bands(
    children: list[DesignNode],
    boxes: dict[int, tuple[float, float, float, float]],
) -> list[list[DesignNode]]:
    ordered = sorted(children, key=lambda node: (boxes[id(node)][1], boxes[id(node)][0]))
    bands: list[list[DesignNode]] = []
    for child in ordered:
        for band in bands:
            if any(_same_band(child, existing, boxes) for existing in band):
                band.append(child)
                break
        else:
            bands.append([child])

    for band in bands:
        band.sort(key=lambda node: boxes[id(node)][0])
    bands.sort(key=lambda band: min(boxes[id(node)][1] for node in band))
    return bands


def _positive_median(values: list[float]) -> float | None:
    positive = [value for value in values if value > 0]
    return float(median(positive)) if positive else None


def _percent(value: float, reference: float) -> float | None:
    if reference <= 0:
        return None
    return value / reference * 100.0


def _flow_style(
    style: DesignStyle,
    *,
    width_percent: float | None = None,
    margin_top_percent: float | None = None,
    margin_left_percent: float | None = None,
) -> DesignStyle:
    result = deepcopy(style)
    result.x = None
    result.y = None
    result.width_percent = width_percent
    result.width_mode = "fill" if width_percent is None else None
    result.margin_top_percent = margin_top_percent
    result.margin_left_percent = margin_left_percent
    if result.height_mode == "fixed":
        result.height_mode = "hug"
    return result


def _make_child_flow(
    child: DesignNode,
    *,
    width_percent: float | None = None,
    margin_top_percent: float | None = None,
    margin_left_percent: float | None = None,
) -> None:
    child.style = _flow_style(
        child.style,
        width_percent=width_percent,
        margin_top_percent=margin_top_percent,
        margin_left_percent=margin_left_percent,
    )
    if child.kind == "container" and child.style.layout_direction is None:
        child.style.layout_direction = "vertical"
        child.style.height_mode = "hug"


def _flow_container_style(
    node: DesignNode,
    child_bounds: list[tuple[float, float, float, float]],
) -> DesignStyle:
    px, py, _, pb = _bounds(node)
    min_y = min(box[1] for box in child_bounds)
    max_y = max(box[3] for box in child_bounds)

    style = deepcopy(node.style)
    style.x = None
    style.y = None
    style.width = None
    style.height = None
    style.layout_direction = "vertical"
    style.width_mode = "fill"
    style.height_mode = "hug"
    # Horizontal placement belongs to each child so desktop x/width geometry is
    # retained without absolute positioning. The parent only owns vertical inset.
    style.padding_left = 0
    style.padding_right = 0
    style.padding_top = max(0.0, min_y - py)
    style.padding_bottom = max(0.0, pb - max_y)
    style.gap = None
    return style


def _compile_free_layout(node: DesignNode) -> DesignNode:
    children = node.children
    if not children or not _has_box(node):
        return node

    flow_children = [
        child
        for child in children
        if _has_box(child) and (_participates_in_flow(child) or _is_primary_visual(child, node))
    ]
    if not flow_children:
        return node

    boxes = {id(child): _layout_bounds(child) for child in flow_children}
    original_child_bounds = list(boxes.values())
    px, _, pr, _ = _bounds(node)
    parent_width = pr - px

    if len(flow_children) == 1:
        child = flow_children[0]
        box = boxes[id(child)]
        node.style = _flow_container_style(node, original_child_bounds)
        _make_child_flow(
            child,
            width_percent=_percent(box[2] - box[0], parent_width),
            margin_left_percent=_percent(box[0] - px, parent_width),
        )
        node.children = [child, *[item for item in children if item is not child]]
        return node

    if _has_real_overlap(flow_children, boxes):
        return node

    bands = _bands(flow_children, boxes)
    if not bands:
        return node

    compiled_children: list[DesignNode] = []
    band_boxes: list[tuple[float, float, float, float]] = []

    for band_index, band in enumerate(bands):
        band_source_boxes = [boxes[id(child)] for child in band]
        bx1, by1, bx2, by2 = _union_bounds(band_source_boxes)
        current_box = (bx1, by1, bx2, by2)
        previous_box = band_boxes[-1] if band_boxes else None
        band_boxes.append(current_box)
        margin_top_percent = None
        if previous_box is not None:
            margin_top_percent = _percent(by1 - previous_box[3], parent_width)

        if len(band) == 1:
            child = band[0]
            child_box = boxes[id(child)]
            _make_child_flow(
                child,
                width_percent=_percent(child_box[2] - child_box[0], parent_width),
                margin_top_percent=margin_top_percent,
                margin_left_percent=_percent(child_box[0] - px, parent_width),
            )
            compiled_children.append(child)
            continue

        widths = [boxes[id(child)][2] - boxes[id(child)][0] for child in band]
        total_width = sum(widths)
        gaps = []
        for left, right in zip(band, band[1:]):
            left_box = boxes[id(left)]
            right_box = boxes[id(right)]
            gaps.append(right_box[0] - left_box[2])

        row_children: list[DesignNode] = []
        for child, width in zip(band, widths):
            percent = (width / total_width * 100.0) if total_width > 0 else None
            _make_child_flow(child, width_percent=percent)
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
                margin_top_percent=margin_top_percent,
            ),
            children=row_children,
        )
        compiled_children.append(row)

    compiled_style = _flow_container_style(node, original_child_bounds)

    flow_ids = {id(child) for child in flow_children}
    deferred_children = [child for child in children if id(child) not in flow_ids]

    node.style = compiled_style
    node.children = [*compiled_children, *deferred_children]
    return node


def _compile_node(node: DesignNode) -> DesignNode:
    if node.kind == "container" and node.style.layout_direction is None:
        node = _compile_free_layout(node)
    node.children = [_compile_node(child) for child in node.children]
    return node


def compile_responsive_layout(root: DesignNode) -> DesignNode:
    """Compile desktop free-layout content into normal flow.

    Auto Layout passes through unchanged. Free-layout semantic content and primary
    visual assets keep their source desktop x/width and vertical relationships
    through proportional widths and margins, including negative margins for
    intentional overlap. Small overlay assets remain deferred for specialized
    positioning rather than distorting the primary composition.
    """
    return _compile_node(deepcopy(root))
