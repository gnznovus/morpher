from morpher.compiler.responsive import compile_for_responsive_render
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.css import render_css


def _free_layout_root() -> DesignNode:
    return DesignNode(
        kind="container",
        name="Body",
        source_id="1:1",
        style=DesignStyle(width=1200, height=600, x=0, y=0),
        children=[
            DesignNode(
                kind="text",
                name="Title",
                source_id="1:2",
                text="Title",
                style=DesignStyle(width=300, height=40, x=100, y=80),
            ),
            DesignNode(
                kind="text",
                name="Copy",
                source_id="1:3",
                text="Copy",
                style=DesignStyle(width=500, height=80, x=100, y=160),
            ),
        ],
    )


def test_responsive_pipeline_preserves_source_and_returns_independent_trees() -> None:
    source = _free_layout_root()

    native_root = compile_for_responsive_render(source)
    elementor_root = compile_for_responsive_render(source)

    assert source.style.layout_direction is None
    assert source.children[0].style.width_percent is None

    assert native_root is not source
    assert elementor_root is not source
    assert native_root is not elementor_root
    assert native_root.style.design_viewport_width == 1200
    assert elementor_root.style.design_viewport_width == 1200

    native_root.children[0].style.margin_left_percent = 99
    assert elementor_root.children[0].style.margin_left_percent != 99
    assert source.children[0].style.margin_left_percent is None


def test_responsive_css_uses_compiled_percent_geometry_without_changing_fidelity_mode() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=1200, height=600, x=0, y=0, layout_direction="vertical"),
        children=[
            DesignNode(
                kind="text",
                source_id="1:2",
                text="Title",
                style=DesignStyle(
                    width=300,
                    height=40,
                    x=100,
                    y=80,
                    width_percent=25,
                    margin_left_percent=8.333333,
                ),
            )
        ],
    )

    responsive_css = render_css(root, responsive=True)
    fidelity_css = render_css(root)

    root_block = responsive_css.split(".morpher-1-1 {", 1)[1].split("}", 1)[0]
    text_block = responsive_css.split(".morpher-1-2 {", 1)[1].split("}", 1)[0]

    assert "width: 100%" in root_block
    assert "width: 25vw" in text_block
    assert "margin: 0% 0% 0% 8.33333%" in text_block
    assert "width: 1200px" in fidelity_css
    assert "width: 25vw" not in fidelity_css


def test_responsive_css_keeps_explicit_absolute_layer_owned_by_flow_container() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        style=DesignStyle(width=1200, x=0, y=0, layout_direction="vertical"),
        children=[
            DesignNode(
                kind="container",
                source_id="1:2",
                style=DesignStyle(width_mode="fill", layout_direction="vertical"),
                children=[
                    DesignNode(
                        kind="icon",
                        source_id="1:3",
                        style=DesignStyle(
                            position_mode="absolute",
                            offset_x=24,
                            offset_y=32,
                            width=48,
                            height=48,
                        ),
                    )
                ],
            )
        ],
    )

    css = render_css(root, responsive=True)
    owner_block = css.split(".morpher-1-2 {", 1)[1].split("}", 1)[0]
    layer_block = css.split(".morpher-1-3 {", 1)[1].split("}", 1)[0]

    assert "display: flex" in owner_block
    assert "position: absolute" in layer_block
    assert "left: 24px" in layer_block
    assert "top: 32px" in layer_block
