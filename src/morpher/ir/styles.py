from dataclasses import dataclass


@dataclass
class DesignStyle:
    """Output-agnostic style foundation for Design IR nodes."""

    width: float | None = None
    height: float | None = None
    gap: float | None = None
    padding_top: float | None = None
    padding_right: float | None = None
    padding_bottom: float | None = None
    padding_left: float | None = None
    opacity: float | None = None
    background: str | None = None
    border_radius: float | None = None
