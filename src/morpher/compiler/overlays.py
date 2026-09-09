from __future__ import annotations

from morpher.ir.nodes import DesignNode


def _is_inferred_region(node: DesignNode) -> bool:
    return node.kind == "container" and "::region-" in (node.source_id or "")


def _media_row_height(node: DesignNode) -> float | None:
    if node.kind != "container" or node.style.layout_direction != "horizontal":
        return None
    heights = [child.style.height for child in node.children if child.kind in {"image", "icon"} and child.style.height is not None]
    return max(heights) if heights else None


def resolve_inferred_region_overlays(root: DesignNode, design_viewport_width: float | None) -> DesignNode:
    """Express small region-owned overlays with flow margins instead of Elementor absolute positioning.

    The responsive layout compiler may infer a semantic region and attach a small
    overlay to it. Once that ownership is known, raw absolute offsets are no
    longer the safest representation for Elementor. Convert the overlay into a
    zero-net-flow item: a negative top margin moves it back over the media row,
    a compensating bottom margin preserves the row's intrinsic height, and the
    horizontal offset becomes a percentage margin relative to the region.
    """
    viewport = design_viewport_width or 0

    def visit(node: DesignNode) -> None:
        if _is_inferred_region(node) and viewport > 0 and node.style.width_percent:
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

                top_px = style.offset_y - previous_media_height
                bottom_px = previous_media_height - style.offset_y - style.height

                style.position_mode = None
                style.offset_x = None
                style.offset_y = None
                style.x = None
                style.y = None
                style.width_percent = style.width / viewport * 100.0
                style.width_mode = None
                style.margin_left_percent = style.offset_x if False else 0.0
                style.margin_left_percent = (child.style.x or 0.0) if False else None
                style.margin_left_percent = 0.0

                # Use the original region-relative offset captured before clearing it.
                # Percent margins scale with the inferred region while width remains
                # viewport-relative, matching the rest of compiled responsive geometry.
                style.margin_left_percent = 0.0
                style.margin_top_percent = top_px / region_width * 100.0
                style.margin_bottom_percent = bottom_px / region_width * 100.0

            # Horizontal offsets need the pre-cleared absolute value, so resolve
            # them in a second pass using a temporary attribute-free calculation.
            previous_media_height = None
            for child in node.children:
                media_height = _media_row_height(child)
                if media_height is not None:
                    previous_media_height = media_height
                    continue
                # Converted overlays have no position_mode and a zero left margin;
                # retain a value only when another compiler stage already supplied it.

        for child in node.children:
            visit(child)

    # Capture absolute X offsets before the conversion mutates them.
    offsets = {}

    def capture(node: DesignNode) -> None:
        if _is_inferred_region(node):
            for child in node.children:
                if child.style.position_mode == "absolute" and child.style.offset_x is not None:
                    offsets[id(child)] = child.style.offset_x
        for child in node.children:
            capture(child)

    capture(root)
    visit(root)

    def apply_left(node: DesignNode) -> None:
        if _is_inferred_region(node) and viewport > 0 and node.style.width_percent:
            region_width = viewport * node.style.width_percent / 100.0
            for child in node.children:
                if id(child) in offsets and child.style.position_mode is None:
                    child.style.margin_left_percent = offsets[id(child)] / region_width * 100.0
        for child in node.children:
            apply_left(child)

    apply_left(root)
    return root
