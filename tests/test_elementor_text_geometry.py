from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_elementor_preserves_authored_text_line_breaks():
    root = DesignNode(
        kind="container",
        children=[
            DesignNode(
                kind="text",
                text="– LOREM IPSUM DOLOR\nSIT AMET, CONSECTETUR\nPELLE\nNTESQUE",
            )
        ],
    )

    result = render_elementor(root)
    title = result["content"][0]["elements"][0]["settings"]["title"]

    assert title == "– LOREM IPSUM DOLOR<br>SIT AMET, CONSECTETUR<br>PELLE<br>NTESQUE"


def test_discovery_semantic_geometry_matches_source_bounds():
    root = DesignNode(
        kind="container",
        name="Discovery",
        source_id="45:5267",
        style=DesignStyle(x=0, y=960, width=1920, height=960),
        children=[
            DesignNode(kind="text", source_id="45:5268", text="Discovery.", style=DesignStyle(x=179, y=1059, width=160, height=36)),
            DesignNode(
                kind="container",
                name="Frame",
                source_id="45:5269",
                style=DesignStyle(x=367, y=1411, width=1326.79, height=1519.57),
                children=[
                    DesignNode(kind="icon", source_id="45:5270", style=DesignStyle(x=442, y=1285, width=1233, height=1412)),
                    DesignNode(kind="text", source_id="45:5271", text="Body copy", style=DesignStyle(x=496, y=1818, width=1013, height=86)),
                ],
            ),
            DesignNode(kind="image", source_id="45:5272", style=DesignStyle(x=0, y=1111, width=1198, height=673)),
            DesignNode(kind="icon", source_id="45:5273", style=DesignStyle(x=510, y=1366, width=144, height=144)),
            DesignNode(kind="text", source_id="45:5276", text="Statement", style=DesignStyle(x=972, y=1375, width=732, height=360)),
            DesignNode(kind="icon", source_id="45:5277", style=DesignStyle(x=972, y=1172, width=589.82, height=141.57)),
        ],
    )

    compiled = compile_responsive_layout(root)
    _, hero, muu, statement, body, _ = compiled.children

    assert round(hero.style.width_percent or 0, 3) == 62.396
    assert round(hero.style.margin_top_percent or 0, 3) == 0.833

    assert round(muu.style.width_percent or 0, 3) == 30.720
    assert round(muu.style.margin_left_percent or 0, 3) == 50.625
    assert round(muu.style.margin_top_percent or 0, 3) == -31.875

    assert round(statement.style.width_percent or 0, 3) == 38.125
    assert round(statement.style.margin_left_percent or 0, 3) == 50.625
    assert round(statement.style.margin_top_percent or 0, 3) == 3.199

    assert round(body.style.width_percent or 0, 3) == 52.760
    assert round(body.style.margin_left_percent or 0, 3) == 25.833
    assert round(body.style.margin_top_percent or 0, 3) == 4.323
