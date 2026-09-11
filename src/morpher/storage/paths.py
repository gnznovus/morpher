from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoragePaths:
    root: Path = Path("storage")

    @property
    def figma_import(self) -> Path:
        return self.root / "figma-import"

    @property
    def input(self) -> Path:
        return self.root / "input"

    @property
    def processed(self) -> Path:
        return self.root / "processed"

    @property
    def fonts(self) -> Path:
        return self.root / "fonts"

    @property
    def log(self) -> Path:
        return self.root / "log"

    @property
    def output_html(self) -> Path:
        return self.root / "output" / "html"

    @property
    def output_elementor(self) -> Path:
        return self.root / "output" / "elementor"

    def ensure(self) -> None:
        for path in (
            self.figma_import,
            self.input,
            self.processed,
            self.fonts,
            self.log,
            self.output_html,
            self.output_elementor,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def html_output(self, source: Path) -> Path:
        return self.output_html / f"{source.stem}.html"

    def css_output(self, source: Path) -> Path:
        return self.output_html / f"{source.stem}.css"

    def figma_asset_dir(self, source: Path) -> Path:
        return self.figma_import / "assets" / source.stem

    def html_asset_dir(self, source: Path) -> Path:
        return self.output_html / "assets" / source.stem

    def elementor_asset_dir(self, source: Path) -> Path:
        return self.output_elementor / "assets" / source.stem

    def elementor_output(self, source: Path) -> Path:
        return self.output_elementor / f"{source.stem}_template.json"

    def trace_output(self, source: Path) -> Path:
        return self.log / f"{source.stem}.txt"

    def processed_output(self, source: Path) -> Path:
        return self.processed / f"{source.stem}_P{source.suffix}"
