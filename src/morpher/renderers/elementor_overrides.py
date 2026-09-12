from __future__ import annotations

import hashlib

from morpher.ir.nodes import DesignNode
from morpher.renderers.elementor import render_elementor


def _element_id(node: DesignNode, path: str) -> str:
    identity = f"{node.source_id or ''}|{node.kind}|{path}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]


def _dimensions(top: float, right: float, bottom: float, left: float) -> dict:
    return {
        "unit": "px",
        "top": str(top),
        "right": str(right),
        "bottom": str(bottom),
        "left": str(left),
        "isLinked": top == right == bottom == left,
    }


def _rendered_by_id(elementor: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    stack = list(elementor.get("content", []))
    while stack:
        element = stack.pop()
        element_id = element.get("id")
        if element_id:
            result[element_id] = element
        stack.extend(element.get("elements", []))
    return result


def _apply_node_override(node: DesignNode, path: str, rendered: dict[str, dict]) -> None:
    element = rendered.get(_element_id(node, path))
    if element is not None:
        settings = element.setdefault("settings", {})
        style = node.style

        if node.kind == "container" and (style.layout_align or "").lower() == "center":
            settings["align_self"] = "center"

        sides = (
            style.border_top_width,
            style.border_right_width,
            style.border_bottom_width,
            style.border_left_width,
        )
        if style.stroke_color and any(value is not None for value in sides):
            weight = style.stroke_weight if style.stroke_weight is not None else 1.0
            top, right, bottom, left = (weight if value is None else value for value in sides)
            prefix = "_" if element.get("widgetType") == "spacer" else ""
            settings[f"{prefix}border_border"] = "solid"
            settings[f"{prefix}border_color"] = style.stroke_color
            settings[f"{prefix}border_width"] = _dimensions(top, right, bottom, left)

    for index, child in enumerate(node.children):
        _apply_node_override(child, f"{path}.{index}", rendered)


def render_elementor_with_ir_overrides(
    root: DesignNode,
    asset_sources: dict[str, str] | None = None,
) -> dict:
    elementor = render_elementor(root, asset_sources=asset_sources)
    _apply_node_override(root, "0", _rendered_by_id(elementor))
    return elementor
