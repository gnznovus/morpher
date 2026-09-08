from pathlib import Path

from .models import ProcessResult
from .paths import StoragePaths


class BatchProcessor:
    """Foundation processor for deterministic output and archive behavior."""

    def __init__(self, storage: StoragePaths) -> None:
        self.storage = storage

    def output_exists(self, source: Path) -> bool:
        return any(
            path.exists()
            for path in (
                self.storage.html_output(source),
                self.storage.css_output(source),
                self.storage.elementor_output(source),
            )
        )

    def planned_result(self, source: Path) -> ProcessResult:
        return ProcessResult(
            source=source,
            html=self.storage.html_output(source),
            css=self.storage.css_output(source),
            elementor=self.storage.elementor_output(source),
        )
