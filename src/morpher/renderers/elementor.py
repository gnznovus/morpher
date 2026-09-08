import hashlib

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle


def _element_id(node: DesignNode, path: str) -> str:
    """Return a stable 8-character Elementor element id for an IR node."""
    identity = f"{node.source_id or ''}|{node.kind}|{path}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]


def _size(unit: str, value: float) -> dict:
    return {"unit": unit, "size": value, "sizes": []}


def _dimensions(
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> dict:
    return {
        "unit": "px",
        "top": str(top),
        "right": str(right),
        "bottom": str(bottom),
        "left": str(left),
        "isLinked": top == right == bottom == left,
    }


def _alignment(value: str | None) -> str | None:
    mapping = {
        "min": "flex-start",
        "center": "center",
        "max": "flex-end",
        "space_between": "space-between",
    }
    return mapping.get((value or "").lower())


def _apply_item_sizing(settings: dict, style: DesignStyle, *, container: bool) -> None:
    if style.width_mode == "fill":
        if container:
            settings["width"] = _size("%", 100)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("%", 100)
    elif style.width_mode == "hug":
        if container and style.width is not None:
            # Elementor containers stretch by default. Preserve Figma's resolved
            # HUG width and make the container content span that intrinsic box.
            settings["width"] = _size("px", style.width)
            settings["content_width"] = "full"
        elif not container:
            settings["_element_width"] = "auto"
    elif style.width_mode == "fixed" and style.width is not None:
        if container:
            settings["width"] = _size("px", style.width)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("px", style.width)

    if style.height_mode == "fixed" and style.height is not None and container:
        settings["min_height"] = _size("px", style.height)


def _apply_child_alignment(
    settings: dict,
    style: DesignStyle,
    parent_style: DesignStyle | None,
    *,
    container: bool,
) -> None:
    if parent_style is None or (parent_style.counter_axis_align or "").lower() != "center":
        return

    # A stretched/fill child consumes the cross axis. HUG/FIXED children inherit
    # the parent's centered counter-axis placement.
    if (style.layout_align or "").lower() == "stretch" or style.width_mode == "fill":
        return

    if container:
        settings["align_self"] = "center"
    else:
        # Elementor's exported Heading JSON represents this visually with the
        # widget's native alignment control while keeping width=auto.
        settings["align"] = "center"


def _container_settings(
    style: DesignStyle,
    parent_style: DesignStyle | None = None,
) -> dict:
    settings: dict = {}

    if style.layout_direction:
        settings["flex_direction"] = "row" if style.layout_direction == "horizontal" else "column"

    justify = _alignment(style.primary_axis_align)
    if justify:
        settings["flex_justify_content"] = justify

    align = _alignment(style.counter_axis_align)
    if align:
        settings["flex_align_items"] = align

    if style.gap is not None:
        gap = str(style.gap)
        settings["flex_gap"] = {
            "column": gap,
            "row": gap,
            "isLinked": True,
            "unit": "px",
            "size": style.gap,
        }

    padding = (
        style.padding_top,
        style.padding_right,
        style.padding_bottom,
        style.padding_left,
    )
    if any(value is not None for value in padding):
        top, right, bottom, left = (value or 0 for value in padding)
        settings["padding"] = _dimensions(top, right, bottom, left)

    _apply_item_sizing(settings, style, container=True)
    _apply_child_alignment(settings, style, parent_style, container=True)

    if style.background:
        settings["background_background"] = "classic"
        settings["background_color"] = style.background

    if style.clips_content:
        settings["overflow"] = "hidden"

    return settings


def _heading_settings(
    node: DesignNode,
    parent_style: DesignStyle | None = None,
) -> dict:
    style = node.style
    settings: dict = {"title": node.text or ""}

    has_typography = any(
        value is not None
        for value in (
            style.font_family,
            style.font_weight,
            style.font_size,
            style.line_height,
            style.letter_spacing,
        )
    )
    if has_typography:
        settings["header_size"] = "div"
        settings["typography_typography"] = "custom"
        if style.font_family:
            settings["typography_font_family"] = style.font_family
        if style.font_weight is not None:
            settings["typography_font_weight"] = str(style.font_weight)
        if style.font_size is not None:
            settings["typography_font_size"] = _size("px", style.font_size)
        if style.line_height is not None:
            settings["typography_line_height"] = _size("px", style.line_height)
        if style.letter_spacing is not None:
            settings["typography_letter_spacing"] = _size("px", style.letter_spacing)

    if style.text_color:
        settings["title_color"] = style.text_color

    align_mapping = {
        "LEFT": "left",
        "CENTER": "center",
        "RIGHT": "right",
        "JUSTIFIED": "justify",
    }
    text_align = align_mapping.get(style.text_align_horizontal or "")
    if text_align:
        settings["align"] = text_align

    _apply_item_sizing(settings, style, container=False)
    _apply_child_alignment(settings, style, parent_style, container=False)
    return settings


def _render_heading(
    node: DesignNode,
    path: str,
    parent_style: DesignStyle | None = None,
) -> dict:
    return {
        "id": _element_id(node, path),
        "settings": _heading_settings(node, parent_style),
        "elements": [],
        "isInner": False,
        "widgetType": "heading",
        "elType": "widget",
    }


def _render_shape(
    node: DesignNode,
    path: str,
    parent_style: DesignStyle | None = None,
) -> dict:
    return {
        "id": _element_id(node, path),
        "settings": _container_settings(node.style, parent_style),
        "elements": [],
        "isInner": False,
        "elType": "container",
    }


def _render_container(
    node: DesignNode,
    path: str,
    parent_style: DesignStyle | None = None,
) -> dict:
    elements = []
    for index, child in enumerate(node.children):
        child_path = f"{path}.{index}"
        if child.kind == "container":
            elements.append(_render_container(child, child_path, node.style))
        elif child.kind == "text":
            elements.append(_render_heading(child, child_path, node.style))
        elif child.kind == "shape":
            elements.append(_render_shape(child, child_path, node.style))

    settings = _container_settings(node.style, parent_style)
    return {
        "id": _element_id(node, path),
        "settings": settings if settings else [],
        "elements": elements,
        "isInner": False,
        "elType": "container",
    }


def render_elementor(root: DesignNode) -> dict:
    """Render portable Elementor JSON from Morpher's shared Design IR."""
    if root.kind != "container":
        raise ValueError("Elementor template root must be a container")

    return {
        "content": [_render_container(root, "0")],
        "page_settings": [],
        "version": "0.4",
        "title": root.name or "Morpher Template",
        "type": "container",
    }
