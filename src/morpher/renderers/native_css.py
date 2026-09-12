from __future__ import annotations

from pathlib import Path
from typing import Callable

from morpher.fonts.css import package_font_face, render_font_resolution_css
from morpher.fonts.resolver import FontResolution, resolve_font_intent
from morpher.ir.nodes import DesignNode
from morpher.renderers.native_html import dom_id


FontIntentResolver = Callable[..., FontResolution]


def render_native_css(
    root: DesignNode,
    *,
    font_root: Path,
    font_cache: Path,
    font_asset_dir: Path,
    css_dir: Path,
    resolver: FontIntentResolver = resolve_font_intent,
) -> str:
    """Render the first Native CSS slice: real typography and packaged font faces."""
    font_blocks: list[str] = []
    rules: list[str] = []
    emitted_faces: set[tuple[str, int, str, str | None]] = set()

    for node in _walk(root):
        declarations: list[str] = []
        intent = node.style.font
        if intent is not None:
            resolution = resolver(font_root, font_cache, intent)
            if resolution.face is not None:
                face = resolution.face
                if face.key not in emitted_faces:
                    packaged = package_font_face(face, font_asset_dir)
                    font_blocks.append(
                        render_font_resolution_css(
                            resolution,
                            packaged_sources=packaged,
                            css_dir=css_dir,
                        )
                    )
                    emitted_faces.add(face.key)
                declarations.extend(
                    [
                        f'font-family: "{_escape(face.family)}";',
                        f"font-weight: {face.weight};",
                        f"font-style: {face.style};",
                    ]
                )
            else:
                font_blocks.append(f'/* MORPHER FONT: "{intent.family}" is unavailable */\n')
                declarations.extend(
                    [
                        f'font-family: "{_escape(intent.family)}";',
                        f"font-weight: {intent.weight};",
                        f"font-style: {intent.style};",
                    ]
                )

        if node.style.font_size is not None:
            declarations.append(f"font-size: {_px(node.style.font_size)};")
        if node.style.line_height is not None:
            declarations.append(f"line-height: {_px(node.style.line_height)};")
        if node.style.letter_spacing is not None:
            declarations.append(f"letter-spacing: {_px(node.style.letter_spacing)};")
        text_transform = _text_transform(node.style.text_case)
        if text_transform:
            declarations.append(f"text-transform: {text_transform};")
        if node.style.text_color:
            declarations.append(f"color: {node.style.text_color};")
        if node.style.text_align_horizontal:
            declarations.append(f"text-align: {node.style.text_align_horizontal.casefold()};")

        if declarations:
            rules.append(_rule(dom_id(node), declarations))

    return "\n".join(font_blocks + rules).rstrip() + "\n"


def _text_transform(value: str | None) -> str | None:
    return {
        "UPPER": "uppercase",
        "LOWER": "lowercase",
        "TITLE": "capitalize",
    }.get(value or "")


def _walk(node: DesignNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _rule(identity: str, declarations: list[str]) -> str:
    body = "\n".join(f"  {declaration}" for declaration in declarations)
    return f".{identity} {{\n{body}\n}}\n"


def _px(value: float) -> str:
    return f"{value:g}px"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
