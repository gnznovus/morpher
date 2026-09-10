from __future__ import annotations

import math

from morpher.ir.nodes import DesignNode


_RENDERABLE_KINDS = {"container", "text", "shape", "image", "icon", "divider"}
_ROTATION_EPSILON = 1e-4


def _class_name(node: DesignNode) -> str:
    source_id = (node.source_id or "node").replace(":", "-")
    return f"morpher-{source_id}"


def _asset_key(value: str | None) -> str:
    return (value or "").replace(":", "-")


def _px(value: float) -> str:
    return f"{value:g}px"


def _alignment(value: str | None) -> str | None:
    mapping = {
        "min": "flex-start",
        "max": "flex-end",
        "center": "center",
        "space_between": "space-between",
        "baseline": "baseline",
    }
    return mapping.get(value)


def _is_free_layout(parent: DesignNode | None) -> bool:
    return parent is not None and parent.style.layout_direction is None


def _relative_offset(child_value: float | None, parent_value: float | None) -> float | None:
    if child_value is None or parent_value is None:
        return None
    return child_value - parent_value


def _font_family(node: DesignNode) -> str | None:
    style = node.style
    if not style.font_family:
        return None
    return f'"{style.font_family}", sans-serif'


def _quarter_turn(rotation: float | None) -> int | None:
    if rotation is None:
        return None
    quarter = round(rotation / (math.pi / 2))
    if quarter == 0 or abs(rotation - quarter * (math.pi / 2)) > _ROTATION_EPSILON:
        return None
    return quarter


def _absolute_geometry(node: DesignNode, parent: DesignNode) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    style = node.style
    left = _relative_offset(style.x, parent.style.x)
    top = _relative_offset(style.y, parent.style.y)
    width = style.width
    height = style.height
    rotation_degrees: float | None = None

    # Figma LINE bounding boxes already encode their final orientation. Re-applying
    # quarter-turn reconstruction turns vertical zero-width dividers invisible.
    if node.kind != "divider":
        quarter = _quarter_turn(style.rotation)
        if quarter is not None:
            normalized = quarter % 4
            rotation_degrees = quarter * 90.0
            if normalized in (1, 3) and width is not None and height is not None:
                # Figma absoluteBoundingBox is post-rotation. Reconstruct the pre-rotation
                # box around the same center so CSS rotation reproduces the same bounds.
                original_width = height
                original_height = width
                if left is not None:
                    left += (width - original_width) / 2
                if top is not None:
                    top += (height - original_height) / 2
                width = original_width
                height = original_height

    return left, top, width, height, rotation_degrees


def _uses_outlined_text_asset(node: DesignNode, asset_sources: dict[str, str]) -> bool:
    if node.kind != "text":
        return False
    source = asset_sources.get(_asset_key(node.source_id))
    return bool(source and source.lower().endswith(".svg"))


def _declarations(
    node: DesignNode,
    parent: DesignNode | None,
    asset_sources: dict[str, str],
) -> list[str]:
    style = node.style
    is_root = parent is None
    is_absolute = _is_free_layout(parent)
    declarations = ["box-sizing: border-box"]

    if is_root:
        if style.width is not None:
            declarations.append(f"width: {_px(style.width)}")
        if style.height is not None:
            declarations.append(f"height: {_px(style.height)}")
    elif is_absolute:
        declarations.append("position: absolute")

        if _uses_outlined_text_asset(node, asset_sources):
            # Outlined Figma TEXT SVGs are exported with useAbsoluteBounds=true.
            # Their SVG canvas already matches the final post-rotation Figma
            # absoluteBoundingBox, so applying quarter-turn reconstruction again
            # swaps the box and rotates the already-rotated artwork a second time.
            left = _relative_offset(style.x, parent.style.x)
            top = _relative_offset(style.y, parent.style.y)
            width = style.width
            height = style.height
            rotation_degrees = None
        else:
            left, top, width, height, rotation_degrees = _absolute_geometry(node, parent)

        if left is not None:
            declarations.append(f"left: {_px(left)}")
        if top is not None:
            declarations.append(f"top: {_px(top)}")
        if width is not None:
            declarations.append(f"width: {_px(width)}")
        if height is not None:
            declarations.append(f"height: {_px(height)}")
        if rotation_degrees is not None:
            declarations.append(f"transform: rotate({rotation_degrees:g}deg)")
            declarations.append("transform-origin: center center")
    else:
        if style.width_mode == "fixed" and style.width is not None:
            declarations.append(f"width: {_px(style.width)}")
        elif style.width_mode == "fill":
            declarations.append("width: 100%")

        if style.height_mode == "fixed" and style.height is not None:
            declarations.append(f"height: {_px(style.height)}")

    if node.kind == "container" and style.layout_direction is None and not is_absolute:
        declarations.append("position: relative")

    if style.clips_content:
        declarations.append("overflow: hidden")

    if style.layout_direction:
        declarations.extend(("display: flex", f"flex-direction: {'row' if style.layout_direction == 'horizontal' else 'column'}"))
        if style.gap is not None:
            declarations.append(f"gap: {_px(style.gap)}")
        if all(value is not None for value in (style.padding_top, style.padding_right, style.padding_bottom, style.padding_left)):
            declarations.append(
                "padding: "
                + " ".join(_px(value) for value in (style.padding_top, style.padding_right, style.padding_bottom, style.padding_left))
            )
        primary = _alignment(style.primary_axis_align)
        counter = _alignment(style.counter_axis_align)
        if primary:
            declarations.append(f"justify-content: {primary}")
        if counter:
            declarations.append(f"align-items: {counter}")

    if not is_absolute:
        if style.layout_align == "stretch":
            declarations.append("align-self: stretch")
        if style.layout_grow is not None and style.layout_grow > 0:
            declarations.append(f"flex-grow: {style.layout_grow:g}")

    # SVG-backed icons already carry their own fill/stroke inside the asset.
    # Painting the IR fill as a CSS background turns vector bounds into solid boxes.
    if style.background and node.kind != "icon":
        declarations.append(f"background: {style.background}")

    if node.kind == "divider" and style.stroke_color:
        weight = style.stroke_weight if style.stroke_weight is not None else 1.0
        if (style.width or 0) >= (style.height or 0):
            declarations.append(f"border-top: {_px(weight)} solid {style.stroke_color}")
        else:
            declarations.append(f"border-left: {_px(weight)} solid {style.stroke_color}")
    elif node.kind == "shape" and style.stroke_color:
        weight = style.stroke_weight if style.stroke_weight is not None else 1.0
        declarations.append(f"border: {_px(weight)} solid {style.stroke_color}")

    if style.border_radius is not None:
        declarations.append(f"border-radius: {_px(style.border_radius)}")

    if node.kind == "image":
        declarations.extend(("display: block", "object-fit: cover"))
        if style.image_opacity is not None:
            declarations.append(f"opacity: {style.image_opacity:g}")
    elif node.kind == "icon":
        declarations.extend(("display: block", "object-fit: contain"))

    if node.kind == "text":
        if style.text_color:
            declarations.append(f"color: {style.text_color}")
        family = _font_family(node)
        if family:
            declarations.append(f"font-family: {family}")
        if style.font_size is not None:
            declarations.append(f"font-size: {_px(style.font_size)}")
        if style.font_weight is not None:
            declarations.append(f"font-weight: {style.font_weight}")
        if style.line_height is not None:
            declarations.append(f"line-height: {_px(style.line_height)}")
        if style.letter_spacing is not None:
            declarations.append(f"letter-spacing: {_px(style.letter_spacing)}")

        # JSON_REST_V1 preserves deliberate Figma line breaks in `characters`.
        # Keep those breaks (and meaningful leading spaces) instead of collapsing
        # them into one browser line. `pre-wrap` still permits wrapping if local
        # font metrics differ slightly from Figma.
        if "\n" in (node.text or ""):
            declarations.append("white-space: pre-wrap")
        elif style.text_auto_resize == "WIDTH_AND_HEIGHT":
            # Single-line auto-sized labels such as CHECK AVIABILITY should not
            # wrap merely because browser font metrics differ by a few pixels.
            declarations.append("white-space: nowrap")

    return declarations


def _walk(node: DesignNode, parent: DesignNode | None = None):
    yield node, parent
    for child in node.children:
        yield from _walk(child, node)


def render_css(
    root: DesignNode,
    asset_sources: dict[str, str] | None = None,
) -> str:
    """Render Design IR using flex for Auto Layout and absolute geometry for free layout."""
    sources = asset_sources or {}
    blocks = [
        "html, body {",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        "",
        ".morpher-text-outline {",
        "  display: block;",
        "}",
        "",
    ]
    for node, parent in _walk(root):
        if node.kind not in _RENDERABLE_KINDS:
            continue
        blocks.append(f".{_class_name(node)} {{")
        blocks.extend(f"  {declaration};" for declaration in _declarations(node, parent, sources))
        blocks.extend(("}", ""))
    return "\n".join(blocks)
