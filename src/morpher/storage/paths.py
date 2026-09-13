from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoragePaths:
    root: Path = Path("storage")
    project_root: Path = Path(".")

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
    def font_registry_cache(self) -> Path:
        return self.fonts / "font-registry.json"

    @property
    def log(self) -> Path:
        return self.root / "log"

    @property
    def root_logs(self) -> Path:
        return self.project_root / "logs"

    @property
    def ir_logs(self) -> Path:
        return self.root_logs / "IR"

    @property
    def output_html(self) -> Path:
        return self.root / "output" / "html"

    @property
    def output_html_fidelity(self) -> Path:
        return self.output_html / "fidelity"

    @property
    def output_html_native(self) -> Path:
        return self.output_html / "native"

    @property
    def output_elementor(self) -> Path:
        return self.root / "output" / "elementor"

    @property
    def elementor_font_plugin(self) -> Path:
        # Keep the plugin in the project tree so Docker and the future Morpher app
        # can share one persistent WordPress integration target.
        return self.project_root / "wp-content" / "plugins" / "morpher-plugin"

    def ensure(self) -> None:
        for path in (
            self.figma_import,
            self.input,
            self.processed,
            self.fonts,
            self.log,
            self.output_html,
            self.output_html_fidelity,
            self.output_html_native,
            self.output_elementor,
            self.elementor_font_plugin,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def fidelity_html_output(self, source: Path) -> Path:
        return self.output_html_fidelity / f"{source.stem}.html"

    def fidelity_css_output(self, source: Path) -> Path:
        return self.output_html_fidelity / f"{source.stem}.css"

    def native_html_output(self, source: Path) -> Path:
        return self.output_html_native / f"{source.stem}.html"

    def native_css_output(self, source: Path) -> Path:
        return self.output_html_native / f"{source.stem}.css"

    # Backward-compatible aliases: the old generic HTML target is Fidelity.
    def html_output(self, source: Path) -> Path:
        return self.fidelity_html_output(source)

    def css_output(self, source: Path) -> Path:
        return self.fidelity_css_output(source)

    def figma_asset_dir(self, source: Path) -> Path:
        return self.figma_import / "assets" / source.stem

    def fidelity_asset_dir(self, source: Path) -> Path:
        return self.output_html_fidelity / "assets" / source.stem

    def native_asset_dir(self, source: Path) -> Path:
        return self.output_html_native / "assets" / source.stem

    def native_font_asset_dir(self) -> Path:
        return self.output_html_native / "assets" / "fonts"

    def html_asset_dir(self, source: Path) -> Path:
        return self.fidelity_asset_dir(source)

    def elementor_asset_dir(self, source: Path) -> Path:
        return self.output_elementor / "assets" / source.stem

    def elementor_output(self, source: Path) -> Path:
        return self.output_elementor / f"{source.stem}_template.json"

    def trace_output(self, source: Path) -> Path:
        return self.log / f"{source.stem}.txt"

    def ir_diagnostics_output(self, source: Path) -> Path:
        return self.ir_logs / f"{source.stem}-ir.txt"

    def processed_output(self, source: Path) -> Path:
        return self.processed / f"{source.stem}_P{source.suffix}"
