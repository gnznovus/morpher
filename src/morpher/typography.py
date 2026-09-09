from dataclasses import dataclass


DEFAULT_ROOT_FONT_SIZE = 16.0
DEFAULT_MOBILE_VIEWPORT = 375.0
MIN_READABLE_FONT_SIZE = 16.0
MIN_SCALE_RATIO = 0.5


@dataclass(frozen=True)
class FluidTypeScale:
    minimum_rem: float
    intercept_rem: float
    slope_vw: float
    maximum_rem: float

    def css(self) -> str:
        return (
            f"clamp({_number(self.minimum_rem)}rem, "
            f"calc({_number(self.intercept_rem)}rem + {_number(self.slope_vw)}vw), "
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
    """Derive a fluid type scale from Figma's desktop measurement.

    The desktop Figma font size and viewport are inputs, not hard-coded design
    assumptions. Morpher supplies only a generic mobile anchor and readability
    policy. The fixed terms are emitted in rem while the interpolation remains
    viewport-relative through vw.
    """
    if desktop_font_size <= 0 or desktop_viewport <= mobile_viewport or root_font_size <= 0:
        return None

    mobile_font_size = minimum_font_size(desktop_font_size)
    if mobile_font_size == desktop_font_size:
        return FluidTypeScale(
            minimum_rem=desktop_font_size / root_font_size,
            intercept_rem=desktop_font_size / root_font_size,
            slope_vw=0.0,
            maximum_rem=desktop_font_size / root_font_size,
        )

    slope_px_per_viewport_px = (desktop_font_size - mobile_font_size) / (desktop_viewport - mobile_viewport)
    intercept_px = mobile_font_size - slope_px_per_viewport_px * mobile_viewport

    return FluidTypeScale(
        minimum_rem=mobile_font_size / root_font_size,
        intercept_rem=intercept_px / root_font_size,
        slope_vw=slope_px_per_viewport_px * 100,
        maximum_rem=desktop_font_size / root_font_size,
    )
