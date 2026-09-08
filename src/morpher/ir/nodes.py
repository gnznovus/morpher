from dataclasses import dataclass, field
from typing import Literal

from .styles import DesignStyle


NodeKind = Literal["container", "text", "image", "button", "icon", "divider", "shape", "absolute", "unsupported"]


@dataclass
class DesignNode:
    kind: NodeKind
    name: str | None = None
    source_id: str | None = None
    source_type: str | None = None
    text: str | None = None
    image_ref: str | None = None
    style: DesignStyle = field(default_factory=DesignStyle)
    children: list["DesignNode"] = field(default_factory=list)


@dataclass
class DesignDocument:
    root: DesignNode
    warnings: list[str] = field(default_factory=list)
    schema_version: int | None = None
