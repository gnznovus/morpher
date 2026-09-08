from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from morpher.compiler.normalizer import normalize
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.renderers.css import render_css
from morpher.renderers.html import render_html
from morpher.storage.paths import StoragePaths


def _copy_image_assets(source: Path, storage: StoragePaths) -> dict[str, str]:
    source_dir = storage.figma_asset_dir(source)
    if not source_dir.exists():
        return {}

    target_dir = storage.html_asset_dir(source)
    target_dir.mkdir(parents=True, exist_ok=True)

    image_sources: dict[str, str] = {}
    for asset in source_dir.iterdir():
        if not asset.is_file():
            continue
        target = target_dir / asset.name
        shutil.copy2(asset, target)
        image_sources[asset.stem] = target.relative_to(storage.output_html).as_posix()
    return image_sources


def render_path(path: Path) -> tuple[Path, Path, int]:
    adapter = FigmaJsonAdapter()
    document = normalize(adapter.load(path))

    storage = StoragePaths()
    storage.ensure()
    html_path = storage.html_output(path)
    css_path = storage.css_output(path)

    image_sources = _copy_image_assets(path, storage)
    css = render_css(document.root)
    html = render_html(document.root, stylesheet=css_path.name, image_sources=image_sources)

    html_path.write_text(html, encoding="utf-8")
    css_path.write_text(css, encoding="utf-8")

    return html_path, css_path, len(document.warnings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a supported design source to HTML/CSS.")
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    args = parser.parse_args()

    try:
        html_path, css_path, warning_count = render_path(args.path)
        print(f"HTML: {html_path}")
        print(f"CSS: {css_path}")
        print(f"Warnings: {warning_count}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
