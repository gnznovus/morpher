import hashlib

from morpher.ir.nodes import DesignNode


def _element_id(node: DesignNode, path: str) -> str:
    """Return a stable 8-character Elementor element id for an IR node."""
    identity = f"{node.source_id or ''}|{node.kind}|{path}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]


def _render_heading(node: DesignNode, path: str) -> dict:
    return {
        "id": _element_id(node, path),
        "settings": {"title": node.text or ""},
        "elements": [],
        "isInner": False,
        "widgetType": "heading",
        "elType": "widget",
    }


def _render_container(node: DesignNode, path: str) -> dict:
    elements = []
    for index, child in enumerate(node.children):
        child_path = f"{path}.{index}"
        if child.kind == "container":
            elements.append(_render_container(child, child_path))
        elif child.kind == "text":
            elements.append(_render_heading(child, child_path))

    return {
        "id": _element_id(node, path),
        "settings": [],
        "elements": elements,
        "isInner": False,
        "elType": "container",
    }


def render_elementor(root: DesignNode) -> dict:
    """Render the first portable Elementor slice: container + heading."""
    if root.kind != "container":
        raise ValueError("Elementor template root must be a container")

    return {
        "content": [_render_container(root, "0")],
        "page_settings": [],
        "version": "0.4",
        "title": root.name or "Morpher Template",
        "type": "container",
    }
