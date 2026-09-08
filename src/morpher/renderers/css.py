from __future__ import annotations

from morpher.ir.nodes import DesignNode


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


def _declarations(node: DesignNode, is_root: bool) -> list[str]:
    style = node.style
    declarations = ["box-sizing: border-box"]

    if is_root:
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
        elif style.height_mode == "fill":
            declarations.append("flex-grow: 1")

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

    if style.layout_align == "stretch":
        declarations.append("align-self: stretch")
    if style.layout_grow is not None and style.layout_grow > 0:
        declarations.append(f"flex-grow: {style.layout_grow:g}")

    if style.background:
        declarations.append(f"background: {style.background}")

    if node.kind == "text":
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


def _walk(node: DesignNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def render_css(root: DesignNode) -> str:
    """Render container/text/shape IR and Auto Layout as deterministic CSS."""
    blocks = ["html, body {", "  margin: 0;", "  padding: 0;", "}", ""]
    for node in _walk(root):
        if node.kind not in {"container", "text", "shape"}:
            continue
        blocks.append(f".{_class_name(node)} {{")
        blocks.extend(f"  {declaration};" for declaration in _declarations(node, node is root))
        blocks.extend(("}", ""))
    return "\n".join(blocks)
