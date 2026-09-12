from __future__ import annotations

from copy import deepcopy

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _is_inferred_region(node: DesignNode) -> bool:
    return node.kind == "container" and "::region-" in (node.source_id or "")


def _media_row_height(node: DesignNode) -> float | None:
    if node.kind != "container" or node.style.layout_direction != "horizontal":
        return None
    heights = [
        child.style.height
        for child in node.children
        if child.kind in {"image", "icon"} and child.style.height is not None
    ]
    return max(heights) if heights else None


def _source_map(root: DesignNode) -> dict[str, DesignNode]:
    result: dict[str, DesignNode] = {}

    def visit(node: DesignNode) -> None:
        if node.source_id:
            result[node.source_id] = node
        for child in node.children:
            visit(child)

    visit(root)
    return result


def _percent(value: float, reference: float) -> float:
    return value / reference * 100.0


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _overlap(a1: float, a2: float, b1: float, b2: float) -> float:
    return max(0.0, min(a2, b2) - max(a1, b1))


def _vertical_overlap_ratio(a: DesignNode, b: DesignNode) -> float:
    ab = _box(a)
    bb = _box(b)
    if ab is None or bb is None:
        return 0.0
    overlap = _overlap(ab[1], ab[3], bb[1], bb[3])
    shorter = min(ab[3] - ab[1], bb[3] - bb[1])
    return overlap / shorter if shorter > 0 else 0.0


def _is_pagination_counter_text(node: DesignNode) -> bool:
    if node.kind != "text":
        return False
    if (node.style.text_auto_resize or "").upper() == "WIDTH_AND_HEIGHT":
        return True
    text = (node.text or "").strip()
    parts = [part.strip() for part in text.split("/")]
    return (
        len(text) <= 12
        and len(parts) == 2
        and all(part.isdigit() and 1 <= len(part) <= 3 for part in parts)
    )


def _is_full_bleed_background(source: DesignNode, source_parent: DesignNode) -> bool:
    if source.kind != "image":
        return False
    box = _box(source)
    parent_box = _box(source_parent)
    if box is None or parent_box is None:
        return False
    sw = box[2] - box[0]
    sh = box[3] - box[1]
    pw = parent_box[2] - parent_box[0]
    ph = parent_box[3] - parent_box[1]
    if pw <= 0 or ph <= 0:
        return False
    return sw / pw >= 0.8 and sh / ph >= 0.8


def _remove_source_id(node: DesignNode, source_id: str) -> bool:
    removed = False
    kept: list[DesignNode] = []
    for child in node.children:
        if child.source_id == source_id:
            removed = True
            continue
        if _remove_source_id(child, source_id):
            removed = True
        if child.children or child.kind != "container" or "::" not in (child.source_id or ""):
            kept.append(child)
    node.children = kept
    return removed


def _promote_full_bleed_backgrounds(compiled: DesignNode, source: DesignNode) -> None:
    if compiled.kind != "container" or source.kind != "container":
        return

    backgrounds = [child for child in source.children if _is_full_bleed_background(child, source)]
    for background in backgrounds[:1]:
        if not background.source_id or not background.image_ref:
            continue
        if _remove_source_id(compiled, background.source_id):
            compiled.style.background_image_ref = background.image_ref
            compiled.style.background_image_opacity = background.style.image_opacity

    compiled_by_id = {child.source_id: child for child in compiled.children if child.source_id}
    for source_child in source.children:
        compiled_child = compiled_by_id.get(source_child.source_id)
        if compiled_child is not None and compiled_child.kind == "container":
            _promote_full_bleed_backgrounds(compiled_child, source_child)


def _find_node(node: DesignNode, source_id: str) -> DesignNode | None:
    if node.source_id == source_id:
        return node
    for child in node.children:
        found = _find_node(child, source_id)
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


def _find_parent_node(node: DesignNode, target: DesignNode) -> DesignNode | None:
    if any(child is target for child in node.children):
        return node
    for child in node.children:
        found = _find_parent_node(child, target)
        if found is not None:
            return found
    return None


def _find_inferred_region_owner(
    node: DesignNode,
    source_id: str,
    current_region: DesignNode | None = None,
) -> DesignNode | None:
    if _is_inferred_region(node):
        current_region = node
    if node.source_id == source_id:
        return current_region
    for child in node.children:
        found = _find_inferred_region_owner(child, source_id, current_region)
        if found is not None:
            return found
    return None


def _inferred_region_horizontal_geometry(
    compiled: DesignNode,
    region: DesignNode,
    source_box: tuple[float, float, float, float],
    viewport: float,
) -> tuple[float, float] | None:
    if not region.style.width_percent or viewport <= 0:
        return None
    parent = _find_parent_node(compiled, region)
    if parent is None or parent.style.layout_direction != "horizontal":
        return None

    source_width = source_box[2] - source_box[0]
    if source_width <= 0:
        return None

    left = source_box[0] + source_width * (parent.style.margin_left_percent or 0.0) / 100.0
    gap = parent.style.gap or 0.0
    found_region = False
    for sibling in parent.children:
        if sibling is region:
            found_region = True
            break
        if sibling.style.width_percent is not None:
            left += viewport * sibling.style.width_percent / 100.0
        elif sibling.style.width is not None:
            left += sibling.style.width
        left += gap
    if not found_region:
        return None

    width = viewport * region.style.width_percent / 100.0
    return (left, width) if width > 0 else None


def _detach_ids(node: DesignNode, source_ids: set[str]) -> None:
    kept: list[DesignNode] = []
    for child in node.children:
        if child.source_id in source_ids:
            continue
        _detach_ids(child, source_ids)
        if child.kind == "container" and "::" in (child.source_id or "") and not child.children:
            continue
        kept.append(child)
    node.children = kept


def _leading_space_count(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _split_contact_rows(compiled: DesignNode, source: DesignNode, source_by_id: dict[str, DesignNode], viewport: float) -> None:
    if source.kind != "container":
        return

    for source_text in source.children:
        if source_text.kind != "text" or not source_text.source_id or not source_text.text:
            continue
        lines = [line for line in source_text.text.replace("\r", "").split("\n") if line.strip()]
        if len(lines) < 2 or not all(_leading_space_count(line) > 0 for line in lines):
            continue
        text_box = _box(source_text)
        compiled_text = _find_node(compiled, source_text.source_id)
        if text_box is None or compiled_text is None:
            continue

        icons: list[DesignNode] = []
        for source_icon in source.children:
            if source_icon.kind != "icon" or not source_icon.source_id:
                continue
            icon_box = _box(source_icon)
            if icon_box is None:
                continue
            if _overlap(text_box[0], text_box[2], icon_box[0], icon_box[2]) <= 0:
                continue
            if _overlap(text_box[1], text_box[3], icon_box[1], icon_box[3]) <= 0:
                continue
            if _find_node(compiled, source_icon.source_id) is not None:
                icons.append(source_icon)

        if len(icons) != len(lines):
            continue
        icons.sort(key=lambda item: (_box(item) or (0, 0, 0, 0))[1])

        compiled_parent = _find_parent(compiled, source_text.source_id) or compiled
        inherited_margin_top = compiled_parent.style.margin_top_percent if compiled_parent is not compiled else compiled_text.style.margin_top_percent
        inherited_margin_left = compiled_parent.style.margin_left_percent if compiled_parent is not compiled else compiled_text.style.margin_left_percent

        row_nodes: list[DesignNode] = []
        font_size = source_text.style.font_size or 16.0
        for index, (line, source_icon) in enumerate(zip(lines, icons)):
            compiled_icon = _find_node(compiled, source_icon.source_id)
            icon_box = _box(source_icon)
            if compiled_icon is None or icon_box is None:
                row_nodes = []
                break
            indent_px = _leading_space_count(line) * font_size * 0.36
            icon_width = icon_box[2] - icon_box[0]
            gap = max(0.0, indent_px - icon_width)

            text_style = deepcopy(compiled_text.style)
            text_style.position_mode = None
            text_style.offset_x = None
            text_style.offset_y = None
            text_style.x = None
            text_style.y = None
            text_style.width = None
            text_style.width_percent = None
            text_style.width_mode = "hug"
            text_style.margin_top_percent = None
            text_style.margin_left_percent = None
            text_style.margin_bottom_percent = None

            line_node = DesignNode(
                kind="text",
                name=source_text.name,
                source_id=f"{source_text.source_id}::line-{index + 1}",
                source_type=source_text.source_type,
                text=line.strip(),
                style=text_style,
            )

            compiled_icon.style.position_mode = None
            compiled_icon.style.offset_x = None
            compiled_icon.style.offset_y = None
            compiled_icon.style.x = None
            compiled_icon.style.y = None
            compiled_icon.style.margin_top_percent = None
            compiled_icon.style.margin_left_percent = None
            compiled_icon.style.margin_bottom_percent = None
            compiled_icon.style.width_mode = "hug"

            row_nodes.append(
                DesignNode(
                    kind="container",
                    name=f"{source_text.name or 'contact'} row {index + 1}",
                    source_id=f"{source_text.source_id}::contact-row-{index + 1}",
                    style=DesignStyle(layout_direction="horizontal", width_mode="fill", height_mode="hug", gap=gap, counter_axis_align="center"),
                    children=[compiled_icon, line_node],
                )
            )

        if not row_nodes:
            continue

        source_ids = {source_text.source_id, *(icon.source_id for icon in icons if icon.source_id)}
        _detach_ids(compiled, source_ids)

        group = DesignNode(
            kind="container",
            name=f"{source_text.name or 'contact'} group",
            source_id=f"{source_text.source_id}::contact-group",
            style=DesignStyle(layout_direction="vertical", width_mode="fill", height_mode="hug", margin_top_percent=inherited_margin_top, margin_left_percent=inherited_margin_left),
            children=row_nodes,
        )

        source_index = source.children.index(source_text)
        inserted = False
        for following in source.children[source_index + 1 :]:
            if not following.source_id:
                continue
            target = _find_node(compiled, following.source_id)
            parent = _find_parent(compiled, following.source_id)
            if target is not None and parent is not None:
                position = parent.children.index(target)
                parent.children.insert(position, group)
                inserted = True
                break
        if not inserted:
            compiled.children.append(group)

        last_icon_box = _box(icons[-1])
        if last_icon_box is not None:
            for following in source.children[source_index + 1 :]:
                if following.kind != "text" or not following.source_id:
                    continue
                following_box = _box(following)
                following_node = _find_node(compiled, following.source_id)
                if following_box is None or following_node is None:
                    continue
                following_node.style.margin_top_percent = _percent(max(0.0, following_box[1] - last_icon_box[3]), viewport)
                break


def _stabilize_bottom_control_row(compiled: DesignNode, source: DesignNode, viewport: float) -> None:
    """Keep wide three-item bottom controls together without losing region ownership.

    Pagination-like controls are spatially separate from nearby content even if
    region inference temporarily nests them inside the same content container.
    Detect the relationship from source geometry: two visual controls plus a
    compact counter in one bottom band spanning a meaningful width. Metadata is
    accepted when present, but counter-like text can recover missing Figma
    auto-resize metadata. When all three controls already belong to one inferred
    region, stabilize them inside that region; otherwise preserve the existing
    section-level row.
    """
    source_box = _box(source)
    if source.kind != "container" or source_box is None:
        return
    parent_width = source_box[2] - source_box[0]
    parent_height = source_box[3] - source_box[1]
    if parent_width <= 0 or parent_height <= 0:
        return

    direct = [child for child in source.children if child.source_id and _box(child) is not None]
    texts = [child for child in direct if _is_pagination_counter_text(child)]
    visuals = [child for child in direct if child.kind == "icon"]

    for text in texts:
        text_box = _box(text)
        if text_box is None or text_box[1] < source_box[1] + parent_height * 0.65:
            continue
        aligned = [icon for icon in visuals if _vertical_overlap_ratio(text, icon) >= 0.25]
        if len(aligned) < 2:
            continue
        aligned.sort(key=lambda node: (_box(node) or (0, 0, 0, 0))[0])
        left = next((node for node in reversed(aligned) if (_box(node) or (0, 0, 0, 0))[2] <= text_box[0]), None)
        right = next((node for node in aligned if (_box(node) or (0, 0, 0, 0))[0] >= text_box[2]), None)
        if left is None or right is None:
            continue
        trio = [left, text, right]
        trio_boxes = [_box(node) for node in trio]
        if any(box is None for box in trio_boxes):
            continue
        boxes = [box for box in trio_boxes if box is not None]
        span_left = min(box[0] for box in boxes)
        span_right = max(box[2] for box in boxes)
        if (span_right - span_left) / parent_width < 0.25:
            continue

        compiled_nodes = [_find_node(compiled, node.source_id) for node in trio]
        if any(node is None for node in compiled_nodes):
            continue
        nodes = [node for node in compiled_nodes if node is not None]

        owners = [
            _find_inferred_region_owner(compiled, node.source_id)
            for node in trio
            if node.source_id
        ]
        region_owner = None
        if owners and owners[0] is not None and all(owner is owners[0] for owner in owners):
            region_owner = owners[0]

        placement_parent = compiled
        width_reference = parent_width
        left_origin = source_box[0]
        if region_owner is not None:
            geometry = _inferred_region_horizontal_geometry(compiled, region_owner, source_box, viewport)
            if geometry is not None:
                left_origin, width_reference = geometry
                placement_parent = region_owner

        _detach_ids(compiled, {node.source_id for node in trio if node.source_id})
        for node in nodes:
            node.style.position_mode = None
            node.style.offset_x = None
            node.style.offset_y = None
            node.style.x = None
            node.style.y = None
            node.style.margin_top_percent = None
            node.style.margin_left_percent = None
            node.style.margin_bottom_percent = None
            if node.kind in {"text", "icon"}:
                node.style.width_mode = "hug"
                node.style.width_percent = None

        preceding_bottom = source_box[1]
        for candidate in direct:
            if candidate in trio or _is_full_bleed_background(candidate, source):
                continue
            box = _box(candidate)
            if box is not None and box[3] <= text_box[1]:
                preceding_bottom = max(preceding_bottom, box[3])

        row = DesignNode(
            kind="container",
            name="Bottom control row",
            source_id=f"{source.source_id or 'section'}::bottom-controls",
            style=DesignStyle(
                layout_direction="horizontal",
                width_percent=_percent(span_right - span_left, width_reference),
                height_mode="hug",
                margin_left_percent=_percent(span_left - left_origin, width_reference),
                margin_top_percent=_percent(max(0.0, text_box[1] - preceding_bottom), viewport),
                primary_axis_align="space_between",
                counter_axis_align="center",
            ),
            children=nodes,
        )
        placement_parent.children.append(row)
        return


def resolve_compiled_spatial_relationships(compiled_root: DesignNode, source_root: DesignNode, design_viewport_width: float | None) -> DesignNode:
    viewport = design_viewport_width or 0
    if viewport <= 0:
        return compiled_root

    source_by_id = _source_map(source_root)
    _promote_full_bleed_backgrounds(compiled_root, source_root)
    _split_contact_rows(compiled_root, source_root, source_by_id, viewport)
    _stabilize_bottom_control_row(compiled_root, source_root, viewport)
    return compiled_root


def resolve_inferred_region_overlays(root: DesignNode, design_viewport_width: float | None) -> DesignNode:
    viewport = design_viewport_width or 0
    if viewport <= 0:
        return root

    def visit(node: DesignNode) -> None:
        if _is_inferred_region(node) and node.style.width_percent:
            region_width = viewport * node.style.width_percent / 100.0
            previous_media_height: float | None = None

            for child in node.children:
                media_height = _media_row_height(child)
                if media_height is not None:
                    previous_media_height = media_height
                    continue

                style = child.style
                if (
                    previous_media_height is None
                    or style.position_mode != "absolute"
                    or style.offset_x is None
                    or style.offset_y is None
                    or style.width is None
                    or style.height is None
                    or region_width <= 0
                ):
                    continue

                offset_x = style.offset_x
                offset_y = style.offset_y
                top_px = offset_y - previous_media_height
                bottom_px = previous_media_height - offset_y - style.height

                style.position_mode = None
                style.offset_x = None
                style.offset_y = None
                style.x = None
                style.y = None
                style.width_percent = style.width / viewport * 100.0
                style.width_mode = None
                style.margin_left_percent = offset_x / region_width * 100.0
                style.margin_top_percent = top_px / region_width * 100.0
                style.margin_bottom_percent = bottom_px / region_width * 100.0

        for child in node.children:
            visit(child)

    visit(root)
    return root
