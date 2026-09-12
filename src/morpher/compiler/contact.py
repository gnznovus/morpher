from __future__ import annotations

from copy import deepcopy

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


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
    if node.kind == "icon":
        return True
    if node.kind == "shape" and node.source_type == "ELLIPSE":
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


def _contact_visual_leaf(anchor: DesignNode) -> DesignNode:
    """Strip a redundant visual-only wrapper when it contains one icon leaf."""
    leaves: list[DesignNode] = []

    def collect(node: DesignNode) -> None:
        if node.kind == "icon":
            leaves.append(node)
            return
        for child in node.children:
            collect(child)

    collect(anchor)
    if len(leaves) == 1:
        return deepcopy(leaves[0])
    return deepcopy(anchor)


def _contact_icons(parent: DesignNode, text: DesignNode) -> list[DesignNode]:
    text_box = _box(text)
    if text_box is None:
        return []

    font_size = text.style.font_size or 16.0
    max_gap = max(font_size * 3.0, (text_box[2] - text_box[0]) * 0.15)
    max_anchor_size = font_size * 4.0
    edge_tolerance = max(4.0, font_size * 0.5)
    icons: list[DesignNode] = []
    for child in parent.children:
        if child is text or not _is_contact_visual_anchor(child):
            continue
        icon_box = _box(child)
        if icon_box is None:
            continue
        icon_width = icon_box[2] - icon_box[0]
        icon_height = icon_box[3] - icon_box[1]
        if icon_width > max_anchor_size or icon_height > max_anchor_size:
            continue
        vertical_overlap = max(0.0, min(text_box[3], icon_box[3]) - max(text_box[1], icon_box[1]))
        if vertical_overlap <= 0:
            continue

        # Marker rails are leading visuals, but small glyphs can overlap the
        # text box edge by a few authored pixels. Reject only anchors clearly
        # inside/to the right of the text rail so near-edge contact icons survive.
        if icon_box[0] > text_box[0] + edge_tolerance:
            continue

        horizontal_overlap = max(0.0, min(text_box[2], icon_box[2]) - max(text_box[0], icon_box[0]))
        horizontal_gap = max(0.0, text_box[0] - icon_box[2])
        if horizontal_overlap <= 0 and horizontal_gap > max_gap:
            continue
        icons.append(child)

    icons.sort(key=lambda node: (_box(node) or (0.0, 0.0, 0.0, 0.0))[1])
    return icons


def _clear_local_geometry(node: DesignNode) -> None:
    node.style.x = None
    node.style.y = None
    node.style.position_mode = None
    node.style.offset_x = None
    node.style.offset_y = None
    node.style.margin_top_percent = None
    node.style.margin_right_percent = None
    node.style.margin_bottom_percent = None
    node.style.margin_left_percent = None


def _line_start_indices(
    anchors: list[DesignNode],
    raw_lines: list[str],
    line_height: float,
) -> list[int] | None:
    """Map visual-anchor rhythm to logical text-line starts.

    A normal marker-to-marker gap represents one logical row. A gap near twice that
    rhythm means the preceding wording wrapped to a continuation line. This uses the
    authored marker rail rather than assuming every newline starts a new item.
    """
    if not anchors or not raw_lines or line_height <= 0:
        return None

    tops: list[float] = []
    for anchor in anchors:
        box = _box(anchor)
        if box is None:
            return None
        tops.append(box[1])

    if len(tops) == 1:
        return [0]
    gaps = [later - earlier for earlier, later in zip(tops, tops[1:]) if later > earlier]
    if not gaps:
        return None
    base_gap = min(gaps)
    if base_gap <= 0:
        return None

    starts = [0]
    for gap in (later - earlier for earlier, later in zip(tops, tops[1:])):
        line_count = max(1, int(round(gap / base_gap)))
        start = starts[-1] + line_count
        if start >= len(raw_lines):
            return None
        starts.append(start)
    return starts


def _build_contact_items(
    text: DesignNode,
    anchors: list[DesignNode],
    parent_style: DesignStyle,
) -> list[DesignNode] | None:
    """Turn one multiline text wall plus a visual rail into authored item pairs.

    The visual rail defines logical item starts. Text between two neighboring anchor
    starts stays inside the earlier item, which preserves wrapped continuation lines
    such as a two-line amenity beside one bullet marker.
    """
    if not text.text or not text.source_id:
        return None

    raw_lines = [line for line in text.text.replace("\r", "").split("\n") if line.strip()]
    if len(raw_lines) < 2 or len(anchors) < 2 or len(anchors) > len(raw_lines):
        return None

    first_anchor_box = _box(anchors[0])
    if first_anchor_box is None or text.style.y is None:
        return None

    font_size = text.style.font_size or 16.0
    line_height = text.style.line_height or font_size
    starts = _line_start_indices(anchors, raw_lines, line_height)
    if starts is None:
        return None

    shared_leading = _leading_space_count(raw_lines[0])
    shared_text_x = (text.style.x or 0.0) + shared_leading * font_size * 0.36
    parent_x = parent_style.x or 0.0
    parent_y = parent_style.y or 0.0
    items: list[DesignNode] = []

    for index, anchor in enumerate(anchors):
        anchor_box = _box(anchor)
        if anchor_box is None:
            return None

        start = starts[index]
        end = starts[index + 1] if index + 1 < len(starts) else len(raw_lines)
        item_lines = raw_lines[start:end]
        if not item_lines:
            return None

        visual = _contact_visual_leaf(anchor)
        visual_box = _box(visual) or anchor_box
        item_x = visual_box[0]
        item_y = text.style.y + (anchor_box[1] - first_anchor_box[1])
        gap = max(0.0, shared_text_x - visual_box[2])

        _clear_local_geometry(visual)
        visual.style.width_mode = "fixed"
        visual.style.height_mode = "fixed"

        wording = deepcopy(text)
        wording.children = []
        wording.source_id = f"{text.source_id}::contact-wording-{index + 1}"
        wording.text = "\n".join(line.strip() for line in item_lines)
        _clear_local_geometry(wording)
        wording.style.width = None
        wording.style.width_percent = None
        wording.style.height = None
        wording.style.width_mode = "hug"
        wording.style.height_mode = "hug"
        wording.style.text_auto_resize = "WIDTH_AND_HEIGHT"

        text_height = line_height * len(item_lines)
        visual_height = visual_box[3] - visual_box[1]
        item = DesignNode(
            kind="container",
            name=f"{text.name or 'contact'} item {index + 1}",
            source_id=f"{text.source_id}::contact-item-{index + 1}",
            style=DesignStyle(
                x=item_x,
                y=item_y,
                position_mode="absolute",
                offset_x=item_x - parent_x,
                offset_y=item_y - parent_y,
                width=None,
                height=max(text_height, visual_height),
                layout_direction="horizontal",
                width_mode="hug",
                height_mode="fixed",
                gap=gap,
                # Elementor's row "Alignment" must stay at Start. Center causes
                # icons/bullets and wrapped wording to drift vertically.
                counter_axis_align="min",
            ),
            children=[visual, wording],
        )
        items.append(item)

    return items


def compile_contact_spatial_layout(root: DesignNode) -> DesignNode:
    """Normalize visual-marker text walls into explicit absolute row items.

    Figma often exports logical rows as one multiline text node beside a separate
    visual rail. Contacts use icons; amenity lists may use small ellipse markers.
    Recover those item boundaries before Elementor sees them while preserving the
    existing size guard so large decorative graphics cannot become row anchors.
    """
    compiled = deepcopy(root)

    def visit(parent: DesignNode) -> None:
        replacements: dict[int, list[DesignNode]] = {}
        consumed_anchor_ids: set[str] = set()

        for index, child in enumerate(parent.children):
            if child.kind != "text":
                continue
            anchors = _contact_icons(parent, child)
            items = _build_contact_items(child, anchors, parent.style)
            if items is None:
                continue
            replacements[index] = items
            consumed_anchor_ids.update(anchor.source_id for anchor in anchors if anchor.source_id)

        if replacements:
            rebuilt: list[DesignNode] = []
            for index, child in enumerate(parent.children):
                if child.source_id in consumed_anchor_ids:
                    continue
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
