from pathlib import Path


def _plugin_code() -> str:
    return (
        Path(__file__).resolve().parents[1] / "figma-plugin" / "code.js"
    ).read_text(encoding="utf-8")


def _plugin_ui() -> str:
    return (
        Path(__file__).resolve().parents[1] / "figma-plugin" / "ui.html"
    ).read_text(encoding="utf-8")


def test_figma_plugin_vector_export_preserves_absolute_bounds() -> None:
    plugin_code = _plugin_code()

    start = plugin_code.index("async function exportVectorAssets")
    end = plugin_code.index("async function exportTextAssets")
    vector_export = plugin_code[start:end]

    assert 'format: "SVG"' in vector_export
    assert "useAbsoluteBounds: true" in vector_export


def test_figma_plugin_warns_on_similar_overlapping_visible_structures() -> None:
    plugin_code = _plugin_code()

    assert "function findOverlappingStructureWarnings" in plugin_code
    assert "function regionFingerprint" in plugin_code
    assert "absoluteRenderBounds" in plugin_code
    assert "overlap < 0.9" in plugin_code
    assert "textSimilarity < 0.75" in plugin_code
    assert "visualSimilarity < 0.7" in plugin_code
    assert "Possible stacked duplicate content" in plugin_code
    assert "Check these layer paths for duplicated or accidentally stacked sections" in plugin_code
    assert "warnings.push(...findOverlappingStructureWarnings(root))" in plugin_code


def test_figma_plugin_overlap_warning_points_to_nested_layer_paths() -> None:
    plugin_code = _plugin_code()

    assert "function formatStructurePath" in plugin_code
    assert 'join(" > ")' in plugin_code
    assert "!isRoot && bounds" in plugin_code
    assert "visit(root, [], false, true);" in plugin_code
    assert '"${formatStructurePath(first)}"' in plugin_code
    assert '"${formatStructurePath(second)}"' in plugin_code


def test_figma_plugin_surfaces_indexed_warning_topics_in_ui() -> None:
    plugin_code = _plugin_code()
    plugin_ui = _plugin_ui()

    assert "function warningTopic" in plugin_code
    assert 'return "Possible stacked duplicate content detected."' in plugin_code
    assert 'return "Possible duplicate layer detected."' in plugin_code
    assert "function formatWarningNote" in plugin_code
    assert "⚠ [${index + 1}] ${warningTopic(warning)}" in plugin_code
    assert "See figma-plugin/log/warning.txt for full details." in plugin_code
    assert "const warningNote = formatWarningNote(warnings);" in plugin_code
    assert "white-space: pre-line" in plugin_ui
