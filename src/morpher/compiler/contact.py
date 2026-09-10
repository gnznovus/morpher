from __future__ import annotations

from morpher.ir.nodes import DesignNode


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _horizontal_overlap_ratio(a: DesignNode, b: DesignNode) -> float:
    ab = _box(a)
    bb = _box(b)
    if ab is None or bb is None:
        return 0.0
    overlap = max(0.0, min(ab[2], bb[2]) - max(ab[0], bb[0]))
    shorter = min(ab[2] - ab[0], bb[2] - bb[0])
    return overlap / shorter if shorter > 0 else 0.0


def _source_map(root: DesignNode) -> dict[str, DesignNode]:
    result: dict[str, DesignNode] = {}

    def visit(node: DesignNode) -> None:
        if node.source_id:
            result[node.source_id] = node
        for child in node.children:
            visit(child)

    visit(root)
    return result


def _find(node: DesignNode, source_id: str) -> DesignNode | None:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find(child, source_id)
        if found is not None:
            return found
    return None


def _find_parent(node: DesignNode, source_id: str) -> DesignNode | None:
    if any(child.source_id == source_id for child in node.children):
        return node
    for child in node.children:
        found = _find_parent(child, source_id)
        if found is not None:
            return found
    return None


def _detach(node: DesignNode, source_id: str) -> DesignNode | None:
    for index, child in enumerate(node.children):
        if child.source_id == source_id:
            return node.children.pop(index)
    for child in node.children:
        detached = _detach(child, source_id)
        if detached is not None:
            return detached
    return None


def _generated_contact_groups(root: DesignNode) -> list[DesignNode]:
    groups: list[DesignNode] = []

    def visit(node: DesignNode) -> None:
        if node.kind == "container" and (node.source_id or "").endswith("::contact-group"):
            groups.append(node)
        for child in node.children:
            visit(child)

    visit(root)
    return groups


def resolve_contact_group_ownership(
    compiled_root: DesignNode,
    source_root: DesignNode,
    design_viewport_width: float | None,
) -> DesignNode:
    """Attach generated contact rows to the nearby semantic content region.

    Contact lists reconstructed from one multiline Figma text node can be
    detached from the content region that owns their heading/body. Source
    geometry is a better ownership signal than source-array order: the nearest
    horizontally aligned text above owns the list, while the nearest aligned
    text starting below the list becomes the following sibling. This keeps the
    relationship in normal flow without absolute positioning or overlap hacks.
    """
    viewport = design_viewport_width or 0.0
    if viewport <= 0:
        return compiled_root

    source_by_id = _source_map(source_root)

    for group in list(_generated_contact_groups(compiled_root)):
        group_id = group.source_id or ""
        contact_id = group_id.removesuffix("::contact-group")
        source_contact = source_by_id.get(contact_id)
        contact_box = _box(source_contact) if source_contact is not None else None
        if source_contact is None or contact_box is None:
            continue

        text_candidates = [
            node
            for node in source_by_id.values()
            if node.kind == "text"
            and node.source_id != contact_id
            and _box(node) is not None
            and _horizontal_overlap_ratio(source_contact, node) >= 0.25
        ]

        preceding = [node for node in text_candidates if (_box(node) or (0, 0, 0, 0))[3] <= contact_box[1]]
        if not preceding:
            continue
        owner_source = max(preceding, key=lambda node: (_box(node) or (0, 0, 0, 0))[3])
        owner = _find(compiled_root, owner_source.source_id or "")
        owner_parent = _find_parent(compiled_root, owner_source.source_id or "")
        if owner is None or owner_parent is None:
            continue

        detached_group = _detach(compiled_root, group_id)
        if detached_group is None:
            continue
        owner_box = _box(owner_source)
        if owner_box is not None:
            detached_group.style.margin_top_percent = max(0.0, contact_box[1] - owner_box[3]) / viewport * 100.0
        detached_group.style.margin_left_percent = None
        detached_group.style.margin_right_percent = None
        detached_group.style.position_mode = None
        detached_group.style.offset_x = None
        detached_group.style.offset_y = None

        following = [node for node in text_candidates if (_box(node) or (0, 0, 0, 0))[1] > contact_box[1]]
        following_source = min(following, key=lambda node: (_box(node) or (0, 0, 0, 0))[1]) if following else None
        following_node = None
        if following_source is not None and following_source.source_id:
            following_node = _detach(compiled_root, following_source.source_id)

        owner_index = owner_parent.children.index(owner)
        owner_parent.children.insert(owner_index + 1, detached_group)

        if following_node is not None and following_source is not None:
            contact_visual_bottom = contact_box[3]
            icon_bottoms = []
            for row in detached_group.children:
                for child in row.children:
                    source_child = source_by_id.get(child.source_id or "")
                    box = _box(source_child) if source_child is not None else None
                    if child.kind == "icon" and box is not None:
                        icon_bottoms.append(box[3])
            if icon_bottoms:
                contact_visual_bottom = max(icon_bottoms)
            following_box = _box(following_source)
            if following_box is not None:
                following_node.style.margin_top_percent = max(0.0, following_box[1] - contact_visual_bottom) / viewport * 100.0
            following_node.style.margin_left_percent = None
            owner_parent.children.insert(owner_index + 2, following_node)

    return compiled_root
