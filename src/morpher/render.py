from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from morpher.assets import prepare_elementor_assets, semantic_asset_names
from morpher.compiler.contact import compile_contact_spatial_layout
from morpher.compiler.elementor_spatial import compile_elementor_spatial_structure
from morpher.compiler.normalizer import normalize
from morpher.compiler.responsive import compile_for_responsive_render
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.renderers.css import render_css
from morpher.renderers.elementor import render_elementor
from morpher.renderers.elementor_font_plugin import render_elementor_font_plugin
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
    elementor_font_plugin: Path | None = None
    font_warnings: tuple[str, ...] = ()


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


def _prepare_elementor_assets(
    source: Path,
    storage: StoragePaths,
    root: DesignNode,
) -> dict[str, str]:
    source_dir = storage.figma_asset_dir(source)
    if not source_dir.exists():
        return {}

    assets = [asset for asset in source_dir.iterdir() if asset.is_file()]
    return prepare_elementor_assets(
        root,
        assets,
        storage.elementor_asset_dir(source),
        storage.output_elementor,
    )


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


def _fluidize_fidelity_absolute_css(css: str, root: DesignNode) -> str:
    """Temporary experiment: make raw Fidelity absolute geometry scale with its owner.

    This deliberately leaves flow/flex declarations alone. For every child that is
    already absolute in Fidelity, px left/top/width/height values are converted to
    percentages of the child's immediate owner. The root becomes a responsive
    aspect-ratio box so percentage-based vertical geometry has a stable reference.
    """

    def class_name(node: DesignNode) -> str:
        return f"morpher-{(node.source_id or 'node').replace(':', '-')}"

    def replace_px(block: str, prop: str, basis: float | None) -> str:
        if not basis:
            return block
        pattern = rf"({prop}: )(-?\d+(?:\.\d+)?)px;"

        def replacement(match: re.Match[str]) -> str:
            value = float(match.group(2))
            percent = value / basis * 100.0
            if abs(percent) < 1e-9:
                percent = 0.0
            return f"{match.group(1)}{percent:.6f}%;"

        return re.sub(pattern, replacement, block)

    def walk(node: DesignNode) -> None:
        nonlocal css
        for child in node.children:
            marker = f".{class_name(child)} {{"
            start = css.find(marker)
            if start >= 0:
                end = css.find("}\n", start)
                if end >= 0:
                    end += 2
                    block = css[start:end]
                    if "position: absolute;" in block:
                        block = replace_px(block, "left", node.style.width)
                        block = replace_px(block, "width", node.style.width)
                        block = replace_px(block, "top", node.style.height)
                        block = replace_px(block, "height", node.style.height)
                        css = css[:start] + block + css[end:]
            walk(child)

    walk(root)

    if root.style.width and root.style.height:
        marker = f".{class_name(root)} {{"
        start = css.find(marker)
        if start >= 0:
            end = css.find("}\n", start)
            if end >= 0:
                end += 2
                block = css[start:end]
                block = re.sub(r"width: -?\d+(?:\.\d+)?px;", "width: 100%;", block, count=1)
                block = re.sub(
                    r"height: -?\d+(?:\.\d+)?px;",
                    f"aspect-ratio: {root.style.width:g} / {root.style.height:g};\n  height: auto;",
                    block,
                    count=1,
                )
                css = css[:start] + block + css[end:]

    return css


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
        # TEMPORARY EXPERIMENT: preserve Fidelity's raw absolute relationships but
        # express their geometry relative to the owning container instead of px.
        fidelity_css = _fluidize_fidelity_absolute_css(fidelity_css, document.root)
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

    elementor_asset_sources = _prepare_elementor_assets(
        path,
        storage,
        document.root,
    )

    # Elementor preserves the source composition. Contact blocks get one narrow
    # relationship pass that splits icon-aligned multiline text into spatial rows.
    # A second spatial pass restores authored ownership for narrow side rails and
    # normalizes rotated Figma lines for Elementor's transform model.
    elementor_root = compile_contact_spatial_layout(document.root)
    elementor_root = compile_elementor_spatial_structure(elementor_root)
    elementor = render_elementor(elementor_root, asset_sources=elementor_asset_sources)
    elementor_path.write_text(
        json.dumps(elementor, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    font_warnings: list[str] = []
    elementor_font_plugin = render_elementor_font_plugin(
        elementor_root,
        font_root=storage.fonts,
        font_cache=storage.font_registry_cache,
        output_dir=storage.elementor_font_plugin,
        diagnostics=font_warnings,
    )

    return RenderOutputs(
        fidelity_html=fidelity_html_path,
        fidelity_css=fidelity_css_path,
        native_html=native_html_path,
        native_css=native_css_path,
        elementor=elementor_path,
        warning_count=len(document.warnings),
        elementor_font_plugin=elementor_font_plugin,
        font_warnings=tuple(font_warnings),
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
        if outputs.elementor_font_plugin is not None:
            print(f"Elementor Font Plugin: {outputs.elementor_font_plugin}")
        print(f"Warnings: {outputs.warning_count}")
        for warning in outputs.font_warnings:
            print(warning)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
