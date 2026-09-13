from pathlib import Path

from morpher.ir.reporting import format_ir_validation_report, write_ir_validation_log
from morpher.ir.validation import IRDiagnostic, ValidationResult
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
