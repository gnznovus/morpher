import pytest

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor
from morpher.typography import fluid_font_size, minimum_font_size


def test_mobile_floor_is_dynamic_from_figma_font_size():
    assert minimum_font_size(50) == 25
    assert minimum_font_size(64) == 32
    assert minimum_font_size(18) == 16
    assert minimum_font_size(14) == 14


def test_magic_clamp_is_derived_from_figma_viewport_and_font_size():
    scale = fluid_font_size(50, 1920)
    assert scale is not None
    assert scale.minimum_rem == pytest.approx(1.5625)
    assert scale.maximum_rem == pytest.approx(3.125)
    assert scale.intercept_rem == pytest.approx(1.183252, abs=1e-6)
    assert scale.slope_vw == pytest.approx(1.618123, abs=1e-6)
    assert scale.css() == "clamp(1.5625rem, calc(1.1833rem + 1.6181vw), 3.125rem)"


def test_magic_clamp_changes_when_design_viewport_changes():
    wide = fluid_font_size(64, 1920)
    compact = fluid_font_size(64, 1440)
    assert wide is not None and compact is not None
    assert wide.css() != compact.css()
    assert wide.maximum_rem == compact.maximum_rem == 4


def test_elementor_uses_custom_unit_for_dynamic_font_size():
    root = DesignNode(
        kind="container",
        name="Fluid Type",
        source_id="fluid:root",
        style=DesignStyle(width=1920, layout_direction="vertical", width_mode="fill"),
        children=[
            DesignNode(
                kind="text",
                source_id="fluid:heading",
                text="MAGIC CLAMP",
                style=DesignStyle(font_size=50),
            )
        ],
    )
    heading = render_elementor(root)["content"][0]["elements"][0]
    assert heading["settings"]["typography_font_size"] == {
        "unit": "custom",
        "size": "clamp(1.5625rem, calc(1.1833rem + 1.6181vw), 3.125rem)",
        "sizes": [],
    }


def test_renderer_falls_back_to_px_without_design_viewport():
    root = DesignNode(
        kind="container",
        source_id="fallback:root",
        children=[DesignNode(kind="text", source_id="fallback:text", text="Fallback", style=DesignStyle(font_size=18))],
    )
    heading = render_elementor(root)["content"][0]["elements"][0]
    assert heading["settings"]["typography_font_size"] == {"unit": "px", "size": 18, "sizes": []}
