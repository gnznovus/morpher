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
