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
    """Return Morpher's generic mobile floor for a desktop Figma font size."""
    return min(desktop_font_size, max(MIN_READABLE_FONT_SIZE, desktop_font_size * MIN_SCALE_RATIO))


def fluid_font_size(
    desktop_font_size: float,
    desktop_viewport: float,
    *,
    mobile_viewport: float = DEFAULT_MOBILE_VIEWPORT,
    root_font_size: float = DEFAULT_ROOT_FONT_SIZE,
) -> FluidTypeScale | None:
    """Derive a composition-relative type scale from Figma measurements.

    Font size follows the source design proportion directly through vw. The
    clamp only guards the lower and upper bounds; it does not alter the
    responsive curve with an interpolation intercept.
    """
    if desktop_font_size <= 0 or desktop_viewport <= mobile_viewport or root_font_size <= 0:
        return None

    mobile_font_size = minimum_font_size(desktop_font_size)
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
