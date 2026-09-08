from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from morpher.compiler.layout import compile_responsive_layout
from morpher.compiler.normalizer import normalize
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.renderers.css import render_css
from morpher.renderers.elementor import render_elementor
from morpher.renderers.html import render_html
from morpher.storage.paths import StoragePaths


def _copy_assets(source: Path, storage: StoragePaths) -> dict[str, str]:
    source_dir = storage.figma_asset_dir(source)
    if not source_dir.exists():
        return {}

    target_dir = storage.html_asset_dir(source)
    target_dir.mkdir(parents=True, exist_ok=True)

    asset_sources: dict[str, str] = {}
    for asset in source_dir.iterdir():
        if not asset.is_file():
            continue
        target = target_dir / asset.name
        shutil.copy2(asset, target)
        asset_sources[asset.stem] = target.relative_to(storage.output_html).as_posix()
    return asset_sources


def render_path(path: Path) -> tuple[Path, Path, Path, int]:
    adapter = FigmaJsonAdapter()
    document = normalize(adapter.load(path))

    storage = StoragePaths()
    storage.ensure()
    html_path = storage.html_output(path)
    css_path = storage.css_output(path)
    elementor_path = storage.elementor_output(path)

    asset_sources = _copy_assets(path, storage)
    css = render_css(document.root)
    html = render_html(document.root, stylesheet=css_path.name, asset_sources=asset_sources)

    # Keep the HTML renderer on raw normalized geometry for fidelity/debugging.
    # Elementor receives a compiled flow layout whenever the free-layout
    # geometry can be represented safely without overlap.
    elementor_root = compile_responsive_layout(document.root)
    elementor = render_elementor(elementor_root)

    html_path.write_text(html, encoding="utf-8")
    css_path.write_text(css, encoding="utf-8")
    elementor_path.write_text(
        json.dumps(elementor, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    return html_path, css_path, elementor_path, len(document.warnings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a supported design source to HTML/CSS and Elementor JSON.")
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    args = parser.parse_args()

    try:
        html_path, css_path, elementor_path, warning_count = render_path(args.path)
        print(f"HTML: {html_path}")
        print(f"CSS: {css_path}")
        print(f"Elementor: {elementor_path}")
        print(f"Warnings: {warning_count}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
