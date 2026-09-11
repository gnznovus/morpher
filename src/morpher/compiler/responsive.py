from __future__ import annotations

from morpher.compiler.contact import resolve_contact_group_ownership
from morpher.compiler.flow_groups import stabilize_compiled_flow_groups
from morpher.compiler.layout import compile_responsive_layout
from morpher.compiler.overlays import (
    resolve_compiled_spatial_relationships,
    resolve_inferred_region_overlays,
)
from morpher.compiler.prune import prune_empty_generated_wrappers
from morpher.ir.nodes import DesignNode


def compile_for_responsive_render(root: DesignNode) -> DesignNode:
    """Compile source Design IR into target-neutral responsive Design IR.

    The layout compiler deep-copies ``root`` before applying inference. Calling
    this function separately for each renderer therefore gives Native and
    Elementor independent compiled trees and keeps Fidelity on untouched source
    geometry.
    """
    design_viewport = root.style.width
    compiled = compile_responsive_layout(root)
    compiled = resolve_compiled_spatial_relationships(
        compiled,
        root,
        design_viewport,
    )
    compiled = stabilize_compiled_flow_groups(
        compiled,
        root,
        design_viewport,
    )
    compiled = resolve_contact_group_ownership(
        compiled,
        root,
        design_viewport,
    )
    compiled = resolve_inferred_region_overlays(compiled, design_viewport)
    compiled = prune_empty_generated_wrappers(compiled)
    compiled.style.width = design_viewport
    compiled.style.design_viewport_width = design_viewport
    return compiled
