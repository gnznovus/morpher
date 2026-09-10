from __future__ import annotations

from morpher.ir.nodes import DesignNode


_GENERATED_WRAPPER_MARKERS = (
    "::region-",
    "::row-",
    "::contact-",
    "::bottom-controls",
)


def _is_generated_wrapper(node: DesignNode) -> bool:
    source_id = node.source_id or ""
    return node.kind == "container" and any(marker in source_id for marker in _GENERATED_WRAPPER_MARKERS)


def _has_visual_ownership(node: DesignNode) -> bool:
    style = node.style
    return bool(
        style.background
        or getattr(style, "background_image_ref", None)
    )


def prune_empty_generated_wrappers(root: DesignNode) -> DesignNode:
    """Remove empty compiler-generated wrappers after ownership rewrites.

    Figma-owned empty containers are preserved. Only containers created by the
    responsive compiler are eligible, and wrappers carrying their own visual
    background are retained even when childless.
    """

    def visit(node: DesignNode) -> None:
        kept: list[DesignNode] = []
        for child in node.children:
            visit(child)
            if _is_generated_wrapper(child) and not child.children and not _has_visual_ownership(child):
                continue
            kept.append(child)
        node.children = kept

    visit(root)
    return root
