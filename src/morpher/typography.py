from dataclasses import dataclass


DEFAULT_ROOT_FONT_SIZE = 16.0
DEFAULT_MOBILE_VIEWPORT = 375.0
MIN_READABLE_FONT_SIZE = 16.0
MIN_SCALE_RATIO = 0.5


@dataclass(frozen=True)
class FluidTypeScale:
    minimum_rem: float
    preferred_vw: float
    maximum_rem: float

    def css(self) -> str:
        return (
            f"clamp({_number(self.minimum_rem)}rem, "
            f"{_number(self.preferred_vw)}vw, "
            f"{_number(self.maximum_rem)}rem)"
        )


def _number(value: float) -> str:
    rounded = round(value, 4)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.4f}".rstrip("0").rstrip(".")


def minimum_font_size(desktop_font_size: float) -> float:
    """Return Morpher's generic mobile floor for readable flow typography."""
    return min(desktop_font_size, max(MIN_READABLE_FONT_SIZE, desktop_font_size * MIN_SCALE_RATIO))


def fluid_font_size(
    desktop_font_size: float,
    desktop_viewport: float,
    *,
    mobile_viewport: float = DEFAULT_MOBILE_VIEWPORT,
    root_font_size: float = DEFAULT_ROOT_FONT_SIZE,
    minimum_px: float | None = None,
) -> FluidTypeScale | None:
    """Derive a viewport-relative type scale from Figma measurements.

    By default Morpher keeps the readable mobile floor used by flow typography.
    Callers that must preserve a scaled spatial composition can pass
    ``minimum_px=0`` so the type continues shrinking with the composition while
    still capping at the authored desktop size.
    """
    if desktop_font_size <= 0 or desktop_viewport <= mobile_viewport or root_font_size <= 0:
        return None

    mobile_font_size = (
        minimum_font_size(desktop_font_size)
        if minimum_px is None
        else min(desktop_font_size, max(0.0, minimum_px))
    )
    if mobile_font_size == desktop_font_size:
        return None

    return FluidTypeScale(
        minimum_rem=mobile_font_size / root_font_size,
        preferred_vw=(desktop_font_size / desktop_viewport) * 100,
        maximum_rem=desktop_font_size / root_font_size,
    )


def relative_typography_value(value: float, font_size: float) -> float | None:
    """Convert a resolved Figma typography measurement to an em ratio."""
    if font_size <= 0:
        return None
    return value / font_size
