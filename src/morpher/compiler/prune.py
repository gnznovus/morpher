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


def _is_redundant_composition(node: DesignNode, child: DesignNode) -> bool:
    """Return true when a generated composition row duplicates its parent.

    Horizontal-region inference originally introduced a composition wrapper so
    later ownership passes had a stable boundary. Once those passes finish, a
    parent containing only that wrapper represents the exact same composition
    and the extra Elementor container has no semantic value.
    """
    expected_id = f"{node.source_id or 'node'}::composition-row"
    return (
        child.kind == "container"
        and child.source_id == expected_id
        and child.style.layout_direction == "horizontal"
        and not _has_visual_ownership(child)
    )


def _flatten_redundant_composition(node: DesignNode) -> None:
    if len(node.children) != 1:
        return
    composition = node.children[0]
    if not _is_redundant_composition(node, composition):
        return

    # The parent is now the composition. Ownership-sensitive passes have
    # already run, so inferred regions can become direct children safely.
    node.style.layout_direction = composition.style.layout_direction
    node.style.gap = composition.style.gap
    node.style.primary_axis_align = composition.style.primary_axis_align
    node.style.counter_axis_align = composition.style.counter_axis_align
    node.children = composition.children


def prune_empty_generated_wrappers(root: DesignNode) -> DesignNode:
    """Remove empty or structurally redundant compiler-generated wrappers.

    Figma-owned empty containers are preserved. Only containers created by the
    responsive compiler are eligible, and wrappers carrying their own visual
    background are retained even when childless. A sole generated composition
    row is flattened after ownership rewrites because its parent can represent
    the same horizontal composition directly.
    """

    def visit(node: DesignNode) -> None:
        kept: list[DesignNode] = []
        for child in node.children:
            visit(child)
            if _is_generated_wrapper(child) and not child.children and not _has_visual_ownership(child):
                continue
            kept.append(child)
        node.children = kept
        _flatten_redundant_composition(node)

    visit(root)
    return root
