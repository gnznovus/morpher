from __future__ import annotations

from html import escape

from morpher.ir.nodes import DesignNode


_RENDERABLE_KINDS = {"container", "text", "shape", "image"}


def _class_name(node: DesignNode) -> str:
    source_id = (node.source_id or "node").replace(":", "-")
    return f"morpher-{source_id}"


def _render_node(node: DesignNode, image_sources: dict[str, str], depth: int = 1) -> list[str]:
    if node.kind not in _RENDERABLE_KINDS:
        return []

    indent = "  " * depth
    class_name = _class_name(node)

    if node.kind == "text":
        return [f'{indent}<div class="{class_name}">{escape(node.text or "")}</div>']

    if node.kind == "image":
        source = image_sources.get(node.image_ref or "")
        if source:
            return [
                f'{indent}<img class="{class_name}" src="{escape(source, quote=True)}" alt="{escape(node.name or "", quote=True)}">'
            ]
        return [f'{indent}<div class="{class_name}"></div>']

    lines = [f'{indent}<div class="{class_name}">']
    for child in node.children:
        lines.extend(_render_node(child, image_sources, depth + 1))
    lines.append(f"{indent}</div>")
    return lines


def render_html(root: DesignNode, stylesheet: str = "styles.css", image_sources: dict[str, str] | None = None) -> str:
    """Render Design IR to standalone HTML using already-resolved local image assets."""
    body = _render_node(root, image_sources or {})
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'  <link rel="stylesheet" href="{escape(stylesheet, quote=True)}">',
        "  <title>Morpher Output</title>",
        "</head>",
        "<body>",
        *body,
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)
