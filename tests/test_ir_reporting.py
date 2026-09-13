from pathlib import Path

import pytest

import morpher.render as render_module
from morpher.ir.nodes import DesignDocument, DesignNode
from morpher.ir.reporting import format_ir_validation_report, write_ir_validation_log
from morpher.ir.styles import DesignStyle
from morpher.ir.validation import IRDiagnostic, IRValidationError, ValidationResult
from morpher.storage.paths import StoragePaths


def _diagnostic(severity: str, code: str) -> IRDiagnostic:
    return IRDiagnostic(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=f"Message for {code}",
        path=(1, 2),
        node_name="Example",
        source_id="1:2",
        source_type="FRAME",
    )


def test_ir_diagnostics_target_is_project_root_logs(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage", tmp_path)

    assert storage.ir_diagnostics_output(Path("Contact.json")) == tmp_path / "logs" / "Contact-ir.txt"


def test_format_ir_validation_report_groups_notices() -> None:
    validation = ValidationResult(
        (
            _diagnostic("error", "ir.bad_geometry"),
            _diagnostic("warning", "ir.suspicious_layout"),
            _diagnostic("info", "ir.normalized"),
        )
    )

    report = format_ir_validation_report(Path("Contact.json"), validation)

    assert "MORPHER DESIGN IR DIAGNOSTICS" in report
    assert "Source: Contact.json" in report
    assert "Status: INVALID" in report
    assert "Errors: 1" in report
    assert "Warnings: 1" in report
    assert "Info: 1" in report
    assert "ERRORS" in report
    assert "WARNINGS" in report
    assert "INFO" in report
    assert "Path: root/1/2" in report
    assert "source_id='1:2'" in report


def test_write_ir_validation_log_persists_notices(tmp_path: Path) -> None:
    target = tmp_path / "logs" / "Contact-ir.txt"
    validation = ValidationResult((_diagnostic("warning", "ir.notice"),))

    written = write_ir_validation_log(Path("Contact.json"), validation, target)

    assert written == target
    assert target.is_file()
    assert "ir.notice" in target.read_text(encoding="utf-8")


def test_clean_validation_removes_stale_ir_log(tmp_path: Path) -> None:
    target = tmp_path / "logs" / "Contact-ir.txt"
    target.parent.mkdir(parents=True)
    target.write_text("stale", encoding="utf-8")

    written = write_ir_validation_log(Path("Contact.json"), ValidationResult(()), target)

    assert written is None
    assert not target.exists()


def test_render_path_writes_blocking_ir_failure_to_root_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = StoragePaths(tmp_path / "storage", tmp_path)
    invalid = DesignDocument(
        root=DesignNode(
            kind="container",
            name="Broken",
            source_id="broken",
            source_type="FRAME",
            style=DesignStyle(width=-1),
        )
    )

    monkeypatch.setattr(render_module, "StoragePaths", lambda: storage)
    monkeypatch.setattr(render_module.FigmaJsonAdapter, "load", lambda self, path: invalid)

    source = tmp_path / "Contact.json"
    with pytest.raises(IRValidationError):
        render_module.render_path(source, fidelity=False, native=False)

    report_path = tmp_path / "logs" / "Contact-ir.txt"
    assert report_path.is_file()
    report = report_path.read_text(encoding="utf-8")
    assert "Status: INVALID" in report
    assert "ir.negative_size" in report
    assert "name='Broken'" in report
