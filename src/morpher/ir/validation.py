from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from .nodes import DesignDocument, DesignNode


DiagnosticSeverity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class IRDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    path: tuple[int, ...]
    node_name: str | None
    source_id: str | None
    source_type: str | None

    @property
    def path_string(self) -> str:
        return "root" if not self.path else "root/" + "/".join(str(index) for index in self.path)


@dataclass(frozen=True)
class ValidationResult:
    diagnostics: tuple[IRDiagnostic, ...]

    @property
    def errors(self) -> tuple[IRDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "error")

    @property
    def warnings(self) -> tuple[IRDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "warning")

    @property
    def info(self) -> tuple[IRDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "info")

    @property
    def valid(self) -> bool:
        return not self.errors


class IRValidationError(ValueError):
    """Raised when Design IR contains compiler-blocking validation errors."""

    def __init__(self, validation: ValidationResult) -> None:
        self.validation = validation
        details = "; ".join(
            f"{item.code} at {item.path_string}: {item.message}"
            for item in validation.errors
        )
        super().__init__(f"Design IR validation failed: {details}")


_NON_NEGATIVE_STYLE_FIELDS = (
    "width",
    "height",
    "design_viewport_width",
    "width_percent",
    "gap",
    "padding_top",
    "padding_right",
    "padding_bottom",
    "padding_left",
    "stroke_weight",
    "border_top_width",
    "border_right_width",
    "border_bottom_width",
    "border_left_width",
    "border_radius",
    "layout_grow",
    "font_size",
    "line_height",
    "paragraph_spacing",
)

_FINITE_STYLE_FIELDS = (
    *_NON_NEGATIVE_STYLE_FIELDS,
    "x",
    "y",
    "offset_x",
    "offset_y",
    "rotation",
    "margin_top_percent",
    "margin_right_percent",
    "margin_bottom_percent",
    "margin_left_percent",
    "opacity",
    "image_opacity",
    "background_image_opacity",
    "letter_spacing",
)

_OPACITY_FIELDS = (
    "opacity",
    "image_opacity",
    "background_image_opacity",
)


def _diagnostic(
    node: DesignNode,
    path: tuple[int, ...],
    severity: DiagnosticSeverity,
    code: str,
    message: str,
) -> IRDiagnostic:
    return IRDiagnostic(
        severity=severity,
        code=code,
        message=message,
        path=path,
        node_name=node.name,
        source_id=node.source_id,
        source_type=node.source_type,
    )


def validate_design_ir(document: DesignDocument | DesignNode) -> ValidationResult:
    """Validate renderer-independent invariants relied on by Morpher's compiler.

    The validator intentionally checks only shared IR contracts. Target-specific
    assumptions belong in their compiler/renderer layers instead of here.
    """

    root = document.root if isinstance(document, DesignDocument) else document
    diagnostics: list[IRDiagnostic] = []
    active_nodes: set[int] = set()
    seen_source_ids: dict[str, tuple[int, ...]] = {}

    def visit(node: DesignNode, path: tuple[int, ...]) -> None:
        identity = id(node)
        if identity in active_nodes:
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "error",
                    "ir.cycle",
                    "Design IR must be a tree; this node is already an active ancestor.",
                )
            )
            return

        active_nodes.add(identity)

        if node.source_id:
            first_path = seen_source_ids.get(node.source_id)
            if first_path is None:
                seen_source_ids[node.source_id] = path
            elif first_path != path:
                first_path_string = "root" if not first_path else "root/" + "/".join(str(index) for index in first_path)
                diagnostics.append(
                    _diagnostic(
                        node,
                        path,
                        "warning",
                        "ir.duplicate_source_id",
                        f"Source id {node.source_id!r} already appears at {first_path_string}.",
                    )
                )

        for field_name in _FINITE_STYLE_FIELDS:
            value = getattr(node.style, field_name)
            if value is not None and not math.isfinite(value):
                diagnostics.append(
                    _diagnostic(
                        node,
                        path,
                        "error",
                        "ir.non_finite_number",
                        f"Style field {field_name!r} must be finite; got {value!r}.",
                    )
                )

        for field_name in _NON_NEGATIVE_STYLE_FIELDS:
            value = getattr(node.style, field_name)
            if value is not None and value < 0:
                diagnostics.append(
                    _diagnostic(
                        node,
                        path,
                        "error",
                        "ir.negative_size",
                        f"Style field {field_name!r} cannot be negative; got {value!r}.",
                    )
                )

        for field_name in _OPACITY_FIELDS:
            value = getattr(node.style, field_name)
            if value is not None and not 0 <= value <= 1:
                diagnostics.append(
                    _diagnostic(
                        node,
                        path,
                        "error",
                        "ir.opacity_range",
                        f"Style field {field_name!r} must be between 0 and 1; got {value!r}.",
                    )
                )

        if node.style.width_mode == "fixed" and node.style.width is None:
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "warning",
                    "ir.fixed_width_without_width",
                    "Fixed width mode has no authored width.",
                )
            )

        if node.style.height_mode == "fixed" and node.style.height is None:
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "warning",
                    "ir.fixed_height_without_height",
                    "Fixed height mode has no authored height.",
                )
            )

        if node.kind == "text" and node.text is None:
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "warning",
                    "ir.text_without_content",
                    "Text node has no text content.",
                )
            )

        if node.kind == "image" and not node.image_ref and not node.style.background_image_ref:
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "warning",
                    "ir.image_without_asset",
                    "Image node has no image reference.",
                )
            )

        if node.kind == "unsupported":
            diagnostics.append(
                _diagnostic(
                    node,
                    path,
                    "warning",
                    "ir.unsupported_node",
                    "Unsupported source content remains in Design IR.",
                )
            )

        for index, child in enumerate(node.children):
            if not isinstance(child, DesignNode):
                diagnostics.append(
                    _diagnostic(
                        node,
                        path + (index,),
                        "error",
                        "ir.invalid_child",
                        f"Child {index} is not a DesignNode.",
                    )
                )
                continue
            visit(child, path + (index,))

        active_nodes.remove(identity)

    visit(root, ())
    return ValidationResult(tuple(diagnostics))
