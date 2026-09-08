from dataclasses import dataclass, field
from typing import Literal


NodeKind = Literal["container", "text", "image", "button", "icon", "divider", "absolute"]


@dataclass
class DesignNode:
    kind: NodeKind
    name: str | None = None
    source_id: str | None = None
    children: list["DesignNode"] = field(default_factory=list)
