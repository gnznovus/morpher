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


def _area(box: tuple[float, float, float, float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _participates_in_flow(node: DesignNode) -> bool:
    if node.kind in {"text", "shape", "divider"}:
        return True
    if node.kind == "container":
        return any(_participates_in_flow(child) for child in node.children)
    return False


def _is_visual(node: DesignNode) -> bool:
    return node.kind in {"image", "icon"} and _has_box(node)


def _is_flow_visual(node: DesignNode) -> bool:
    return _is_visual(node) and node.style.position_mode != "absolute"


def _layout_bounds(node: DesignNode) -> tuple[float, float, float, float]:
    if node.kind == "container" and not node.style.background:
        descendant_boxes = [
            _layout_bounds(child)
            for child in node.children
            if (_participates_in_flow(child) or _is_flow_visual(child)) and _has_box(child)
        ]
        if descendant_boxes:
            return _union_bounds(descendant_boxes)
    return _bounds(node)


def _contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _semantic_anchor_bounds(node: DesignNode) -> tuple[float, float, float, float]:
    semantic_boxes = [
        _layout_bounds(child)
        for child in node.children
        if _has_box(child) and _participates_in_flow(child)
    ]
    if semantic_boxes:
        return _union_bounds(semantic_boxes)
    return _bounds(node)


def _layer_anchor_bounds(node: DesignNode) -> tuple[float, float, float, float]:
    parent_box = _bounds(node)
    if node.kind != "container" or node.style.background:
        return parent_box
    semantic_box = _semantic_anchor_bounds(node)
    parent_area = _area(parent_box)
    if parent_area > 0 and _area(semantic_box) / parent_area < 0.5:
        return semantic_box
    return parent_box


def _is_independent_visual(node: DesignNode, parent: DesignNode, siblings: list[DesignNode]) -> bool:
    if node.kind != "icon" or not _has_box(node) or not _has_box(parent):
        return False
    node_box = _bounds(node)
    parent_box = _bounds(parent)
    parent_area = _area(parent_box)
    if parent_area > 0 and _area(node_box) / parent_area > 0.5:
        return True
    for sibling in siblings:
        if sibling is node or not _is_visual(sibling):
            continue
        if _contains(_bounds(sibling), node_box):
            return True
    return False


def _mark_independent_visual_layers(node: DesignNode) -> None:
    if not _has_box(node):
        for child in node.children:
            _mark_independent_visual_layers(child)
        return
    siblings = list(node.children)
    anchor_x, anchor_y, _, _ = _layer_anchor_bounds(node)
    for child in siblings:
        if _is_independent_visual(child, node, siblings):
            child.style.position_mode = "absolute"
            child.style.offset_x = (child.style.x or 0) - anchor_x
            child.style.offset_y = (child.style.y or 0) - anchor_y
        _mark_independent_visual_layers(child)


def _overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    return width * height


def _is_semantic_collision_node(node: DesignNode) -> bool:
    return node.kind in {"text", "shape"} or (node.kind == "container" and bool(node.style.background))


def _has_real_overlap(children: list[DesignNode], boxes: dict[int, tuple[float, float, float, float]]) -> bool:
    semantic_children = [child for child in children if _is_semantic_collision_node(child)]
    for index, child in enumerate(semantic_children):
        box = boxes[id(child)]
        area = _area(box)
        if area <= 0:
            continue
        for other in semantic_children[index + 1 :]:
            other_box = boxes[id(other)]
            other_area = _area(other_box)
            if other_area <= 0:
                continue
            overlap = _overlap_area(box, other_box)
            if overlap / min(area, other_area) > 0.8:
                return True
    return False


def _vertical_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    _, ay1, _, ay2 = a
    _, by1, _, by2 = b
    return max(0.0, min(ay2, by2) - max(ay1, by1))


def _same_band(a: DesignNode, b: DesignNode, boxes: dict[int, tuple[float, float, float, float]]) -> bool:
    if (a.kind == "image") != (b.kind == "image"):
        return False
    a_box = boxes[id(a)]
    b_box = boxes[id(b)]
    overlap = _vertical_overlap(a_box, b_box)
    shorter = min(a_box[3] - a_box[1], b_box[3] - b_box[1])
    return shorter > 0 and overlap / shorter >= 0.25


def _bands(children: list[DesignNode], boxes: dict[int, tuple[float, float, float, float]]) -> list[list[DesignNode]]:
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


def _horizontal_regions(children: list[DesignNode], boxes: dict[int, tuple[float, float, float, float]], parent_width: float) -> list[list[DesignNode]]:
    if len(children) < 4 or parent_width <= 0:
        return []
    tolerance = max(8.0, parent_width * 0.005)
    ordered = sorted(children, key=lambda child: (boxes[id(child)][0], boxes[id(child)][1]))
    regions: list[list[DesignNode]] = []
    current: list[DesignNode] = []
    current_right: float | None = None
    for child in ordered:
        left = boxes[id(child)][0]
        right = boxes[id(child)][2]
        if current and current_right is not None and left > current_right + tolerance:
            regions.append(current)
            current = []
            current_right = None
        current.append(child)
        current_right = right if current_right is None else max(current_right, right)
    if current:
        regions.append(current)
    if len(regions) != 2 or any(len(region) < 2 for region in regions):
        return []
    first_box = _union_bounds([boxes[id(child)] for child in regions[0]])
    second_box = _union_bounds([boxes[id(child)] for child in regions[1]])
    overlap = _vertical_overlap(first_box, second_box)
    shorter = min(first_box[3] - first_box[1], second_box[3] - second_box[1])
    if shorter <= 0 or overlap / shorter < 0.5:
        return []
    return regions


def _positive_median(values: list[float]) -> float | None:
    positive = [value for value in values if value > 0]
    return float(median(positive)) if positive else None


def _percent(value: float, reference: float) -> float | None:
    if reference <= 0:
        return None
    return value / reference * 100.0


def _flow_style(style: DesignStyle, *, width_percent: float | None = None, margin_top_percent: float | None = None, margin_left_percent: float | None = None) -> DesignStyle:
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


def _make_child_flow(child: DesignNode, *, width_percent: float | None = None, margin_top_percent: float | None = None, margin_left_percent: float | None = None) -> None:
    intrinsic_text = child.kind == "text" and (child.style.text_auto_resize or "").upper() == "WIDTH_AND_HEIGHT"
    if intrinsic_text:
        width_percent = None
    child.style = _flow_style(child.style, width_percent=width_percent, margin_top_percent=margin_top_percent, margin_left_percent=margin_left_percent)
    if intrinsic_text:
        child.style.width_mode = "hug"
    if child.kind == "container" and child.style.layout_direction is None:
        child.style.layout_direction = "vertical"
        child.style.height_mode = "hug"


def _flow_container_style(node: DesignNode, child_bounds: list[tuple[float, float, float, float]]) -> DesignStyle:
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
    style.padding_left = 0
    style.padding_right = 0
    style.padding_top = max(0.0, min_y - py)
    style.padding_bottom = max(0.0, pb - max_y)
    style.gap = None
    return style


def _compile_horizontal_regions(node: DesignNode, regions: list[list[DesignNode]], boxes: dict[int, tuple[float, float, float, float]], original_child_bounds: list[tuple[float, float, float, float]], design_viewport_width: float) -> DesignNode:
    px, _, _, _ = _bounds(node)
    parent_width = _bounds(node)[2] - px
    region_boxes = [_union_bounds([boxes[id(child)] for child in region]) for region in regions]
    row_left = min(box[0] for box in region_boxes)
    row_top = min(box[1] for box in region_boxes)
    row_children: list[DesignNode] = []
    for index, (region, box) in enumerate(zip(regions, region_boxes)):
        x1, y1, x2, y2 = box
        region_node = DesignNode(kind="container", name=f"{node.name or 'section'} region {index + 1}", source_id=f"{node.source_id or 'node'}::region-{index + 1}", style=DesignStyle(x=x1, y=y1, width=x2 - x1, height=y2 - y1, width_percent=_percent(x2 - x1, design_viewport_width), margin_top_percent=_percent(y1 - row_top, parent_width)), children=region)
        row_children.append(region_node)
    gap = region_boxes[1][0] - region_boxes[0][2]
    row = DesignNode(kind="container", name=f"{node.name or 'section'} composition row", source_id=f"{node.source_id or 'node'}::composition-row", style=DesignStyle(layout_direction="horizontal", width_mode="fill", height_mode="hug", gap=max(0.0, gap), counter_axis_align="min", margin_left_percent=_percent(row_left - px, parent_width)), children=row_children)

    flow_ids = {id(child) for region in regions for child in region}
    deferred_children = [child for child in node.children if id(child) not in flow_ids]
    remaining_deferred: list[DesignNode] = []
    for child in deferred_children:
        if child.style.position_mode != "absolute" or not _has_box(child):
            remaining_deferred.append(child)
            continue
        child_box = _bounds(child)
        child_area = _area(child_box)
        center_x = (child_box[0] + child_box[2]) / 2
        center_y = (child_box[1] + child_box[3]) / 2
        anchored = False
        for region_node, region_box in zip(row_children, region_boxes):
            region_area = _area(region_box)
            center_inside = region_box[0] <= center_x <= region_box[2] and region_box[1] <= center_y <= region_box[3]
            if center_inside and region_area > 0 and child_area / region_area <= 0.25:
                child.style.offset_x = child_box[0] - region_box[0]
                child.style.offset_y = child_box[1] - region_box[1]
                region_node.children.append(child)
                anchored = True
                break
        if not anchored:
            remaining_deferred.append(child)

    node.style = _flow_container_style(node, original_child_bounds)
    node.children = [row, *remaining_deferred]
    return node


def _compile_free_layout(node: DesignNode, design_viewport_width: float) -> DesignNode:
    children = node.children
    if not children or not _has_box(node):
        return node
    flow_children = [child for child in children if _has_box(child) and (_participates_in_flow(child) or _is_flow_visual(child))]
    if not flow_children:
        return node
    boxes = {id(child): _layout_bounds(child) for child in flow_children}
    original_child_bounds = list(boxes.values())
    px, _, pr, _ = _bounds(node)
    parent_width = pr - px
    if len(flow_children) == 1:
        child = flow_children[0]
        box = boxes[id(child)]
        if child.kind == "container" and child.style.layout_direction is None:
            child = _compile_node(child, design_viewport_width)
            flow_children[0] = child
        node.style = _flow_container_style(node, original_child_bounds)
        _make_child_flow(child, width_percent=_percent(box[2] - box[0], design_viewport_width), margin_left_percent=_percent(box[0] - px, parent_width))
        node.children = [child, *[item for item in children if item is not flow_children[0] and item is not child]]
        return node
    if _has_real_overlap(flow_children, boxes):
        return node
    regions = _horizontal_regions(flow_children, boxes, parent_width)
    if regions:
        return _compile_horizontal_regions(node, regions, boxes, original_child_bounds, design_viewport_width)
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
        margin_top_percent = _percent(by1 - previous_box[3], parent_width) if previous_box is not None else None
        if len(band) == 1:
            child = band[0]
            child_box = boxes[id(child)]
            _make_child_flow(child, width_percent=_percent(child_box[2] - child_box[0], design_viewport_width), margin_top_percent=margin_top_percent, margin_left_percent=_percent(child_box[0] - px, parent_width))
            compiled_children.append(child)
            continue
        widths = [boxes[id(child)][2] - boxes[id(child)][0] for child in band]
        gaps = [boxes[id(right)][0] - boxes[id(left)][2] for left, right in zip(band, band[1:])]
        row_children: list[DesignNode] = []
        for child, width in zip(band, widths):
            _make_child_flow(child, width_percent=_percent(width, design_viewport_width))
            row_children.append(child)
        row = DesignNode(kind="container", name=f"{node.name or 'section'} row {band_index + 1}", source_id=f"{node.source_id or 'node'}::row-{band_index + 1", style=DesignStyle(layout_direction="horizontal", width_mode="fill", height_mode="hug", gap=_positive_median(gaps), counter_axis_align="min", margin_top_percent=margin_top_percent, margin_left_percent=_percent(bx1 - px, parent_width)), children=row_children)
        compiled_children.append(row)
    compiled_style = _flow_container_style(node, original_child_bounds)
    flow_ids = {id(child) for child in flow_children}
    deferred_children = [child for child in children if id(child) not in flow_ids]
    node.style = compiled_style
    node.children = [*compiled_children, *deferred_children]
    return node


def _compile_node(node: DesignNode, design_viewport_width: float) -> DesignNode:
    if node.kind == "container" and node.style.layout_direction is None:
        node = _compile_free_layout(node, design_viewport_width)
    node.children = [_compile_node(child, design_viewport_width) for child in node.children]
    return node


def compile_responsive_layout(root: DesignNode) -> DesignNode:
    """Compile desktop free-layout content into normal flow plus explicit layers."""
    compiled = deepcopy(root)
    _mark_independent_visual_layers(compiled)
    design_viewport_width = compiled.style.width or 0
    return _compile_node(compiled, design_viewport_width)