import math

from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.css import render_css


def test_icon_fill_is_not_rendered_as_css_background() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=200, height=100, x=0, y=0),
        children=[
            DesignNode(
                kind="icon",
                source_id="2:3",
                style=DesignStyle(
                    width=156.86,
                    height=18.44,
                    x=10,
                    y=20,
                    background="rgba(255, 255, 255, 1)",
                ),
            )
        ],
    )

    css = render_css(root)

    icon_block = css.split(".morpher-2-3 {", 1)[1].split("}", 1)[0]
    assert "background:" not in icon_block
    assert "width: 156.86px" in icon_block
    assert "height: 18.44px" in icon_block
    assert "object-fit: contain" in icon_block


def test_shape_fill_still_renders_as_css_background() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        children=[
            DesignNode(
                kind="shape",
                source_id="2:4",
                style=DesignStyle(background="rgba(255, 0, 0, 1)"),
            )
        ],
    )

    css = render_css(root)

    shape_block = css.split(".morpher-2-4 {", 1)[1].split("}", 1)[0]
    assert "background: rgba(255, 0, 0, 1)" in shape_block


def test_outlined_rotated_text_keeps_final_figma_bounds_without_second_rotation() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=1920, height=960, x=0, y=0),
        children=[
            DesignNode(
                kind="text",
                source_id="45:5317",
                text="LOREM IPSUM DO",
                style=DesignStyle(
                    width=24,
                    height=192,
                    x=25,
                    y=366,
                    rotation=-math.pi / 2,
                ),
            )
        ],
    )

    css = render_css(
        root,
        asset_sources={"45-5317": "assets/Homepage-Hide/45-5317.svg"},
    )

    text_block = css.split(".morpher-45-5317 {", 1)[1].split("}", 1)[0]
    assert "left: 25px" in text_block
    assert "top: 366px" in text_block
    assert "width: 24px" in text_block
    assert "height: 192px" in text_block
    assert "transform: rotate" not in text_block


def test_semantic_rotated_text_still_reconstructs_pre_rotation_box() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=1920, height=960, x=0, y=0),
        children=[
            DesignNode(
                kind="text",
                source_id="45:5317",
                text="LOREM IPSUM DO",
                style=DesignStyle(
                    width=24,
                    height=192,
                    x=25,
                    y=366,
                    rotation=-math.pi / 2,
                ),
            )
        ],
    )

    css = render_css(root)

    text_block = css.split(".morpher-45-5317 {", 1)[1].split("}", 1)[0]
    assert "width: 192px" in text_block
    assert "height: 24px" in text_block
    assert "transform: rotate(-90deg)" in text_block
