from morpher.compiler.layout import compile_responsive_layout
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.renderers.elementor import render_elementor


def test_compiles_free_layout_into_vertical_bands_and_horizontal_row():
    root = DesignNode(
        kind="container",
        name="Discovery",
        source_id="10:1",
        style=DesignStyle(x=100, y=200, width=1200, height=700),
        children=[
            DesignNode(kind="text", name="Section label", source_id="10:2", text="Discovery.", style=DesignStyle(x=140, y=240, width=180, height=40)),
            DesignNode(kind="text", name="Statement", source_id="10:3", text="– LOREM IPSUM DOLOR SIT AMET", style=DesignStyle(x=140, y=360, width=560, height=260)),
            DesignNode(kind="container", name="Body copy", source_id="10:4", style=DesignStyle(x=760, y=380, width=420, height=180), children=[DesignNode(kind="text", source_id="10:5", text="Muu is a new, unpretentious yet luxurious hotel brand.", style=DesignStyle(x=760, y=380, width=420, height=180))]),
        ],
    )
    compiled = compile_responsive_layout(root)
    assert compiled.style.layout_direction == "vertical"
    assert compiled.style.width_mode == "fill"
    assert compiled.style.x is None
    assert compiled.style.y is None
    assert len(compiled.children) == 2
    label = compiled.children[0]
    row = compiled.children[1]
    assert label.text == "Discovery."
    assert row.kind == "container"
    assert row.style.layout_direction == "horizontal"
    assert row.style.width_mode == "fill"
    assert len(row.children) == 2
    statement, body = row.children
    assert round(statement.style.width_percent or 0, 3) == 46.667
    assert round(body.style.width_percent or 0, 3) == 35.0
    assert statement.style.x is None
    assert body.style.x is None
    elementor = render_elementor(compiled)
    section = elementor["content"][0]
    row_json = section["elements"][1]
    assert section["settings"]["flex_direction"] == "column"
    assert row_json["settings"]["flex_direction"] == "row"
    assert "position" not in row_json["settings"]
    statement_settings = row_json["elements"][0]["settings"]
    body_settings = row_json["elements"][1]["settings"]
    assert "_position" not in statement_settings
    assert "position" not in body_settings
    assert statement_settings["_element_custom_width"]["unit"] == "vw"
    assert body_settings["width"]["unit"] == "vw"


def test_discovery_visuals_join_flow_without_forcing_text_absolute():
    root = DesignNode(
        kind="container", name="Discovery", source_id="45:5267", style=DesignStyle(x=0, y=960, width=1920, height=960),
        children=[
            DesignNode(kind="text", source_id="45:5268", text="Discovery.", style=DesignStyle(x=179, y=1059, width=160, height=36)),
            DesignNode(kind="container", name="Frame", source_id="45:5269", style=DesignStyle(x=367, y=1411, width=1326.79, height=1519.57), children=[
                DesignNode(kind="icon", source_id="45:5270", style=DesignStyle(x=442, y=1285, width=1233, height=1412)),
                DesignNode(kind="text", source_id="45:5271", text="Muu is a new, unpretentious yet luxurious hotel brand.", style=DesignStyle(x=496, y=1818, width=1013, height=86)),
            ]),
            DesignNode(kind="image", source_id="45:5272", style=DesignStyle(x=0, y=1111, width=1198, height=673)),
            DesignNode(kind="icon", source_id="45:5273", style=DesignStyle(x=510, y=1366, width=144, height=144)),
            DesignNode(kind="text", source_id="45:5276", text="– LOREM IPSUM DOLOR SIT AMET", style=DesignStyle(x=972, y=1375, width=732, height=360)),
            DesignNode(kind="icon", source_id="45:5277", style=DesignStyle(x=972, y=1172, width=589.82, height=141.57)),
        ],
    )
    compiled = compile_responsive_layout(root)
    elementor = render_elementor(
        compiled,
        asset_sources={
            "45-5270": "assets/Discovery/discovery-background.svg",
            "45-5272": "assets/Discovery/discovery-rectangle-1.jpg",
            "45-5273": "assets/Discovery/discovery-play.svg",
            "45-5277": "assets/Discovery/discovery-muu.svg",
        },
    )
    section = elementor["content"][0]
    assert compiled.style.layout_direction == "vertical"
    assert section["settings"]["flex_direction"] == "column"
    assert section["settings"]["padding"]["top"] == "99"

    assert len(compiled.children) == 6
    label, hero, muu, statement, body, play = compiled.children
    assert label.kind == "text"
    assert hero.source_id == "45:5272"
    assert muu.source_id == "45:5277"
    assert statement.source_id == "45:5276"
    assert body.source_id == "45:5269"
    assert play.source_id == "45:5273"

    assert round(label.style.width_percent or 0, 3) == 8.333
    assert round(label.style.margin_left_percent or 0, 3) == 9.323
    assert round(hero.style.width_percent or 0, 3) == 62.396
    assert round(hero.style.margin_left_percent or 0, 3) == 0
    assert round(hero.style.margin_top_percent or 0, 3) == 0.833
    assert round(muu.style.width_percent or 0, 3) == 30.720
    assert round(muu.style.margin_left_percent or 0, 3) == 50.625
    assert round(muu.style.margin_top_percent or 0, 3) == -31.875

    assert play.style.position_mode == "absolute"
    assert play.style.offset_x == 510
    assert play.style.offset_y == 406

    backdrop = body.children[0]
    body_copy = body.children[1]
    assert backdrop.source_id == "45:5270"
    assert backdrop.style.position_mode == "absolute"
    assert backdrop.style.offset_x == -54
    assert backdrop.style.offset_y == -533
    assert body_copy.source_id == "45:5271"

    rendered_headings = []
    stack = list(section["elements"])
    while stack:
        element = stack.pop()
        stack.extend(element.get("elements", []))
        if element.get("widgetType") == "heading":
            rendered_headings.append(element)
    assert len(rendered_headings) == 3
    for heading in rendered_headings:
        assert "_position" not in heading["settings"]

    play_json = section["elements"][5]
    assert play_json["widgetType"] == "image"
    assert play_json["settings"]["_position"] == "absolute"
    assert play_json["settings"]["_offset_x"]["size"] == 510
    assert play_json["settings"]["_offset_y"]["size"] == 406

    body_json = section["elements"][4]
    backdrop_json = body_json["elements"][0]
    assert backdrop_json["widgetType"] == "image"
    assert backdrop_json["settings"]["_position"] == "absolute"
    assert backdrop_json["settings"]["_offset_x"]["size"] == -54
    assert backdrop_json["settings"]["_offset_y"]["size"] == -533


def test_nested_wrapper_is_compiled_before_parent_flow_erases_geometry():
    inner = DesignNode(
        kind="container",
        name="Destination",
        source_id="45:5282",
        style=DesignStyle(x=0, y=1920, width=1920, height=960),
        children=[
            DesignNode(kind="text", source_id="45:5284", text="Destination.", style=DesignStyle(x=179, y=2091, width=184, height=36)),
            DesignNode(kind="text", source_id="45:5285", text="Heading", style=DesignStyle(x=179, y=2148, width=716, height=120)),
            DesignNode(kind="text", source_id="45:5286", text="Intro", style=DesignStyle(x=179, y=2289, width=701, height=86)),
            DesignNode(kind="text", source_id="45:5287", text="Body", style=DesignStyle(x=179, y=2413, width=768, height=246)),
            DesignNode(kind="icon", source_id="45:5288", style=DesignStyle(x=179, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="icon", source_id="45:5289", style=DesignStyle(x=726, y=2800, width=156.86, height=18.44)),
            DesignNode(kind="text", source_id="45:5290", text="01 / 02", style=DesignStyle(x=492, y=2791, width=79, height=36)),
            DesignNode(kind="image", source_id="45:5291", style=DesignStyle(x=1129, y=2014, width=486, height=865)),
            DesignNode(kind="image", source_id="45:5292", style=DesignStyle(x=1618, y=2014, width=486, height=865)),
            DesignNode(kind="icon", source_id="45:5293", style=DesignStyle(x=1789, y=2375, width=144, height=144)),
        ],
    )
    root = DesignNode(
        kind="container",
        name="Destination root",
        source_id="45:5281",
        style=DesignStyle(x=0, y=1920, width=1920, height=960),
        children=[inner],
    )

    compiled = compile_responsive_layout(root)
    assert compiled.style.layout_direction == "vertical"
    assert len(compiled.children) == 1

    compiled_inner = compiled.children[0]
    assert compiled_inner.style.layout_direction == "vertical"
    assert len(compiled_inner.children) >= 1
    composition = compiled_inner.children[0]
    assert composition.kind == "container"
    assert composition.style.layout_direction == "horizontal"
    assert len(composition.children) == 2
    assert composition.children[0].style.layout_direction == "vertical"
    assert composition.children[1].style.layout_direction == "vertical"


def test_keeps_strongly_layered_free_layout_for_specialized_positioning():
    root = DesignNode(kind="container", source_id="20:1", style=DesignStyle(x=0, y=0, width=800, height=600), children=[
        DesignNode(kind="shape", source_id="20:2", style=DesignStyle(x=0, y=0, width=800, height=600)),
        DesignNode(kind="text", source_id="20:3", text="Overlay", style=DesignStyle(x=100, y=100, width=300, height=80)),
    ])
    compiled = compile_responsive_layout(root)
    assert compiled.style.layout_direction is None
    elementor = render_elementor(compiled)
    overlay = elementor["content"][0]["elements"][1]
    assert overlay["settings"]["_position"] == "absolute"


def test_auto_layout_passes_through_without_recompiling():
    root = DesignNode(kind="container", source_id="30:1", style=DesignStyle(layout_direction="horizontal", width_mode="fill", gap=24), children=[
        DesignNode(kind="text", source_id="30:2", text="One"),
        DesignNode(kind="text", source_id="30:3", text="Two"),
    ])
    compiled = compile_responsive_layout(root)
    assert compiled.style.layout_direction == "horizontal"
    assert compiled.style.gap == 24
    assert compiled.children[0].text == "One"
    assert compiled.children[1].text == "Two"
