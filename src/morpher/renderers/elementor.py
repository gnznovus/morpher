import hashlib
import re

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


def _relative_percent(value: float | None, basis: float | None) -> float | None:
    if value is None or basis in (None, 0):
        return None
    percent = value / basis * 100.0
    return 0.0 if abs(percent) < 1e-9 else percent


def _composition_vw(value: float | None, design_viewport: float | None) -> float | None:
    """Express one authored spatial measurement on the page composition scale."""
    return _relative_percent(value, design_viewport)


def _is_fluid_absolute(style: DesignStyle, parent_style: DesignStyle | None) -> bool:
    return parent_style is not None and (
        style.position_mode == "absolute" or parent_style.layout_direction is None
    )


def _is_fluid_composition(style: DesignStyle, parent_style: DesignStyle | None) -> bool:
    return _is_fluid_absolute(style, parent_style) or (
        parent_style is not None and parent_style.position_mode == "absolute"
    )


def _asset_key(image_ref: str) -> str:
    return image_ref.replace(":", "-")


def _overlay_color(background: str | None, alpha: float) -> str:
    if background:
        rgba = re.fullmatch(r"rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)(?:\s*,\s*[\d.]+)?\s*\)", background)
        if rgba:
            r, g, b = rgba.groups()
            return f"rgba({r}, {g}, {b}, {alpha})"
        if re.fullmatch(r"#[0-9a-fA-F]{6}", background):
            r = int(background[1:3], 16)
            g = int(background[3:5], 16)
            b = int(background[5:7], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
    return f"rgba(0, 0, 0, {alpha})"


def _apply_item_sizing(settings: dict, style: DesignStyle, *, container: bool) -> None:
    if style.width_percent is not None:
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


def _set_fluid_absolute_size(
    settings: dict,
    style: DesignStyle,
    *,
    container: bool,
    design_viewport: float | None,
) -> None:
    if not container and style.text_auto_resize == "WIDTH_AND_HEIGHT":
        settings["_element_width"] = "auto"
        settings.pop("_element_custom_width", None)
        return

    width_vw = _composition_vw(style.width, design_viewport)
    if width_vw is not None:
        if container:
            width = _size("vw", width_vw)
            settings["width"] = width
            settings["width_mobile"] = width
        else:
            settings["_element_width"] = "initial"
            settings["_element_custom_width"] = _size("vw", width_vw)

    height_vw = _composition_vw(style.height, design_viewport)
    if container and height_vw is not None:
        height = _size("vw", height_vw)
        settings["min_height"] = height
        settings["min_height_mobile"] = height


def _apply_fluid_composition_size(
    settings: dict,
    style: DesignStyle,
    parent_style: DesignStyle | None,
    *,
    container: bool,
    design_viewport: float | None,
) -> None:
    if parent_style is None or parent_style.position_mode != "absolute":
        return
    if style.position_mode == "absolute":
        return
    _set_fluid_absolute_size(
        settings,
        style,
        container=container,
        design_viewport=design_viewport,
    )


def _apply_free_layout_geometry(
    settings: dict,
    style: DesignStyle,
    parent_style: DesignStyle | None,
    *,
    container: bool,
    design_viewport: float | None,
) -> None:
    if parent_style is None:
        if style.layout_direction is None:
            settings["width"] = _size("%", 100)
            root_height_vw = _composition_vw(style.height, design_viewport)
            if container and root_height_vw is not None:
                settings["min_height"] = _size("vw", root_height_vw)
        return

    if not _is_fluid_absolute(style, parent_style):
        return

    if style.position_mode == "absolute":
        left = style.offset_x
        top = style.offset_y
    else:
        if any(value is None for value in (style.x, style.y, parent_style.x, parent_style.y)):
            return
        left = _relative_offset(style.x, parent_style.x)
        top = _relative_offset(style.y, parent_style.y)

    settings["position" if container else "_position"] = "absolute"
    settings["_offset_orientation_h"] = "start"
    settings["_offset_orientation_v"] = "start"

    left_vw = _composition_vw(left, design_viewport)
    top_vw = _composition_vw(top, design_viewport)
    if left_vw is not None:
        settings["_offset_x"] = _size("vw", left_vw)
    if top_vw is not None:
        settings["_offset_y"] = _size("vw", top_vw)

    _set_fluid_absolute_size(
        settings,
        style,
        container=container,
        design_viewport=design_viewport,
    )


def _apply_child_alignment(settings: dict, style: DesignStyle, parent_style: DesignStyle | None, *, container: bool) -> None:
    if parent_style is None or (parent_style.counter_axis_align or "").lower() != "center":
        return
    if (style.layout_align or "").lower() == "stretch" or style.width_mode == "fill":
        return
    settings["align_self" if container else "align"] = "center"


def _apply_container_border(settings: dict, style: DesignStyle) -> None:
    if style.stroke_color:
        weight = style.stroke_weight if style.stroke_weight is not None else 1.0
        settings["border_border"] = "solid"
        settings["border_color"] = style.stroke_color
        settings["border_width"] = _dimensions(weight, weight, weight, weight)
    if style.border_radius is not None:
        radius = style.border_radius
        settings["border_radius"] = _dimensions(radius, radius, radius, radius)


def _container_settings(
    style: DesignStyle,
    parent_style: DesignStyle | None = None,
    asset_sources: dict[str, str] | None = None,
    *,
    design_viewport: float | None = None,
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
        gap_unit = "px"
        gap_size = style.gap
        if _is_fluid_composition(style, parent_style):
            fluid_gap = _composition_vw(style.gap, design_viewport)
            if fluid_gap is not None:
                gap_unit = "vw"
                gap_size = fluid_gap
        gap = str(gap_size)
        settings["flex_gap"] = {"column": gap, "row": gap, "isLinked": True, "unit": gap_unit, "size": gap_size}
    padding = (style.padding_top, style.padding_right, style.padding_bottom, style.padding_left)
    if any(value is not None for value in padding):
        top, right, bottom, left = (value or 0 for value in padding)
        settings["padding"] = _dimensions(top, right, bottom, left)
    _apply_item_sizing(settings, style, container=True)
    _apply_flow_margin(settings, style, container=True)
    _apply_free_layout_geometry(settings, style, parent_style, container=True, design_viewport=design_viewport)
    _apply_fluid_composition_size(settings, style, parent_style, container=True, design_viewport=design_viewport)
    _apply_child_alignment(settings, style, parent_style, container=True)
    _apply_container_border(settings, style)
    if style.background:
        settings["background_background"] = "classic"
        settings["background_color"] = style.background
    if style.background_image_ref and asset_sources:
        source = asset_sources.get(_asset_key(style.background_image_ref))
        if source:
            settings["background_background"] = "classic"
            settings["background_image"] = {"url": source, "id": "", "size": ""}
            settings["background_position"] = "center center"
            settings["background_repeat"] = "no-repeat"
            settings["background_size"] = "cover"
            if style.background_image_opacity is not None and style.background_image_opacity < 1:
                settings["background_overlay_background"] = "classic"
                settings["background_overlay_color"] = _overlay_color(style.background, 1.0 - style.background_image_opacity)
    if style.clips_content:
        settings["overflow"] = "hidden"
    return settings


def _elementor_text(value: str | None) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _text_transform(value: str | None) -> str | None:
    return {
        "UPPER": "uppercase",
        "LOWER": "lowercase",
        "TITLE": "capitalize",
    }.get(value or "")


def _source_is_single_line(node: DesignNode) -> bool:
    text = (node.text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text or "\n" in text:
        return False

    style = node.style
    line_box = style.line_height or style.font_size
    if line_box is None or style.height is None:
        return style.text_auto_resize == "WIDTH_AND_HEIGHT"

    return style.height <= line_box * 1.5


def _heading_settings(node: DesignNode, parent_style: DesignStyle | None = None, *, design_viewport: float | None = None) -> dict:
    style = node.style
    settings: dict = {"title": _elementor_text(node.text)}
    has_typography = any(value is not None for value in (style.font_family, style.font_weight, style.font_size, style.line_height, style.letter_spacing, style.text_case))
    if has_typography:
        settings["header_size"] = "div"
        settings["typography_typography"] = "custom"
        if style.font_family:
            settings["typography_font_family"] = style.font_family
        if style.font_weight is not None:
            settings["typography_font_weight"] = str(style.font_weight)
        if style.font_size is not None:
            fluid = None
            if design_viewport is not None:
                minimum_px = 0.0 if _is_fluid_composition(style, parent_style) else None
                fluid = fluid_font_size(style.font_size, design_viewport, minimum_px=minimum_px)
            settings["typography_font_size"] = _size("custom", fluid.css()) if fluid is not None else _size("px", style.font_size)
        if style.line_height is not None:
            relative = relative_typography_value(style.line_height, style.font_size) if style.font_size is not None else None
            settings["typography_line_height"] = _size("em", relative) if relative is not None else _size("px", style.line_height)
        if style.letter_spacing is not None:
            relative = relative_typography_value(style.letter_spacing, style.font_size) if style.font_size is not None else None
            settings["typography_letter_spacing"] = _size("em", relative) if relative is not None else _size("px", style.letter_spacing)
        text_transform = _text_transform(style.text_case)
        if text_transform:
            settings["typography_text_transform"] = text_transform
    if style.text_color:
        settings["title_color"] = style.text_color
    text_align = {"LEFT": "left", "CENTER": "center", "RIGHT": "right", "JUSTIFIED": "justify"}.get(style.text_align_horizontal or "")
    if text_align:
        settings["align"] = text_align
    _apply_item_sizing(settings, style, container=False)
    _apply_flow_margin(settings, style, container=False)
    _apply_free_layout_geometry(settings, style, parent_style, container=False, design_viewport=design_viewport)
    _apply_fluid_composition_size(settings, style, parent_style, container=False, design_viewport=design_viewport)
    if _is_fluid_composition(style, parent_style) and _source_is_single_line(node):
        settings["_element_width"] = "auto"
        settings.pop("_element_custom_width", None)
    _apply_child_alignment(settings, style, parent_style, container=False)
    return settings


def _render_heading(node: DesignNode, path: str, parent_style: DesignStyle | None = None, *, design_viewport: float | None = None) -> dict:
    return {"id": _element_id(node, path), "settings": _heading_settings(node, parent_style, design_viewport=design_viewport), "elements": [], "isInner": False, "widgetType": "heading", "elType": "widget"}


def _render_shape(node: DesignNode, path: str, parent_style: DesignStyle | None = None, asset_sources: dict[str, str] | None = None, *, design_viewport: float | None = None) -> dict:
    style = node.style
    if style.stroke_color and not style.background and style.height is not None and style.border_radius is None:
        settings: dict = {}
        _apply_item_sizing(settings, style, container=False)
        _apply_flow_margin(settings, style, container=False)
        _apply_free_layout_geometry(settings, style, parent_style, container=False, design_viewport=design_viewport)
        _apply_fluid_composition_size(settings, style, parent_style, container=False, design_viewport=design_viewport)
        _apply_child_alignment(settings, style, parent_style, container=False)
        height_vw = _composition_vw(style.height, design_viewport)
        if height_vw is not None:
            space = _size("custom", f"{height_vw:g}vw")
            settings["space"] = space
            settings["space_mobile"] = space
        weight = style.stroke_weight if style.stroke_weight is not None else 1.0
        settings["_border_border"] = "solid"
        settings["_border_color"] = style.stroke_color
        settings["_border_width"] = _dimensions(weight, weight, weight, weight)
        return {"id": _element_id(node, path), "settings": settings, "elements": [], "isInner": False, "widgetType": "spacer", "elType": "widget"}
    return {"id": _element_id(node, path), "settings": _container_settings(style, parent_style, asset_sources, design_viewport=design_viewport), "elements": [], "isInner": False, "elType": "container"}


def _render_divider(node: DesignNode, path: str, parent_style: DesignStyle | None = None, *, design_viewport: float | None = None) -> dict:
    style = node.style
    settings: dict = {"style": "solid", "gap": _size("px", 0)}
    if style.stroke_color:
        settings["color"] = style.stroke_color
    if style.stroke_weight is not None:
        settings["weight"] = _size("px", style.stroke_weight)
    _apply_item_sizing(settings, style, container=False)
    _apply_flow_margin(settings, style, container=False)
    _apply_free_layout_geometry(settings, style, parent_style, container=False, design_viewport=design_viewport)
    _apply_fluid_composition_size(settings, style, parent_style, container=False, design_viewport=design_viewport)
    _apply_child_alignment(settings, style, parent_style, container=False)
    return {"id": _element_id(node, path), "settings": settings, "elements": [], "isInner": False, "widgetType": "divider", "elType": "widget"}


def _is_background_image_layer(node: DesignNode, parent_style: DesignStyle | None) -> bool:
    if node.kind != "image" or parent_style is None:
        return False
    if node.style.width is None or node.style.height is None:
        return False
    if parent_style.width in (None, 0) or parent_style.height in (None, 0):
        return False
    return (
        node.style.width >= parent_style.width * 0.9
        and node.style.height >= parent_style.height * 0.9
    )


def _render_asset_widget(node: DesignNode, path: str, parent_style: DesignStyle | None, asset_sources: dict[str, str], *, design_viewport: float | None = None) -> dict | None:
    key = _asset_key(node.image_ref) if node.kind == "image" and node.image_ref else (node.source_id or "").replace(":", "-")
    source = asset_sources.get(key)
    if not source:
        return None
    settings: dict = {"image": {"url": source, "id": "", "size": ""}, "image_size": "full"}
    if node.kind == "image" and node.style.image_opacity is not None:
        settings["opacity"] = _size("px", node.style.image_opacity)
        settings["css_filters_css_filter"] = "custom"
        settings["css_filters_opacity"] = _size("px", node.style.image_opacity * 100)
    if _is_background_image_layer(node, parent_style):
        settings["_z_index"] = 0
    _apply_item_sizing(settings, node.style, container=False)
    _apply_flow_margin(settings, node.style, container=False)
    _apply_free_layout_geometry(settings, node.style, parent_style, container=False, design_viewport=design_viewport)
    _apply_fluid_composition_size(settings, node.style, parent_style, container=False, design_viewport=design_viewport)
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
            elements.append(_render_shape(child, child_path, node.style, asset_sources, design_viewport=design_viewport))
        elif child.kind == "divider":
            elements.append(_render_divider(child, child_path, node.style, design_viewport=design_viewport))
        elif child.kind in {"image", "icon"}:
            asset = _render_asset_widget(child, child_path, node.style, asset_sources, design_viewport=design_viewport)
            if asset is not None:
                elements.append(asset)
    return {"id": _element_id(node, path), "settings": _container_settings(node.style, parent_style, asset_sources, design_viewport=design_viewport), "elements": elements, "isInner": False, "elType": "container"}


def render_elementor(root: DesignNode, asset_sources: dict[str, str] | None = None) -> dict:
    if root.kind != "container":
        raise ValueError("Elementor template root must be a container")
    design_viewport = root.style.width
    return {"content": [_render_container(root, "0", asset_sources=asset_sources, design_viewport=design_viewport)], "page_settings": [], "version": "0.4", "title": root.name or "Morpher Template", "type": "container"}
