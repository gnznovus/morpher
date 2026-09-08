from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from morpher.storage.paths import StoragePaths


@dataclass
class Trace:
    source: Path
    storage: StoragePaths = field(default_factory=StoragePaths)
    lines: list[str] = field(default_factory=list)

    def add(self, message: str = "") -> None:
        self.lines.append(message)

    def section(self, title: str) -> None:
        if self.lines and self.lines[-1] != "":
            self.lines.append("")
        self.lines.append(f"=== {title} ===")

    def extend(self, values: list[str]) -> None:
        self.lines.extend(values)

    def render(self) -> str:
        header = [
            "MORPHER TRACE",
            f"SOURCE: {self.source}",
            f"CREATED: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
        ]
        return "\n".join(header + self.lines).rstrip() + "\n"

    def write(self) -> Path:
        self.storage.ensure()
        output = self.storage.trace_output(self.source)
        output.write_text(self.render(), encoding="utf-8")
        return output
