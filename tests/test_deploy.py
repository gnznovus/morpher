import json
from pathlib import Path

from morpher.deploy import deploy_all, resolve_template_target, stage_template
from morpher.storage.paths import StoragePaths


def _storage(tmp_path: Path) -> StoragePaths:
    storage = StoragePaths(root=tmp_path / "storage", project_root=tmp_path)
    storage.ensure()
    return storage


def _write_template(storage: StoragePaths, name: str = "Stay-Residences") -> Path:
    template = storage.output_elementor / f"{name}_template.json"
    template.write_text(
        json.dumps(
            {
                "content": [
                    {
                        "id": "root",
                        "elType": "container",
                        "settings": {},
                        "elements": [],
                        "isInner": False,
                    }
                ],
                "page_settings": [],
                "version": "0.4",
                "title": "Stay > Residences",
                "type": "container",
            }
        ),
        encoding="utf-8",
    )
    asset_dir = storage.output_elementor / "assets" / name
    asset_dir.mkdir(parents=True)
    (asset_dir / "hero.webp").write_bytes(b"webp")
    return template


def test_target_filename_and_path_resolve_to_same_elementor_template(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    template = _write_template(storage)

    by_name = resolve_template_target("Stay-Residences.json", storage)
    by_path = resolve_template_target(
        storage.output_elementor / "Stay-Residences_template.json",
        storage,
    )

    assert by_name == template.resolve()
    assert by_path == template.resolve()


def test_target_cannot_escape_elementor_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    outside = tmp_path / "other.json"
    outside.write_text("{}", encoding="utf-8")

    try:
        resolve_template_target(outside, storage)
    except ValueError as exc:
        assert "under" in str(exc)
    else:
        raise AssertionError("outside template should not resolve")


def test_stage_copies_template_assets_and_manifest_then_skips_same_build(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    template = _write_template(storage)

    first = stage_template(template, storage)
    assert first.status == "staged"
    assert first.deployment is not None
    assert (first.deployment / "template.json").is_file()
    assert (first.deployment / "assets" / "hero.webp").read_bytes() == b"webp"

    manifest = json.loads((first.deployment / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["slug"] == "stay-residences"
    assert manifest["title"] == "Stay > Residences"
    assert manifest["asset_root"] == "assets/Stay-Residences"
    assert manifest["force"] is False
    assert len(manifest["build_hash"]) == 64

    second = stage_template(template, storage)
    assert second.status == "skipped"


def test_force_restages_same_build(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    template = _write_template(storage)
    assert stage_template(template, storage).status == "staged"

    forced = stage_template(template, storage, force=True)
    assert forced.status == "staged"
    manifest = json.loads((forced.deployment / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["force"] is True


def test_bulk_deploy_only_reads_elementor_templates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    _write_template(storage, "One")
    _write_template(storage, "Two")
    (storage.output_elementor / "ignore.json").write_text("{}", encoding="utf-8")

    results = deploy_all(storage=storage)

    assert [result.template.name for result in results] == ["One_template.json", "Two_template.json"]
    assert all(result.status == "staged" for result in results)
