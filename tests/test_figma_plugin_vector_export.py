from pathlib import Path


def test_figma_plugin_vector_export_preserves_absolute_bounds() -> None:
    plugin_code = (
        Path(__file__).resolve().parents[1] / "figma-plugin" / "code.js"
    ).read_text(encoding="utf-8")

    start = plugin_code.index("async function exportVectorAssets")
    end = plugin_code.index("async function exportTextAssets")
    vector_export = plugin_code[start:end]

    assert 'format: "SVG"' in vector_export
    assert "useAbsoluteBounds: true" in vector_export
