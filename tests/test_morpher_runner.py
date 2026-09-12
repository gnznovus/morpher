from pathlib import Path

import pytest

from morpher import run
from morpher.render import RenderOutputs
from morpher.storage.paths import StoragePaths


def _outputs(tmp_path: Path, source: Path, warning_count: int = 0) -> RenderOutputs:
    storage = StoragePaths(tmp_path / "storage")
    return RenderOutputs(
        fidelity_html=storage.fidelity_html_output(source),
        fidelity_css=storage.fidelity_css_output(source),
        native_html=storage.native_html_output(source),
        native_css=storage.native_css_output(source),
        elementor=storage.elementor_output(source),
        warning_count=warning_count,
    )


def test_run_source_consumes_render_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    source = storage.figma_import / "Newsletter.json"
    outputs = _outputs(tmp_path, source, warning_count=3)
    inspected: list[Path] = []

    monkeypatch.setattr(run, "inspect_path", inspected.append)
    monkeypatch.setattr(run, "render_path", lambda path: outputs)

    result = run.run_source(source, storage, force=True)

    assert inspected == [source]
    assert result.status == "processed"
    assert result.warnings == 3
    assert result.outputs == outputs
    assert result.error is None


def test_source_is_complete_only_when_all_current_outputs_exist(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    storage.ensure()
    source = storage.figma_import / "Newsletter.json"

    required = [
        storage.fidelity_html_output(source),
        storage.fidelity_css_output(source),
        storage.native_html_output(source),
        storage.native_css_output(source),
        storage.elementor_output(source),
    ]
    for path in required:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")

    assert run._outputs_exist(source, storage)

    storage.native_css_output(source).unlink()

    assert not run._outputs_exist(source, storage)


def test_main_reports_generated_targets_and_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    source = Path("storage/figma-import/Newsletter.json")
    outputs = _outputs(tmp_path, source, warning_count=2)
    result = run.RunResult(
        source=source,
        status="processed",
        warnings=2,
        outputs=outputs,
    )

    monkeypatch.setattr(run, "run_all", lambda target=None, force=False: [result])
    monkeypatch.setattr("sys.argv", ["morpher"])

    run.main()

    stdout = capsys.readouterr().out
    assert f"PROCESS  {source}  warnings=2" in stdout
    assert f"Fidelity HTML: {outputs.fidelity_html}" in stdout
    assert f"Fidelity CSS:  {outputs.fidelity_css}" in stdout
    assert f"Native HTML:   {outputs.native_html}" in stdout
    assert f"Native CSS:    {outputs.native_css}" in stdout
    assert f"Elementor:     {outputs.elementor}" in stdout
    assert "Result: processed=1 skipped=0 failed=0" in stdout


def test_main_reports_existing_paths_when_source_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    source = Path("storage/figma-import/Newsletter.json")
    outputs = _outputs(tmp_path, source)
    result = run.RunResult(source=source, status="skipped", outputs=outputs)

    monkeypatch.setattr(run, "run_all", lambda target=None, force=False: [result])
    monkeypatch.setattr("sys.argv", ["morpher"])

    run.main()

    stdout = capsys.readouterr().out
    assert f"SKIP     {source}  outputs already exist" in stdout
    assert f"Fidelity HTML: {outputs.fidelity_html}" in stdout
    assert f"Native HTML:   {outputs.native_html}" in stdout
    assert f"Elementor:     {outputs.elementor}" in stdout
    assert "Result: processed=0 skipped=1 failed=0" in stdout


def test_clean_outputs_recreates_all_renderer_roots(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    stale = storage.output_html / "stale.txt"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("old", encoding="utf-8")

    run.clean_outputs(storage)

    assert not stale.exists()
    assert storage.output_html_fidelity.is_dir()
    assert storage.output_html_native.is_dir()
    assert storage.output_elementor.is_dir()
