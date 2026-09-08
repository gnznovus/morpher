from typing import Any

from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignDocument


def normalize(source: dict[str, Any] | DesignDocument) -> DesignDocument:
    """Convert supported adapter data into the shared Design IR.

    Figma JSON is the first concrete source format. Already-normalized
    documents pass through unchanged so renderers only consume Design IR.
    """
    if isinstance(source, DesignDocument):
        return source
    if isinstance(source, dict):
        return FigmaJsonAdapter().from_data(source)
    raise TypeError(f"Unsupported source for normalization: {type(source).__name__}")
