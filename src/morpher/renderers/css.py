from __future__ import annotations

from morpher.ir.nodes import DesignNode


_RENDERABLE_KINDS = {"container", "text", "shape", "image", "icon", "divider"}


def _class_name(node: DesignNode) -> str:
    source_id = (node.source_id or "node").replace(":", "-")
    return f"morpher-{source_id}"


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


def _declarations(node: DesignNode, parent: DesignNode | None) -> list[str]:
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

        left = _relative_offset(style.x, parent.style.x)
        top = _relative_offset(style.y, parent.style.y)
        if left is not None:
            declarations.append(f"left: {_px(left)}")
        if top is not None:
            declarations.append(f"top: {_px(top)}")
        if style.width is not None:
            declarations.append(f"width: {_px(style.width)}")
        if style.height is not None:
            declarations.append(f"height: {_px(style.height)}")
    else:
        if style.width_mode == "fixed" and style.width is not None:
            declarations.append(f"width: {_px(style.width)}")
        elif style.width_mode == "fill":
            declarations.append("width: 100%")

        if style.height_mode == "fixed" and style.height is not None:
            declarations.append(f"height: {_px(style.height)}")

    if node.kind == "container" and style.layout_direction is None and not is_absolute:
        declarations.append("position: relative")

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

    if style.background:
        declarations.append(f"background: {style.background}")

    if node.kind == "divider" and style.stroke_color:
        weight = style.stroke_weight if style.stroke_weight is not None else 1.0
        if (style.width or 0) >= (style.height or 0):
            declarations.append(f"border-top: {_px(weight)} solid {style.stroke_color}")
        else:
            declarations.append(f"border-left: {_px(weight)} solid {style.stroke_color}")

    if node.kind == "image":
        declarations.extend(("display: block", "object-fit: cover"))
    elif node.kind == "icon":
        declarations.extend(("display: block", "object-fit: contain"))

    if node.kind == "text":
        if style.text_color:
            declarations.append(f"color: {style.text_color}")
        if style.font_family:
            declarations.append(f'font-family: "{style.font_family}", sans-serif')
        if style.font_size is not None:
            declarations.append(f"font-size: {_px(style.font_size)}")
        if style.font_weight is not None:
            declarations.append(f"font-weight: {style.font_weight}")
        if style.line_height is not None:
            declarations.append(f"line-height: {_px(style.line_height)}")
        if style.letter_spacing is not None:
            declarations.append(f"letter-spacing: {_px(style.letter_spacing)}")

    return declarations


def _walk(node: DesignNode, parent: DesignNode | None = None):
    yield node, parent
    for child in node.children:
        yield from _walk(child, node)


def render_css(root: DesignNode) -> str:
    """Render Design IR using flex for Auto Layout and absolute geometry for free layout."""
    blocks = ["html, body {", "  margin: 0;", "  padding: 0;", "}", ""]
    for node, parent in _walk(root):
        if node.kind not in _RENDERABLE_KINDS:
            continue
        blocks.append(f".{_class_name(node)} {{")
        blocks.extend(f"  {declaration};" for declaration in _declarations(node, parent))
        blocks.extend(("}", ""))
    return "\n".join(blocks)
