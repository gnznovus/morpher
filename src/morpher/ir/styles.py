from dataclasses import dataclass
from typing import Literal


LayoutDirection = Literal["horizontal", "vertical"]
SizingMode = Literal["fixed", "hug", "fill"]


@dataclass
class DesignStyle:
    """Output-agnostic style foundation for Design IR nodes."""

    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    rotation: float | None = None
    gap: float | None = None
    padding_top: float | None = None
    padding_right: float | None = None
    padding_bottom: float | None = None
    padding_left: float | None = None
    opacity: float | None = None
    background: str | None = None
    border_radius: float | None = None
    layout_direction: LayoutDirection | None = None
    width_mode: SizingMode | None = None
    height_mode: SizingMode | None = None
    constraint_horizontal: str | None = None
    constraint_vertical: str | None = None
    font_family: str | None = None
    font_style: str | None = None
    font_weight: int | None = None
    font_size: float | None = None
    letter_spacing: float | None = None
    line_height: float | None = None
    text_align_horizontal: str | None = None
    text_align_vertical: str | None = None
