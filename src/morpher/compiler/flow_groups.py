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

            # Contact-group placement belongs to its inferred wrapper. If the
            # wrapper was created as a horizontal row from overlapping Figma
            # text bounds, restore the semantic vertical relationship instead
            # of applying the same spatial offset twice.
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

        # Find the compiler-generated row already owning the trio.
        row = None
        first = compiled_members[0]
        parent = _find_parent(compiled_root, first)
        if parent is not None and all(member in parent.children for member in compiled_members):
            row = parent
        if row is None or row.kind != "container" or row.style.layout_direction != "horizontal":
            continue

        boxes = [_box(member) for member in members]
        left = min(box[0] for box in boxes)
        right = max(box[2] for box in boxes)
        row.style.width_percent = (right - left) / viewport * 100.0
        row.style.width_mode = None
        row.style.margin_left_percent = (left - px) / (pr - px) * 100.0
        row.style.primary_axis_align = "space_between"
        row.style.gap = None

        # These controls are direct children of the source section, so keep
        # their inferred row at section level too. This avoids a nested region
        # adding another horizontal offset and sending pagination off-canvas.
        if parent is not compiled_root:
            owner = _find_parent(compiled_root, row)
            if owner is not None:
                owner.children = [child for child in owner.children if child is not row]
                compiled_root.children.append(row)
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
