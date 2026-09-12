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


def _box(node: DesignNode) -> tuple[float, float, float, float] | None:
    style = node.style
    if any(value is None for value in (style.x, style.y, style.width, style.height)):
        return None
    return style.x, style.y, style.x + style.width, style.y + style.height


def _contains_center(container: DesignNode, child: DesignNode) -> bool:
    outer = _box(container)
    inner = _box(child)
    if outer is None or inner is None:
        return False
    center_x = (inner[0] + inner[2]) / 2.0
    center_y = (inner[1] + inner[3]) / 2.0
    return outer[0] <= center_x <= outer[2] and outer[1] <= center_y <= outer[3]


def _area(node: DesignNode) -> float:
    box = _box(node)
    if box is None:
        return float("inf")
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


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


def _walk_with_paths(root: DesignNode) -> list[tuple[DesignNode, str]]:
    result: list[tuple[DesignNode, str]] = []

    def visit(node: DesignNode, path: str) -> None:
        result.append((node, path))
        for index, child in enumerate(node.children):
            visit(child, f"{path}.{index}")

    visit(root, "0")
    return result


def _apply_border_override(
    node: DesignNode,
    path: str,
    rendered: dict[str, dict],
    *,
    bottom_zero: bool = False,
) -> None:
    element = rendered.get(_element_id(node, path))
    if element is None or not node.style.stroke_color:
        return

    style = node.style
    weight = style.stroke_weight if style.stroke_weight is not None else 1.0
    sides = (
        style.border_top_width,
        style.border_right_width,
        0.0 if bottom_zero else style.border_bottom_width,
        style.border_left_width,
    )
    top, right, bottom, left = (weight if value is None else value for value in sides)
    settings = element.setdefault("settings", {})
    prefix = "_" if element.get("widgetType") == "spacer" else ""
    settings[f"{prefix}border_border"] = "solid"
    settings[f"{prefix}border_color"] = style.stroke_color
    settings[f"{prefix}border_width"] = _dimensions(top, right, bottom, left)


def _apply_contact_overrides(root: DesignNode, rendered: dict[str, dict]) -> None:
    nodes = _walk_with_paths(root)

    # Generated Contact/Amenities pairs are horizontal containers. The container
    # uses Align Items: Center, while its direct icon/wording widgets keep their
    # own Alignment at Start.
    for node, path in nodes:
        if node.kind != "container" or "::contact-item-" not in (node.source_id or ""):
            continue
        element = rendered.get(_element_id(node, path))
        if element is None:
            continue
        settings = element.setdefault("settings", {})
        settings["flex_align_items"] = "center"
        settings.pop("align_self", None)
        for child in element.get("elements", []):
            if child.get("elType") == "widget":
                child.setdefault("settings", {})["align"] = "left"

    # The newsletter label and its stroked rectangle may live in different Figma
    # groups. Use final authored geometry instead of tree ownership: choose the
    # smallest stroked shape containing the center of each SUBMIT label.
    submits = [
        (node, path)
        for node, path in nodes
        if node.kind == "text" and (node.text or "").strip().upper() == "SUBMIT"
    ]
    shapes = [
        (node, path)
        for node, path in nodes
        if node.kind == "shape" and node.style.stroke_color and _box(node) is not None
    ]
    for submit, _ in submits:
        candidates = [(shape, path) for shape, path in shapes if _contains_center(shape, submit)]
        if not candidates:
            continue
        border, border_path = min(candidates, key=lambda pair: _area(pair[0]))
        _apply_border_override(border, border_path, rendered, bottom_zero=True)


def _apply_explicit_ir_overrides(root: DesignNode, rendered: dict[str, dict]) -> None:
    for node, path in _walk_with_paths(root):
        element = rendered.get(_element_id(node, path))
        if element is None:
            continue
        style = node.style
        settings = element.setdefault("settings", {})

        if node.kind == "container" and (style.layout_align or "").lower() == "center":
            settings["align_self"] = "center"

        sides = (
            style.border_top_width,
            style.border_right_width,
            style.border_bottom_width,
            style.border_left_width,
        )
        if style.stroke_color and any(value is not None for value in sides):
            _apply_border_override(node, path, rendered)


def render_elementor_with_ir_overrides(
    root: DesignNode,
    asset_sources: dict[str, str] | None = None,
) -> dict:
    elementor = render_elementor(root, asset_sources=asset_sources)
    rendered = _rendered_by_id(elementor)
    _apply_explicit_ir_overrides(root, rendered)
    _apply_contact_overrides(root, rendered)
    return elementor
