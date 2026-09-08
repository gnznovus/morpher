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
    *,
    unit: str = "px",
) -> dict:
    return {
        "unit": unit,
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


def _relative_offset(value: float | None, parent_value: float | None) -> float | None:
    if value is None or parent_value is None:
        return None
    return value - parent_value


def _apply_item_sizing(settings: dict, style: DesignStyle, *, container: bool) -> None:
    if style.width_percent is not None:
        if container:
            settings["width"] = _size("%", style.width_percent)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("%", style.width_percent)
    elif style.width_mode == "fill":
        if container:
            settings["width"] = _size("%", 100)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("%", 100)
    elif style.width_mode == "hug":
        if container and style.width is not None:
            settings["width"] = _size("px", style.width)
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


def _apply_flow_margin(settings: dict, style: DesignStyle, *, container: bool) -> None:
    margins = (
        style.margin_top_percent,
        style.margin_right_percent,
        style.margin_bottom_percent,
        style.margin_left_percent,
    )
    if not any(value is not None for value in margins):
        return

    top, right, bottom, left = (value or 0 for value in margins)
    settings["margin" if container else "_margin"] = _dimensions(
        top,
        right,
        bottom,
        left,
        unit="%",
    )


def _apply_free_layout_geometry(
    settings: dict,
    style: DesignStyle,
    parent_style: DesignStyle | None,
    *,
    container: bool,
) -> None:
    """Mirror raw free-layout geometry only when concrete coordinates exist."""
    if parent_style is None:
        if style.layout_direction is None:
            if style.width is not None:
                settings["width"] = _size("px", style.width)
            if style.height is not None and container:
                settings["min_height"] = _size("px", style.height)
        return

    if parent_style.layout_direction is not None:
        return

    if any(
        value is None
        for value in (style.x, style.y, parent_style.x, parent_style.y)
    ):
        return

    left = _relative_offset(style.x, parent_style.x)
    top = _relative_offset(style.y, parent_style.y)

    if container:
        settings["position"] = "absolute"
    else:
        settings["_position"] = "absolute"

    settings["_offset_orientation_h"] = "start"
    settings["_offset_orientation_v"] = "start"
    if left is not None:
        settings["_offset_x"] = _size("px", left)
    if top is not None:
        settings["_offset_y"] = _size("px", top)

    if style.width is not None:
        if container:
            settings["width"] = _size("px", style.width)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("px", style.width)

    if style.height is not None and container:
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

    if (style.layout_align or "").lower() == "stretch" or style.width_mode == "fill":
        return

    if container:
        settings["align_self"] = "center"
    else:
        settings["align"] = "center"


def _container_settings(
    style: DesignStyle,
    parent_style: DesignStyle | None = None,
) -> dict:
    settings: dict = {"content_width": "full"}

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
    _apply_flow_margin(settings, style, container=True)
    _apply_free_layout_geometry(settings, style, parent_style, container=True)
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
    _apply_flow_margin(settings, style, container=False)
    _apply_free_layout_geometry(settings, style, parent_style, container=False)
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
        "settings": settings,
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
