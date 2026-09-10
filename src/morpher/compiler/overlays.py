from __future__ import annotations

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
    s = node.style
    if any(value is None for value in (s.x, s.y, s.width, s.height)):
        return None
    return s.x, s.y, s.x + s.width, s.y + s.height


def _overlap(a1: float, a2: float, b1: float, b2: float) -> float:
    return max(0.0, min(a2, b2) - max(a1, b1))


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


def _restore_relative_background(
    compiled: DesignNode,
    source: DesignNode,
    viewport: float,
) -> None:
    if compiled.kind != "container" or source.kind != "container":
        return

    source_by_id = {child.source_id: child for child in source.children if child.source_id}
    backgrounds = [
        child
        for child in compiled.children
        if child.source_id in source_by_id
        and _is_full_bleed_background(source_by_id[child.source_id], source)
    ]
    if not backgrounds:
        return

    background = backgrounds[0]
    source_background = source_by_id[background.source_id]
    background.style.position_mode = None
    background.style.offset_x = None
    background.style.offset_y = None
    background.style.x = None
    background.style.y = None
    background.style.width_percent = None
    background.style.width_mode = "fill"
    background.style.margin_top_percent = None
    background.style.margin_left_percent = None
    background.style.margin_bottom_percent = None

    others = [child for child in compiled.children if child is not background]
    if others and source_background.style.height is not None:
        first = others[0]
        first.style.margin_top_percent = (first.style.margin_top_percent or 0.0) - _percent(
            source_background.style.height,
            viewport,
        )
    compiled.children = [background, *others]


def _raw_text_overlap(a: DesignNode, b: DesignNode) -> bool:
    if a.kind != "text" or b.kind != "text":
        return False
    ab = _box(a)
    bb = _box(b)
    if ab is None or bb is None:
        return False
    horizontal = _overlap(ab[0], ab[2], bb[0], bb[2])
    shorter_width = min(ab[2] - ab[0], bb[2] - bb[0])
    top_delta = abs(ab[1] - bb[1])
    return shorter_width > 0 and horizontal / shorter_width >= 0.25 and top_delta > 4


def _resolve_overlapping_text_control_groups(
    compiled: DesignNode,
    source_by_id: dict[str, DesignNode],
    viewport: float,
) -> None:
    """Undo false horizontal rows caused by vertically overlapping text boxes.

    Figma text bounds may overlap vertically even when the elements form a
    vertical content stack. When one of those text blocks also owns small icon
    controls, keep the text stack vertical and express the icons as zero-net-flow
    overlays rather than Elementor absolute positioning.
    """
    for child in list(compiled.children):
        _resolve_overlapping_text_control_groups(child, source_by_id, viewport)

    for index, row in enumerate(list(compiled.children)):
        if row.kind != "container" or row.style.layout_direction != "horizontal":
            continue
        text_children = [child for child in row.children if child.kind == "text" and child.source_id in source_by_id]
        if len(text_children) < 2:
            continue

        overlapping_pair: tuple[DesignNode, DesignNode] | None = None
        for i, left in enumerate(text_children):
            for right in text_children[i + 1 :]:
                if _raw_text_overlap(source_by_id[left.source_id], source_by_id[right.source_id]):
                    overlapping_pair = (left, right)
                    break
            if overlapping_pair:
                break
        if not overlapping_pair:
            continue

        ordered = sorted(
            text_children,
            key=lambda node: (
                source_by_id[node.source_id].style.y or 0,
                source_by_id[node.source_id].style.x or 0,
            ),
        )
        owner = next((node for node in ordered if "\n" in (node.text or "")), ordered[0])
        owner_source = source_by_id[owner.source_id]
        owner_box = _box(owner_source)
        if owner_box is None:
            continue

        owned_icons: list[DesignNode] = []
        for sibling in compiled.children:
            if sibling.kind != "icon" or sibling.source_id not in source_by_id:
                continue
            source_icon = source_by_id[sibling.source_id]
            icon_box = _box(source_icon)
            if icon_box is None:
                continue
            horizontal = _overlap(owner_box[0], owner_box[2], icon_box[0], icon_box[2])
            vertical = _overlap(owner_box[1], owner_box[3], icon_box[1], icon_box[3])
            if horizontal > 0 and vertical > 0:
                owned_icons.append(sibling)

        group = DesignNode(
            kind="container",
            name=f"{owner.name or 'text'} controls",
            source_id=f"{owner.source_id or 'text'}::controls",
            style=DesignStyle(
                layout_direction="vertical",
                width_mode="fill",
                height_mode="hug",
                margin_top_percent=row.style.margin_top_percent,
                margin_left_percent=row.style.margin_left_percent,
            ),
            children=[owner],
        )
        owner.style.margin_top_percent = None
        owner.style.margin_left_percent = None

        for icon in sorted(owned_icons, key=lambda node: source_by_id[node.source_id].style.y or 0):
            icon_source = source_by_id[icon.source_id]
            icon_box = _box(icon_source)
            if icon_box is None:
                continue
            icon.style.position_mode = None
            icon.style.offset_x = None
            icon.style.offset_y = None
            icon.style.x = None
            icon.style.y = None
            icon.style.margin_left_percent = _percent(icon_box[0] - owner_box[0], viewport)
            icon.style.margin_top_percent = _percent(icon_box[1] - owner_box[3], viewport)
            icon.style.margin_bottom_percent = _percent(owner_box[3] - icon_box[1] - (icon_box[3] - icon_box[1]), viewport)
            group.children.append(icon)

        remaining_text = [node for node in ordered if node is not owner]
        replacement: list[DesignNode] = [group]
        previous_source = owner_source
        for text in remaining_text:
            text_source = source_by_id[text.source_id]
            prev_box = _box(previous_source)
            text_box = _box(text_source)
            if prev_box is None or text_box is None:
                continue
            text.style.margin_left_percent = row.style.margin_left_percent
            text.style.margin_top_percent = _percent(text_box[1] - prev_box[3], viewport)
            replacement.append(text)
            previous_source = text_source

        removed = set(id(node) for node in [row, *owned_icons])
        new_children: list[DesignNode] = []
        inserted = False
        for sibling in compiled.children:
            if id(sibling) in removed:
                if sibling is row and not inserted:
                    new_children.extend(replacement)
                    inserted = True
                continue
            new_children.append(sibling)
        compiled.children = new_children
        break


def resolve_compiled_spatial_relationships(
    compiled_root: DesignNode,
    source_root: DesignNode,
    design_viewport_width: float | None,
) -> DesignNode:
    viewport = design_viewport_width or 0
    if viewport <= 0:
        return compiled_root

    source_by_id = _source_map(source_root)
    _restore_relative_background(compiled_root, source_root, viewport)
    _resolve_overlapping_text_control_groups(compiled_root, source_by_id, viewport)
    return compiled_root


def resolve_inferred_region_overlays(
    root: DesignNode,
    design_viewport_width: float | None,
) -> DesignNode:
    """Convert region-owned absolute overlays into zero-net-flow overlays.

    Once the responsive compiler has inferred a semantic region, small overlays
    inside that region no longer need Elementor absolute positioning. A negative
    top margin moves the item back over the preceding media row, a compensating
    bottom margin keeps the region's flow height unchanged, and the horizontal
    offset becomes a percentage margin relative to the inferred region.
    """
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
