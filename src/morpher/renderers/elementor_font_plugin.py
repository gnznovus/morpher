from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from morpher.fonts.css import package_font_face, render_font_resolution_css
from morpher.fonts.resolver import FontResolution, resolve_font_intent
from morpher.ir.nodes import DesignNode


FontIntentResolver = Callable[..., FontResolution]

_PLUGIN_PHP = r'''<?php
/**
 * Plugin Name: Morpher
 * Description: WordPress integration for Morpher-generated Elementor output.
 * Version: 0.1.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

function morpher_plugin_enqueue_fonts() {
    $css_path = plugin_dir_path( __FILE__ ) . 'assets/fonts.css';
    if ( ! file_exists( $css_path ) ) {
        return;
    }

    wp_enqueue_style(
        'morpher-fonts',
        plugin_dir_url( __FILE__ ) . 'assets/fonts.css',
        array(),
        (string) filemtime( $css_path )
    );
}

add_action( 'wp_enqueue_scripts', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/frontend/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/editor/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/preview/enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
'''

_MANIFEST_VERSION = 1


def render_elementor_font_plugin(
    root: DesignNode,
    *,
    font_root: Path,
    font_cache: Path,
    output_dir: Path,
    resolver: FontIntentResolver = resolve_font_intent,
) -> Path:
    """Update the persistent Morpher WordPress plugin with fonts required by this design.

    The plugin directory is intentionally persistent across renders. Each render merges
    newly resolved faces into a small manifest instead of replacing fonts required by
    previously generated Elementor pages.
    """
    assets_dir = output_dir / "assets"
    font_dir = assets_dir / "fonts"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    font_dir.mkdir(parents=True, exist_ok=True)

    plugin_path = output_dir / "morpher-plugin.php"
    css_path = assets_dir / "fonts.css"
    manifest_path = assets_dir / "fonts.json"
    plugin_path.write_text(_PLUGIN_PHP, encoding="utf-8")

    manifest = _load_manifest(manifest_path)
    faces: dict[str, dict] = manifest.setdefault("faces", {})

    for node in _walk(root):
        intent = node.style.font
        if intent is None:
            continue

        resolution = resolver(font_root, font_cache, intent)
        if resolution.face is None:
            continue

        face = resolution.face
        key = _face_key(face.key)
        if key in faces:
            continue

        packaged = package_font_face(face, font_dir)
        css = render_font_resolution_css(
            resolution,
            packaged_sources=packaged,
            css_dir=assets_dir,
        )
        faces[key] = {
            "family": face.family,
            "weight": face.weight,
            "style": face.style,
            "flavor": face.flavor,
            "css": css,
        }

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    css_path.write_text(
        "\n".join(faces[key]["css"].rstrip() for key in sorted(faces)).rstrip() + "\n",
        encoding="utf-8",
    )
    return output_dir


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"version": _MANIFEST_VERSION, "faces": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": _MANIFEST_VERSION, "faces": {}}
    if data.get("version") != _MANIFEST_VERSION or not isinstance(data.get("faces"), dict):
        return {"version": _MANIFEST_VERSION, "faces": {}}
    return data


def _face_key(key: tuple[str, int, str, str | None]) -> str:
    family, weight, style, flavor = key
    return "|".join((family, str(weight), style.casefold(), (flavor or "").casefold()))


def _walk(node: DesignNode):
    yield node
    for child in node.children:
        yield from _walk(child)
