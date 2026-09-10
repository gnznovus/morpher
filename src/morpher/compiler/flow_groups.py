from __future__ import annotations

from morpher.ir.nodes import DesignNode


def _find_parent(node: DesignNode, target: DesignNode) -> DesignNode | None:
    if target in node.children:
        return node
    for child in node.children:
        found = _find_parent(child, target)
        if found is not None:
            return found
    return None


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    s = node.style
    if any(value is None for value in (s.x, s.y, s.width, s.height)):
        return None
    return s.x, s.y, s.x + s.width, s.y + s.height


def _find(node: DesignNode, source_id: str) -> DesignNode | None:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def _source_map(root: DesignNode) -> dict[str, DesignNode]:
    result: dict[str, DesignNode] = {}

    def visit(node: DesignNode) -> None:
        if node.source_id:
            result[node.source_id] = node
        for child in node.children:
            visit(child)

    visit(root)
    return result


def _is_inferred_region(node: DesignNode) -> bool:
    source_id = node.source_id or ""
    final_segment = source_id.rsplit("::", 1)[-1]
    return node.kind == "container" and final_segment.startswith("region-")


def _find_region_owner(
    node: DesignNode,
    target: DesignNode,
    current_region: DesignNode | None = None,
) -> DesignNode | None:
    if _is_inferred_region(node):
        current_region = node
    if node is target:
        return current_region
    for child in node.children:
        found = _find_region_owner(child, target, current_region)
        if found is not None:
            return found
    return None


def _inferred_regions(root: DesignNode) -> list[DesignNode]:
    regions: list[DesignNode] = []

    def visit(node: DesignNode) -> None:
        if _is_inferred_region(node):
            regions.append(node)
        for child in node.children:
            visit(child)

    visit(root)
    return regions


def _region_horizontal_geometry(
    compiled_root: DesignNode,
    region: DesignNode,
    source_root: DesignNode,
    viewport: float,
) -> tuple[float, float] | None:
    if viewport <= 0 or region.style.width_percent is None:
        return None
    source_box = _box(source_root)
    parent = _find_parent(compiled_root, region)
    if source_box is None or parent is None or parent.style.layout_direction != "horizontal":
        return None

    source_left = source_box[0]
    source_width = source_box[2] - source_box[0]
    if source_width <= 0:
        return None

    left = source_left + source_width * (parent.style.margin_left_percent or 0.0) / 100.0
    gap = parent.style.gap or 0.0
    for sibling in parent.children:
        if sibling is region:
            width = viewport * region.style.width_percent / 100.0
            return (left, width) if width > 0 else None
        if sibling.style.width_percent is not None:
            left += viewport * sibling.style.width_percent / 100.0
        elif sibling.style.width is not None:
            left += sibling.style.width
        left += gap
    return None


def _owns_source_members(
    compiled_root: DesignNode,
    region: DesignNode,
    source_root: DesignNode,
    members: list[DesignNode],
    viewport: float,
) -> bool:
    geometry = _region_horizontal_geometry(compiled_root, region, source_root, viewport)
    if geometry is None:
        return False
    left, width = geometry
    right = left + width
    for member in members:
        member_box = _box(member)
        if member_box is None:
            return False
        center_x = (member_box[0] + member_box[2]) / 2.0
        if not (left <= center_x <= right):
            return False
    return True


def _normalize_row_to_region(
    compiled_root: DesignNode,
    row: DesignNode,
    region: DesignNode,
    source_root: DesignNode,
    members: list[DesignNode],
    viewport: float,
) -> None:
    geometry = _region_horizontal_geometry(compiled_root, region, source_root, viewport)
    member_boxes = [_box(member) for member in members]
    if geometry is None or any(box is None for box in member_boxes):
        return
    region_left, region_width = geometry
    boxes = [box for box in member_boxes if box is not None]
    left = min(box[0] for box in boxes)
    right = max(box[2] for box in boxes)
    row.style.width_percent = (right - left) / region_width * 100.0
    row.style.width_mode = None
    row.style.margin_left_percent = (left - region_left) / region_width * 100.0


def _normalize_contact_groups(root: DesignNode) -> None:
    def visit(node: DesignNode) -> None:
        for child in node.children:
            visit(child)

        for child in node.children:
            if child.kind != "container" or "::contact-group" not in (child.source_id or ""):
                continue
            child.style.margin_left_percent = None
            child.style.margin_top_percent = None
            child.style.margin_bottom_percent = None
            child.style.width_mode = "fill"
            child.style.width_percent = None

            if node.kind == "container" and "::row-" in (node.source_id or ""):
                node.style.layout_direction = "vertical"
                node.style.gap = None

    visit(root)


def _stabilize_bottom_control_row(
    compiled_root: DesignNode,
    source_root: DesignNode,
    source_by_id: dict[str, DesignNode],
    viewport: float,
) -> None:
    if viewport <= 0 or source_root.kind != "container":
        return
    parent_box = _box(source_root)
    if parent_box is None:
        return
    px, py, pr, pb = parent_box
    ph = pb - py
    if ph <= 0:
        return

    source_children = [child for child in source_root.children if child.source_id and _box(child) is not None]
    bottom_candidates = [
        child for child in source_children
        if (_box(child)[1] - py) / ph >= 0.75
    ]

    for text in bottom_candidates:
        if text.kind != "text" or not text.source_id:
            continue
        tb = _box(text)
        if tb is None:
            continue
        visuals = []
        for child in bottom_candidates:
            if child.kind != "icon" or not child.source_id:
                continue
            cb = _box(child)
            if cb is None:
                continue
            overlap = max(0.0, min(tb[3], cb[3]) - max(tb[1], cb[1]))
            if overlap > 0:
                visuals.append(child)
        if len(visuals) != 2:
            continue

        members = sorted([visuals[0], text, visuals[1]], key=lambda child: _box(child)[0])
        compiled_members = [_find(compiled_root, member.source_id) for member in members]
        if any(member is None for member in compiled_members):
            continue

        row = None
        first = compiled_members[0]
        parent = _find_parent(compiled_root, first)
        if parent is not None and all(member in parent.children for member in compiled_members):
            row = parent
        if row is None or row.kind != "container" or row.style.layout_direction != "horizontal":
            continue

        row.style.primary_axis_align = "space_between"
        row.style.gap = None

        region_owner = _find_region_owner(compiled_root, row)
        if region_owner is not None and _owns_source_members(
            compiled_root, region_owner, source_root, members, viewport
        ):
            _normalize_row_to_region(
                compiled_root, row, region_owner, source_root, members, viewport
            )
            break

        geometric_owner = next(
            (
                region
                for region in _inferred_regions(compiled_root)
                if _owns_source_members(compiled_root, region, source_root, members, viewport)
            ),
            None,
        )
        if geometric_owner is not None:
            current_parent = _find_parent(compiled_root, row)
            if current_parent is not None and current_parent is not geometric_owner:
                current_parent.children = [child for child in current_parent.children if child is not row]
                geometric_owner.children.append(row)
            _normalize_row_to_region(
                compiled_root, row, geometric_owner, source_root, members, viewport
            )
            break

        if parent is not compiled_root:
            owner = _find_parent(compiled_root, row)
            if owner is not None:
                owner.children = [child for child in owner.children if child is not row]
                compiled_root.children.append(row)

        boxes = [_box(member) for member in members]
        left = min(box[0] for box in boxes)
        right = max(box[2] for box in boxes)
        row.style.width_percent = (right - left) / viewport * 100.0
        row.style.width_mode = None
        row.style.margin_left_percent = (left - px) / (pr - px) * 100.0
        break


def stabilize_compiled_flow_groups(
    compiled_root: DesignNode,
    source_root: DesignNode,
    design_viewport_width: float | None,
) -> DesignNode:
    viewport = design_viewport_width or 0
    _normalize_contact_groups(compiled_root)
    _stabilize_bottom_control_row(compiled_root, source_root, _source_map(source_root), viewport)
    return compiled_root
