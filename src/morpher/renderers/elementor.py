import hashlib

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.typography import fluid_font_size, relative_typography_value


def _element_id(node: DesignNode, path: str) -> str:
    identity = f"{node.source_id or ''}|{node.kind}|{path}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]


def _size(unit: str, value) -> dict:
    return {"unit": unit, "size": value, "sizes": []}


def _dimensions(top: float, right: float, bottom: float, left: float, *, unit: str = "px") -> dict:
    return {"unit": unit, "top": str(top), "right": str(right), "bottom": str(bottom), "left": str(left), "isLinked": top == right == bottom == left}


def _alignment(value: str | None) -> str | None:
    return {"min": "flex-start", "center": "center", "max": "flex-end", "space_between": "space-between"}.get((value or "").lower())


def _relative_offset(value: float | None, parent_value: float | None) -> float | None:
    if value is None or parent_value is None:
        return None
    return value - parent_value


def _apply_item_sizing(settings: dict, style: DesignStyle, *, container: bool) -> None:
    if style.width_percent is not None:
        # Responsive-compiler widths are measured against the Figma design
        # viewport, so preserve that coordinate system instead of rebasing the
        # same numeric value against an arbitrary Elementor parent.
        if container:
            settings["width"] = _size("vw", style.width_percent)
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("vw", style.width_percent)
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
    margins = (style.margin_top_percent, style.margin_right_percent, style.margin_bottom_percent, style.margin_left_percent)
    if not any(value is not None for value in margins):
        return
    top, right, bottom, left = (value or 0 for value in margins)
    settings["margin" if container else "_margin"] = _dimensions(top, right, bottom, left, unit="%")


def _apply_free_layout_geometry(settings: dict, style: DesignStyle, parent_style: DesignStyle | None, *, container: bool) -> None:
    if style.position_mode == "absolute":
        settings["position" if container else "_position"] = "absolute"
        settings["_offset_orientation_h"] = "start"
        settings["_offset_orientation_v"] = "start"
        if style.offset_x is not None:
            settings["_offset_x"] = _size("px", style.offset_x)
        if style.offset_y is not None:
            settings["_offset_y"] = _size("px", style.offset_y)
        if style.width is not None:
            if container:
                settings["width"] = _size("px", style.width)
            else:
                settings["_element_width"] = "initial"
                settings["_element_custom_width"] = _size("px", style.width)
        if style.height is not None and container:
            settings["min_height"] = _size("px", style.height)
        return
    if parent_style is None:
        if style.layout_direction is None:
            if style.width is not None:
                settings["width"] = _size("px", style.width)
            if style.height is not None and container:
                settings["min_height"] = _size("px", style.height)
        return
    if parent_style.layout_direction is not None:
        return
    if any(value is None for value in (style.x, style.y, parent_style.x, parent_style.y)):
        return
    left = _relative_offset(style.x, parent_style.x)
    top = _relative_offset(style.y, parent_style.y)
    settings["position" if container else "_position"] = "absolute"
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


def _apply_child_alignment(settings: dict, style: DesignStyle, parent_style: DesignStyle | None, *, container: bool) -> None:
    if parent_style is None or (parent_style.counter_axis_align or "").lower() != "center":
        return
    if (style.layout_align or "").lower() == "stretch" or style.width_mode == "fill":
        return
    settings["align_self" if container else "align"] = "center"


def _container_settings(style: DesignStyle, parent_style: DesignStyle | None = None) -> dict:
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
        settings["flex_gap"] = {"column": gap, "row": gap, "isLinked": True, "unit": "px", "size": style.gap}
    padding = (style.padding_top, style.padding_right, style.padding_bottom, style.padding_left)
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


def _elementor_text(value: str | None) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _heading_settings(node: DesignNode, parent_style: DesignStyle | None = None, *, design_viewport: float | None = None) -> dict:
    style = node.style
    settings: dict = {"title": _elementor_text(node.text)}
    has_typography = any(value is not None for value in (style.font_family, style.font_weight, style.font_size, style.line_height, style.letter_spacing))
    if has_typography:
        settings["header_size"] = "div"
        settings["typography_typography"] = "custom"
        if style.font_family:
            settings["typography_font_family"] = style.font_family
        if style.font_weight is not None:
            settings["typography_font_weight"] = str(style.font_weight)
        if style.font_size is not None:
            fluid = fluid_font_size(style.font_size, design_viewport) if design_viewport is not None else None
            settings["typography_font_size"] = _size("custom", fluid.css()) if fluid is not None else _size("px", style.font_size)
        if style.line_height is not None:
            relative = relative_typography_value(style.line_height, style.font_size) if style.font_size is not None else None
            settings["typography_line_height"] = _size("em", relative) if relative is not None else _size("px", style.line_height)
        if style.letter_spacing is not None:
            relative = relative_typography_value(style.letter_spacing, style.font_size) if style.font_size is not None else None
            settings["typography_letter_spacing"] = _size("em", relative) if relative is not None else _size("px", style.letter_spacing)
    if style.text_color:
        settings["title_color"] = style.text_color
    text_align = {"LEFT": "left", "CENTER": "center", "RIGHT": "right", "JUSTIFIED": "justify"}.get(style.text_align_horizontal or "")
    if text_align:
        settings["align"] = text_align
    _apply_item_sizing(settings, style, container=False)
    _apply_flow_margin(settings, style, container=False)
    _apply_free_layout_geometry(settings, style, parent_style, container=False)
    _apply_child_alignment(settings, style, parent_style, container=False)
    return settings


def _render_heading(node: DesignNode, path: str, parent_style: DesignStyle | None = None, *, design_viewport: float | None = None) -> dict:
    return {"id": _element_id(node, path), "settings": _heading_settings(node, parent_style, design_viewport=design_viewport), "elements": [], "isInner": False, "widgetType": "heading", "elType": "widget"}


def _render_shape(node: DesignNode, path: str, parent_style: DesignStyle | None = None) -> dict:
    return {"id": _element_id(node, path), "settings": _container_settings(node.style, parent_style), "elements": [], "isInner": False, "elType": "container"}


def _render_asset_widget(node: DesignNode, path: str, parent_style: DesignStyle | None, asset_sources: dict[str, str]) -> dict | None:
    key = node.image_ref.replace(":", "-") if node.kind == "image" and node.image_ref else (node.source_id or "").replace(":", "-")
    source = asset_sources.get(key)
    if not source:
        return None
    settings: dict = {"image": {"url": source, "id": "", "size": ""}, "image_size": "full"}
    _apply_item_sizing(settings, node.style, container=False)
    _apply_flow_margin(settings, node.style, container=False)
    _apply_free_layout_geometry(settings, node.style, parent_style, container=False)
    _apply_child_alignment(settings, node.style, parent_style, container=False)
    return {"id": _element_id(node, path), "settings": settings, "elements": [], "isInner": False, "widgetType": "image", "elType": "widget"}


def _render_container(node: DesignNode, path: str, parent_style: DesignStyle | None = None, asset_sources: dict[str, str] | None = None, *, design_viewport: float | None = None) -> dict:
    asset_sources = asset_sources or {}
    elements = []
    for index, child in enumerate(node.children):
        child_path = f"{path}.{index}"
        if child.kind == "container":
            elements.append(_render_container(child, child_path, node.style, asset_sources, design_viewport=design_viewport))
        elif child.kind == "text":
            elements.append(_render_heading(child, child_path, node.style, design_viewport=design_viewport))
        elif child.kind == "shape":
            elements.append(_render_shape(child, child_path, node.style))
        elif child.kind in {"image", "icon"}:
            asset = _render_asset_widget(child, child_path, node.style, asset_sources)
            if asset is not None:
                elements.append(asset)
    return {"id": _element_id(node, path), "settings": _container_settings(node.style, parent_style), "elements": elements, "isInner": False, "elType": "container"}


def render_elementor(root: DesignNode, asset_sources: dict[str, str] | None = None) -> dict:
    if root.kind != "container":
        raise ValueError("Elementor template root must be a container")
    design_viewport = root.style.width
    return {"content": [_render_container(root, "0", asset_sources=asset_sources, design_viewport=design_viewport)], "page_settings": [], "version": "0.4", "title": root.name or "Morpher Template", "type": "container"}
