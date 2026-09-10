from dataclasses import dataclass
from typing import Literal


LayoutDirection = Literal["horizontal", "vertical"]
SizingMode = Literal["fixed", "hug", "fill"]
PositionMode = Literal["absolute"]


@dataclass
class DesignStyle:
    """Output-agnostic style foundation for Design IR nodes."""

    width: float | None = None
    design_viewport_width: float | None = None
    width_percent: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    position_mode: PositionMode | None = None
    offset_x: float | None = None
    offset_y: float | None = None
    rotation: float | None = None
    gap: float | None = None
    padding_top: float | None = None
    padding_right: float | None = None
    padding_bottom: float | None = None
    padding_left: float | None = None
    margin_top_percent: float | None = None
    margin_right_percent: float | None = None
    margin_bottom_percent: float | None = None
    margin_left_percent: float | None = None
    opacity: float | None = None
    image_opacity: float | None = None
    background_image_ref: str | None = None
    background_image_opacity: float | None = None
    clips_content: bool | None = None
    background: str | None = None
    text_color: str | None = None
    stroke_color: str | None = None
    stroke_weight: float | None = None
    border_radius: float | None = None
    layout_direction: LayoutDirection | None = None
    width_mode: SizingMode | None = None
    height_mode: SizingMode | None = None
    primary_axis_align: str | None = None
    counter_axis_align: str | None = None
    layout_align: str | None = None
    layout_grow: float | None = None
    constraint_horizontal: str | None = None
    constraint_vertical: str | None = None
    font_family: str | None = None
    font_postscript_name: str | None = None
    font_style: str | None = None
    font_weight: int | None = None
    font_size: float | None = None
    letter_spacing: float | None = None
    line_height: float | None = None
    text_auto_resize: str | None = None
    text_align_horizontal: str | None = None
    text_align_vertical: str | None = None
