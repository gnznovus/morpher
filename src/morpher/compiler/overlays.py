from __future__ import annotations

from morpher.ir.nodes import DesignNode


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
