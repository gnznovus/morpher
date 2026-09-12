from __future__ import annotations

from html import escape

from morpher.ir.nodes import DesignNode


_RENDERABLE_KINDS = {"container", "text", "shape", "image", "button", "icon", "divider", "absolute"}


def dom_id(node: DesignNode) -> str:
    source_id = node.source_id or "node"
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in source_id)
    return f"morpher-{safe}"


def _attrs(node: DesignNode, *, extra_class: str | None = None) -> str:
    identity = dom_id(node)
    classes = identity if extra_class is None else f"{identity} {extra_class}"
    source_id = escape(node.source_id or "", quote=True)
    return (
        f'id="{escape(identity, quote=True)}" '
        f'class="{escape(classes, quote=True)}" '
        f'data-morpher-source-id="{source_id}"'
    )


def _asset_key(value: str | None) -> str:
    return (value or "").replace(":", "-")


def _render_node(node: DesignNode, asset_sources: dict[str, str], depth: int = 1) -> list[str]:
    if node.kind not in _RENDERABLE_KINDS:
        return []

    indent = "  " * depth
    attrs = _attrs(node)

    if node.kind == "text":
        # Native always preserves real text. Fidelity owns outlined-text SVG rendering.
        return [f"{indent}<div {attrs}>{escape(node.text or '')}</div>"]

    if node.kind == "image":
        source = asset_sources.get(_asset_key(node.image_ref))
        if source:
            return [
                f'{indent}<img {attrs} src="{escape(source, quote=True)}" '
                f'alt="{escape(node.name or "", quote=True)}">'
            ]
        return [f"{indent}<div {attrs}></div>"]

    if node.kind == "icon":
        source = asset_sources.get(_asset_key(node.source_id))
        if source:
            return [
                f'{indent}<img {attrs} src="{escape(source, quote=True)}" '
                'alt="" aria-hidden="true">'
            ]
        return [f"{indent}<div {attrs}></div>"]

    tag = "button" if node.kind == "button" else "div"
    lines = [f"{indent}<{tag} {attrs}>"]
    if node.kind == "button" and node.text:
        lines.append(f"{indent}  {escape(node.text)}")
    for child in node.children:
        lines.extend(_render_node(child, asset_sources, depth + 1))
    lines.append(f"{indent}</{tag}>")
    return lines


def render_native_html(
    root: DesignNode,
    stylesheet: str = "styles.css",
    asset_sources: dict[str, str] | None = None,
) -> str:
    """Render semantic/editable Morpher Native HTML from Design IR."""
    body = _render_node(root, asset_sources or {})
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'  <link rel="stylesheet" href="{escape(stylesheet, quote=True)}">',
        "  <title>Morpher Native Output</title>",
        "</head>",
        "<body>",
        *body,
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)
