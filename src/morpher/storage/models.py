from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProcessResult:
    source: Path
    html: Path | None = None
    css: Path | None = None
    elementor: Path | None = None
    success: bool = False
    skipped: bool = False
    warnings: list[str] = field(default_factory=list)
