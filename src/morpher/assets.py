from __future__ import annotations

import io
import re
import shutil
from pathlib import Path

from PIL import Image
import resvg_py

from morpher.ir.nodes import DesignNode

_MAX_CONTEXT_LENGTH = 48
_MAX_NODE_NAME_LENGTH = 72


def _slug(value: str | None, fallback: str, max_length: int | None = None) -> str:
    text = (value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or fallback
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].rstrip("-")
    return text or fallback


def _node_asset_slug(node: DesignNode) -> str:
    full = _slug(node.name, node.kind)
    if len(full) <= _MAX_NODE_NAME_LENGTH:
        return full

    # Figma often uses the full text contents as a TEXT node name. Keep a
    # readable prefix, then append the source id so the shortened filename can
    # still be traced directly back to the original Figma node.
    trace = _slug(node.source_id, node.kind, max_length=24)
    prefix_length = max(1, _MAX_NODE_NAME_LENGTH - len(trace) - 1)
    prefix = full[:prefix_length].rstrip("-")
    return f"{prefix}-{trace}"


def semantic_asset_names(root: DesignNode, source_assets: list[Path]) -> dict[str, str]:
    """Map raw Figma asset keys to deterministic human-facing filenames.

    The root name provides semantic context while the original Figma node name
    is preserved for traceability. Raw hashes/source ids remain lookup keys only.

    Long Figma text-node names are bounded for cross-platform filesystem safety;
    their shortened name keeps a readable prefix plus the Figma source id.

    ``source_assets`` describes exported asset paths; callers may pass discovered
    filesystem paths or synthetic Paths in unit tests, so existence is deliberately
    not checked here. Filesystem filtering belongs to the discovery/copy boundary.
    """
    context = _slug(root.name, "design", max_length=_MAX_CONTEXT_LENGTH)
    assets_by_key = {asset.stem: asset for asset in source_assets}
    result: dict[str, str] = {}
    used: set[str] = set()

    def reserve(base: str, suffix: str) -> str:
        candidate = f"{base}{suffix}"
        index = 2
        while candidate in used:
            candidate = f"{base}-{index}{suffix}"
            index += 1
        used.add(candidate)
        return candidate

    def visit(node: DesignNode) -> None:
        keys: list[str] = []
        if node.kind == "image" and node.image_ref:
            keys.append(node.image_ref.replace(":", "-"))
        if node.kind in {"icon", "text"} and node.source_id:
            keys.append(node.source_id.replace(":", "-"))

        for key in keys:
            asset = assets_by_key.get(key)
            if asset is not None and key not in result:
                node_name = _node_asset_slug(node)
                result[key] = reserve(f"{context}-{node_name}", asset.suffix.lower())

        for child in node.children:
            visit(child)

    visit(root)

    # Preserve exported assets that are not represented by a renderable IR node,
    # but never expose their raw Figma key as the human-facing filename.
    orphan_index = 1
    for key, asset in assets_by_key.items():
        if key in result:
            continue
        result[key] = reserve(f"{context}-asset-{orphan_index}", asset.suffix.lower())
        orphan_index += 1

    return result


def elementor_asset_keys(root: DesignNode) -> set[str]:
    """Return only source assets that can become Elementor media.

    Standalone TEXT nodes are deliberately excluded. If text is contained inside
    a vector subtree that the compiler has already collapsed to one atomic icon,
    only that atomic icon's source id reaches this function, so the artwork stays
    intact without exporting the original text node as separate media.
    """
    keys: set[str] = set()

    def visit(node: DesignNode) -> None:
        if node.kind == "image" and node.image_ref:
            keys.add(node.image_ref.replace(":", "-"))
        elif node.kind == "icon" and node.source_id:
            keys.add(node.source_id.replace(":", "-"))

        for child in node.children:
            visit(child)

    visit(root)
    return keys


def _svg_to_webp(source: Path, target: Path, *, scale: float = 2.0) -> None:
    """Rasterize one SVG to transparent lossless WebP for Elementor."""
    png_bytes = resvg_py.svg_to_bytes(svg_path=str(source), zoom=scale)
    with Image.open(io.BytesIO(png_bytes)) as image:
        rgba = image.convert("RGBA")
        target.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(target, format="WEBP", lossless=True, method=6)


def prepare_elementor_assets(
    root: DesignNode,
    source_assets: list[Path],
    target_dir: Path,
    relative_root: Path,
) -> dict[str, str]:
    """Package only media actually referenced by Elementor.

    Raster formats pass through unchanged. SVG artwork is derived as transparent
    2x lossless WebP so Elementor never needs to upload SVG media. Standalone text
    exports and unrelated/orphaned Figma assets are omitted entirely.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    assets_by_key = {asset.stem: asset for asset in source_assets}
    semantic_names = semantic_asset_names(root, source_assets)
    result: dict[str, str] = {}

    for key in sorted(elementor_asset_keys(root)):
        source = assets_by_key.get(key)
        if source is None:
            continue

        semantic_name = semantic_names[key]
        if source.suffix.lower() == ".svg":
            target = target_dir / f"{Path(semantic_name).stem}.webp"
            _svg_to_webp(source, target)
        else:
            target = target_dir / semantic_name
            try:
                shutil.copy2(source, target)
            except OSError as exc:
                raise OSError(
                    f"Could not package Figma asset {source!s} -> {target!s}: {exc}"
                ) from exc

        result[key] = target.relative_to(relative_root).as_posix()

    return result
