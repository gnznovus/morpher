from pathlib import Path

from morpher.storage.paths import StoragePaths


def test_html_targets_have_separate_output_roots(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    source = Path("Newsletter.json")

    assert storage.fidelity_html_output(source) == tmp_path / "storage" / "output" / "html" / "fidelity" / "Newsletter.html"
    assert storage.fidelity_css_output(source) == tmp_path / "storage" / "output" / "html" / "fidelity" / "Newsletter.css"
    assert storage.native_html_output(source) == tmp_path / "storage" / "output" / "html" / "native" / "Newsletter.html"
    assert storage.native_css_output(source) == tmp_path / "storage" / "output" / "html" / "native" / "Newsletter.css"


def test_storage_ensure_creates_both_html_target_directories(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")

    storage.ensure()

    assert storage.output_html_fidelity.is_dir()
    assert storage.output_html_native.is_dir()


def test_legacy_html_helpers_point_to_fidelity(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    source = Path("Newsletter.json")

    assert storage.html_output(source) == storage.fidelity_html_output(source)
    assert storage.css_output(source) == storage.fidelity_css_output(source)
    assert storage.html_asset_dir(source) == storage.fidelity_asset_dir(source)
