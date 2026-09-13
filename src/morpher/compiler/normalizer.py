from typing import Any

from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignDocument
from morpher.ir.validation import validate_design_ir


def _require_valid(document: DesignDocument) -> DesignDocument:
    validation = validate_design_ir(document)
    if not validation.errors:
        return document

    details = "; ".join(
        f"{item.code} at {item.path_string}: {item.message}"
        for item in validation.errors
    )
    raise ValueError(f"Design IR validation failed: {details}")


def normalize(source: dict[str, Any] | DesignDocument) -> DesignDocument:
    """Convert supported adapter data into validated shared Design IR.

    Figma JSON is the first concrete source format. Already-normalized
    documents pass through the same invariant validation so compiler entry
    points receive a structurally safe Design IR tree.
    """
    if isinstance(source, DesignDocument):
        return _require_valid(source)
    if isinstance(source, dict):
        return _require_valid(FigmaJsonAdapter().from_data(source))
    raise TypeError(f"Unsupported source for normalization: {type(source).__name__}")
