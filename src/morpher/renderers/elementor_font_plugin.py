from __future__ import annotations

from pathlib import Path
from typing import Callable

from morpher.fonts.css import package_font_face, render_font_resolution_css
from morpher.fonts.resolver import FontResolution, resolve_font_intent
from morpher.ir.nodes import DesignNode


FontIntentResolver = Callable[..., FontResolution]

_PLUGIN_PHP = r'''<?php
/**
 * Plugin Name: Morpher Font Injector
 * Description: Loads Morpher-packaged font faces in Elementor frontend and editor preview.
 * Version: 0.1.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

function morpher_font_injector_enqueue() {
    $css_path = plugin_dir_path( __FILE__ ) . 'assets/fonts.css';
    if ( ! file_exists( $css_path ) ) {
        return;
    }

    wp_enqueue_style(
        'morpher-font-injector',
        plugin_dir_url( __FILE__ ) . 'assets/fonts.css',
        array(),
        (string) filemtime( $css_path )
    );
}

add_action( 'wp_enqueue_scripts', 'morpher_font_injector_enqueue', 1 );
add_action( 'elementor/frontend/after_enqueue_styles', 'morpher_font_injector_enqueue', 1 );
add_action( 'elementor/editor/after_enqueue_styles', 'morpher_font_injector_enqueue', 1 );
add_action( 'elementor/preview/enqueue_styles', 'morpher_font_injector_enqueue', 1 );
'''


def render_elementor_font_plugin(
    root: DesignNode,
    *,
    font_root: Path,
    font_cache: Path,
    output_dir: Path,
    resolver: FontIntentResolver = resolve_font_intent,
) -> Path:
    """Build a tiny WordPress plugin that injects resolved Morpher fonts into Elementor."""
    assets_dir = output_dir / "assets"
    font_dir = assets_dir / "fonts"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    font_dir.mkdir(parents=True, exist_ok=True)

    plugin_path = output_dir / "morpher-font-injector.php"
    css_path = assets_dir / "fonts.css"
    plugin_path.write_text(_PLUGIN_PHP, encoding="utf-8")

    blocks: list[str] = []
    emitted_faces: set[tuple[str, int, str, str | None]] = set()

    for node in _walk(root):
        intent = node.style.font
        if intent is None:
            continue

        resolution = resolver(font_root, font_cache, intent)
        if resolution.face is None:
            blocks.append(f'/* MORPHER FONT: "{intent.family}" is unavailable */\n')
            continue

        face = resolution.face
        if face.key in emitted_faces:
            continue

        packaged = package_font_face(face, font_dir)
        blocks.append(
            render_font_resolution_css(
                resolution,
                packaged_sources=packaged,
                css_dir=assets_dir,
            )
        )
        emitted_faces.add(face.key)

    css_path.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")
    return output_dir


def _walk(node: DesignNode):
    yield node
    for child in node.children:
        yield from _walk(child)
