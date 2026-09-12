from pathlib import Path

import pytest

from morpher.run import resolve_source_target, run_all
from morpher.storage.paths import StoragePaths


def _storage(tmp_path: Path) -> StoragePaths:
    storage = StoragePaths(root=tmp_path / "storage", project_root=tmp_path)
    storage.ensure()
    return storage


def test_bare_target_resolves_figma_import_with_or_without_extension(tmp_path):
    storage = _storage(tmp_path)
    source = storage.figma_import / "Stay-Residences-Detail.json"
    source.write_text("{}", encoding="utf-8")

    assert resolve_source_target("Stay-Residences-Detail", storage) == source.resolve()
    assert resolve_source_target("Stay-Residences-Detail.json", storage) == source.resolve()


def test_figma_import_has_priority_over_input_for_same_bare_name(tmp_path):
    storage = _storage(tmp_path)
    figma = storage.figma_import / "Dine.json"
    generic = storage.input / "Dine.json"
    figma.write_text("{}", encoding="utf-8")
    generic.write_text("{}", encoding="utf-8")

    assert resolve_source_target("Dine", storage) == figma.resolve()


def test_friendly_queue_paths_resolve_inside_storage(tmp_path, monkeypatch):
    storage = _storage(tmp_path)
    figma = storage.figma_import / "Dine.json"
    generic = storage.input / "Other.json"
    figma.write_text("{}", encoding="utf-8")
    generic.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert resolve_source_target("figma-import/Dine", storage) == figma.resolve()
    assert resolve_source_target("storage/figma-import/Dine.json", storage) == figma.resolve()
    assert resolve_source_target("input/Other", storage) == generic.resolve()
    assert resolve_source_target("storage/input/Other.json", storage) == generic.resolve()


def test_target_cannot_escape_morpher_source_roots(tmp_path, monkeypatch):
    storage = _storage(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Morpher source not found"):
        resolve_source_target("../outside.json", storage)

    with pytest.raises(ValueError, match="Morpher source not found"):
        resolve_source_target(str(outside), storage)


def test_run_all_returns_target_failure_without_bulk_fallback(tmp_path):
    storage = _storage(tmp_path)
    (storage.figma_import / "Existing.json").write_text("{}", encoding="utf-8")

    results = run_all("Missing", storage=storage)

    assert len(results) == 1
    assert results[0].status == "failed"
    assert results[0].source == Path("Missing")
    assert "Morpher source not found" in (results[0].error or "")
