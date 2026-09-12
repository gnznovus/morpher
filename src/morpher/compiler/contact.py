from __future__ import annotations

from copy import deepcopy

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


def _leading_space_count(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_contact_visual_anchor(node: DesignNode) -> bool:
    """Return true for an icon or a wrapper whose descendants are only icon visuals.

    Some Figma exports keep a simple glyph as a direct icon while others wrap the
    same kind of glyph in a small Frame/Group. The wrapper geometry is the authored
    row anchor, so contact inference must treat both shapes equivalently without
    flattening or moving the visual itself.
    """
    if node.kind == "icon":
        return True
    if node.kind != "container" or not node.children:
        return False

    found_icon = False

    def visual_only(current: DesignNode) -> bool:
        nonlocal found_icon
        if current.kind == "icon":
            found_icon = True
            return True
        if current.kind != "container" or not current.children:
            return False
        return all(visual_only(child) for child in current.children)

    return visual_only(node) and found_icon


def _contact_icons(parent: DesignNode, text: DesignNode) -> list[DesignNode]:
    text_box = _box(text)
    if text_box is None:
        return []

    font_size = text.style.font_size or 16.0
    max_gap = max(font_size * 3.0, (text_box[2] - text_box[0]) * 0.15)
    icons: list[DesignNode] = []
    for child in parent.children:
        if child is text or not _is_contact_visual_anchor(child):
            continue
        icon_box = _box(child)
        if icon_box is None:
            continue
        vertical_overlap = max(0.0, min(text_box[3], icon_box[3]) - max(text_box[1], icon_box[1]))
        if vertical_overlap <= 0:
            continue
        horizontal_overlap = max(0.0, min(text_box[2], icon_box[2]) - max(text_box[0], icon_box[0]))
        horizontal_gap = max(0.0, text_box[0] - icon_box[2])
        if horizontal_overlap <= 0 and horizontal_gap > max_gap:
            continue
        icons.append(child)

    icons.sort(key=lambda node: (_box(node) or (0.0, 0.0, 0.0, 0.0))[1])
    return icons


def _split_spatial_contact_text(parent: DesignNode, text: DesignNode) -> list[DesignNode] | None:
    if text.kind != "text" or not text.text or not text.source_id:
        return None
    lines = [line for line in text.text.replace("\r", "").split("\n") if line.strip()]
    if len(lines) < 2:
        return None

    icons = _contact_icons(parent, text)
    if len(icons) < 2 or len(icons) > len(lines):
        return None

    text_box = _box(text)
    if text_box is None:
        return None

    base_y = text.style.y
    if base_y is None:
        return None
    line_height = text.style.line_height or text.style.font_size or 16.0
    font_size = text.style.font_size or 16.0

    rows: list[DesignNode] = []
    last_y = base_y
    for index, line in enumerate(lines):
        row = deepcopy(text)
        row.children = []
        row.source_id = f"{text.source_id}::contact-line-{index + 1}"
        row.text = line.strip()
        row.style.height = line_height
        row.style.width = None
        row.style.width_percent = None
        row.style.width_mode = "hug"
        row.style.text_auto_resize = "WIDTH_AND_HEIGHT"
        row.style.x = (text.style.x or 0.0) + _leading_space_count(line) * font_size * 0.36

        if index < len(icons):
            icon_box = _box(icons[index])
            if icon_box is None:
                return None
            # Treat the authored visual as the row's vertical anchor. Elementor's
            # spatial equivalent of align-self:center is to center the text line box
            # on the icon/wrapper box rather than aligning their top edges.
            icon_center_y = (icon_box[1] + icon_box[3]) / 2.0
            row.style.y = icon_center_y - line_height / 2.0
            last_y = row.style.y
        else:
            row.style.y = last_y + line_height
            last_y = row.style.y
        rows.append(row)

    return rows


def compile_contact_spatial_layout(root: DesignNode) -> DesignNode:
    """Preserve contact relationships for Elementor without converting them to flow.

    Figma contact blocks are often authored as a vertical icon rail beside one
    multiline text node. Elementor cannot reproduce Figma paragraph spacing from
    that single widget, so the text lines drift away from independently positioned
    icons. Detect that relationship, split only the multiline text into individual
    spatial text nodes, and keep every authored icon and coordinate in the same
    free-layout composition. Native keeps the existing flow-oriented contact pass.
    """
    compiled = deepcopy(root)

    def visit(parent: DesignNode) -> None:
        replacements: dict[int, list[DesignNode]] = {}
        for index, child in enumerate(parent.children):
            rows = _split_spatial_contact_text(parent, child)
            if rows is not None:
                replacements[index] = rows

        if replacements:
            rebuilt: list[DesignNode] = []
            for index, child in enumerate(parent.children):
                rebuilt.extend(replacements.get(index, [child]))
            parent.children = rebuilt

        for child in parent.children:
            if child.kind == "container":
                visit(child)

    visit(compiled)
    return compiled


def _normalize_contact_icon_widths(
    group: DesignNode,
    source_by_id: dict[str, DesignNode],
    viewport: float,
) -> None:
    """Give peer contact icons one shared widget width.

    The contact compiler already knows these icons are siblings because it
    rebuilt them as rows inside one generated contact group. Normalizing only
    this peer set keeps narrow glyphs (for example a phone icon) centered on
    the same visual column without introducing global icon rules or wrappers.
    """
    icons: list[tuple[DesignNode, float]] = []
    for row in group.children:
        for child in row.children:
            if child.kind != "icon" or not child.source_id:
                continue
            source = source_by_id.get(child.source_id)
            source_box = _box(source) if source is not None else None
            if source_box is None:
                continue
            width = source_box[2] - source_box[0]
            if width > 0:
                icons.append((child, width))

    if len(icons) < 2:
        return

    peer_width = max(width for _, width in icons)
    peer_width_percent = peer_width / viewport * 100.0
    for icon, _ in icons:
        icon.style.width = peer_width
        icon.style.width_percent = peer_width_percent
        icon.style.width_mode = None


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
        _normalize_contact_icon_widths(group, source_by_id, viewport)

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
        detached_group.style.margin_left_percent = owner.style.margin_left_percent
        detached_group.style.margin_right_percent = owner.style.margin_right_percent
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
            following_node.style.margin_left_percent = owner.style.margin_left_percent
            following_node.style.margin_right_percent = owner.style.margin_right_percent
            owner_parent.children.insert(owner_index + 2, following_node)

    return compiled_root
