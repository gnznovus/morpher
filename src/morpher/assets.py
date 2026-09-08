from __future__ import annotations

import re
from pathlib import Path

from morpher.ir.nodes import DesignNode


def _slug(value: str | None, fallback: str) -> str:
    text = (value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def semantic_asset_names(root: DesignNode, source_assets: list[Path]) -> dict[str, str]:
    """Map raw Figma asset keys to deterministic human-facing filenames.

    The root name provides semantic context while the original Figma node name
    is preserved for traceability. Raw hashes/source ids remain lookup keys only.
    """
    context = _slug(root.name, "design")
    assets_by_key = {asset.stem: asset for asset in source_assets if asset.is_file()}
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
                node_name = _slug(node.name, node.kind)
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
