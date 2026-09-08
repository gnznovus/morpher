from morpher.ir.nodes import DesignNode
from morpher.renderers.html import render_html


def test_text_uses_outline_asset_when_available() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        children=[DesignNode(kind="text", source_id="2:3", text="Butler text")],
    )

    html = render_html(root, asset_sources={"2-3": "assets/example/2-3.svg"})

    assert 'class="morpher-2-3 morpher-text-outline"' in html
    assert 'class="morpher-text-outline-asset"' in html
    assert 'src="assets/example/2-3.svg"' in html
    assert 'alt="Butler text"' in html
    assert 'data-morpher-source-id="2:3"' in html


def test_text_outline_keeps_positioned_class_on_wrapper_not_img() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        children=[DesignNode(kind="text", source_id="2:3", text="Layout text")],
    )

    html = render_html(root, asset_sources={"2-3": "assets/example/2-3.svg"})

    assert '<div class="morpher-2-3 morpher-text-outline"' in html
    assert '<img class="morpher-text-outline-asset"' in html
    assert '<img class="morpher-2-3' not in html


def test_text_falls_back_to_semantic_html_without_outline_asset() -> None:
    root = DesignNode(
        kind="container",
        source_id="1:1",
        children=[DesignNode(kind="text", source_id="2:3", text="Semantic text")],
    )

    html = render_html(root)

    assert '<div class="morpher-2-3">Semantic text</div>' in html
