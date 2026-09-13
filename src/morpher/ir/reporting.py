from __future__ import annotations

from pathlib import Path

from .validation import IRDiagnostic, ValidationResult


def _format_diagnostic(index: int, diagnostic: IRDiagnostic) -> list[str]:
    node_bits: list[str] = []
    if diagnostic.node_name:
        node_bits.append(f"name={diagnostic.node_name!r}")
    if diagnostic.source_id:
        node_bits.append(f"source_id={diagnostic.source_id!r}")
    if diagnostic.source_type:
        node_bits.append(f"source_type={diagnostic.source_type!r}")

    lines = [
        f"[{index}] {diagnostic.code}",
        f"Path: {diagnostic.path_string}",
    ]
    if node_bits:
        lines.append("Node: " + ", ".join(node_bits))
    lines.append(f"Message: {diagnostic.message}")
    return lines


def format_ir_validation_report(source: Path, validation: ValidationResult) -> str:
    """Render actionable Design IR diagnostics for Morpher's root logs directory."""

    lines = [
        "MORPHER DESIGN IR DIAGNOSTICS",
        "=============================",
        "",
        f"Source: {source.name}",
        f"Status: {'INVALID' if validation.errors else 'VALID WITH NOTICES'}",
        f"Errors: {len(validation.errors)}",
        f"Warnings: {len(validation.warnings)}",
        f"Info: {len(validation.info)}",
    ]

    for title, diagnostics in (
        ("ERRORS", validation.errors),
        ("WARNINGS", validation.warnings),
        ("INFO", validation.info),
    ):
        if not diagnostics:
            continue
        lines.extend(["", title])
        for index, diagnostic in enumerate(diagnostics, start=1):
            lines.extend(_format_diagnostic(index, diagnostic))
            if index != len(diagnostics):
                lines.append("")

    lines.extend(["", f"Total notices: {len(validation.diagnostics)}", ""])
    return "\n".join(lines)


def write_ir_validation_log(
    source: Path,
    validation: ValidationResult,
    target: Path,
) -> Path | None:
    """Persist only actionable IR notices and remove a stale clean-run report."""

    if not validation.diagnostics:
        if target.exists():
            target.unlink()
        return None

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        format_ir_validation_report(source, validation),
        encoding="utf-8",
    )
    return target
