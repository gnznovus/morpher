from __future__ import annotations

from html import escape

from morpher.ir.nodes import DesignNode


_RENDERABLE_KINDS = {"container", "text", "shape"}


def _class_name(node: DesignNode) -> str:
    source_id = (node.source_id or "node").replace(":", "-")
    return f"morpher-{source_id}"


def _render_node(node: DesignNode, depth: int = 1) -> list[str]:
    if node.kind not in _RENDERABLE_KINDS:
        return []

    indent = "  " * depth
    class_name = _class_name(node)

    if node.kind == "text":
        return [f'{indent}<div class="{class_name}">{escape(node.text or "")}</div>']

    lines = [f'{indent}<div class="{class_name}">']
    for child in node.children:
        lines.extend(_render_node(child, depth + 1))
    lines.append(f"{indent}</div>")
    return lines


def render_html(root: DesignNode, stylesheet: str = "styles.css") -> str:
    """Render the first verified Design IR slice to standalone HTML."""
    body = _render_node(root)
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
