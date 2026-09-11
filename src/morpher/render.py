from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from morpher.assets import semantic_asset_names
from morpher.compiler.normalizer import normalize
from morpher.compiler.responsive import compile_for_responsive_render
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.renderers.css import render_css
from morpher.renderers.elementor import render_elementor
from morpher.renderers.html import render_html
from morpher.renderers.native_css import render_native_css
from morpher.renderers.native_html import render_native_html
from morpher.storage.paths import StoragePaths


@dataclass(frozen=True)
class RenderOutputs:
    fidelity_html: Path | None
    fidelity_css: Path | None
    native_html: Path | None
    native_css: Path | None
    elementor: Path
    warning_count: int


def _copy_assets(
    source: Path,
    storage: StoragePaths,
    root: DesignNode,
    target_dir: Path,
    relative_root: Path,
) -> dict[str, str]:
    source_dir = storage.figma_asset_dir(source)
    if not source_dir.exists():
        return {}

    target_dir.mkdir(parents=True, exist_ok=True)

    assets = [asset for asset in source_dir.iterdir() if asset.is_file()]
    semantic_names = semantic_asset_names(root, assets)
    asset_sources: dict[str, str] = {}
    for asset in assets:
        target = target_dir / semantic_names[asset.stem]
        try:
            shutil.copy2(asset, target)
        except OSError as exc:
            raise OSError(
                f"Could not package Figma asset {asset!s} -> {target!s}: {exc}"
            ) from exc
        asset_sources[asset.stem] = target.relative_to(relative_root).as_posix()
    return asset_sources


def _text_source_keys(root: DesignNode) -> set[str]:
    keys: set[str] = set()

    def walk(node: DesignNode) -> None:
        if node.kind == "text" and node.source_id:
            keys.add(node.source_id.replace(":", "-"))
        for child in node.children:
            walk(child)

    walk(root)
    return keys


def _native_layout_asset_sources(
    root: DesignNode,
    asset_sources: dict[str, str],
) -> dict[str, str]:
    """Hide outlined text assets from layout CSS while retaining image/icon assets."""
    text_keys = _text_source_keys(root)
    return {key: value for key, value in asset_sources.items() if key not in text_keys}


def render_path(
    path: Path,
    *,
    fidelity: bool = True,
    native: bool = True,
) -> RenderOutputs:
    adapter = FigmaJsonAdapter()
    document = normalize(adapter.load(path))

    storage = StoragePaths()
    storage.ensure()
    elementor_path = storage.elementor_output(path)

    fidelity_html_path: Path | None = None
    fidelity_css_path: Path | None = None
    native_html_path: Path | None = None
    native_css_path: Path | None = None

    if fidelity:
        fidelity_html_path = storage.fidelity_html_output(path)
        fidelity_css_path = storage.fidelity_css_output(path)
        fidelity_asset_sources = _copy_assets(
            path,
            storage,
            document.root,
            storage.fidelity_asset_dir(path),
            storage.output_html_fidelity,
        )
        fidelity_css = render_css(document.root, asset_sources=fidelity_asset_sources)
        fidelity_html = render_html(
            document.root,
            stylesheet=fidelity_css_path.name,
            asset_sources=fidelity_asset_sources,
        )
        fidelity_html_path.write_text(fidelity_html, encoding="utf-8")
        fidelity_css_path.write_text(fidelity_css, encoding="utf-8")

    if native:
        native_root = compile_for_responsive_render(document.root)
        native_html_path = storage.native_html_output(path)
        native_css_path = storage.native_css_output(path)
        native_asset_sources = _copy_assets(
            path,
            storage,
            document.root,
            storage.native_asset_dir(path),
            storage.output_html_native,
        )
        native_layout_sources = _native_layout_asset_sources(document.root, native_asset_sources)
        native_layout_css = render_css(
            native_root,
            asset_sources=native_layout_sources,
            responsive=True,
        )
        native_font_css = render_native_css(
            native_root,
            font_root=storage.fonts,
            font_cache=storage.font_registry_cache,
            font_asset_dir=storage.native_font_asset_dir(),
            css_dir=storage.output_html_native,
        )
        native_css = native_layout_css.rstrip() + "\n\n" + native_font_css
        native_html = render_native_html(
            native_root,
            stylesheet=native_css_path.name,
            asset_sources=native_asset_sources,
        )
        native_html_path.write_text(native_html, encoding="utf-8")
        native_css_path.write_text(native_css, encoding="utf-8")

    elementor_asset_sources = _copy_assets(
        path,
        storage,
        document.root,
        storage.elementor_asset_dir(path),
        storage.output_elementor,
    )

    # Native and Elementor each receive an independent compiled tree. Fidelity
    # stays on normalized source geometry so its diagnostic contract is unchanged.
    elementor_root = compile_for_responsive_render(document.root)
    elementor = render_elementor(elementor_root, asset_sources=elementor_asset_sources)
    elementor_path.write_text(
        json.dumps(elementor, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    return RenderOutputs(
        fidelity_html=fidelity_html_path,
        fidelity_css=fidelity_css_path,
        native_html=native_html_path,
        native_css=native_css_path,
        elementor=elementor_path,
        warning_count=len(document.warnings),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a supported design source to Fidelity/Native HTML and Elementor JSON."
    )
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    parser.add_argument("--fidelity", action="store_true", help="Render the Fidelity HTML target.")
    parser.add_argument("--native", action="store_true", help="Render the Native HTML target.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force selected outputs to be rebuilt (renders currently overwrite outputs already).",
    )
    args = parser.parse_args()

    if not args.fidelity and not args.native:
        render_fidelity = True
        render_native = True
    else:
        render_fidelity = args.fidelity
        render_native = args.native

    try:
        outputs = render_path(
            args.path,
            fidelity=render_fidelity,
            native=render_native,
        )
        if outputs.fidelity_html is not None:
            print(f"Fidelity HTML: {outputs.fidelity_html}")
            print(f"Fidelity CSS: {outputs.fidelity_css}")
        if outputs.native_html is not None:
            print(f"Native HTML: {outputs.native_html}")
            print(f"Native CSS: {outputs.native_css}")
        print(f"Elementor: {outputs.elementor}")
        print(f"Warnings: {outputs.warning_count}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
