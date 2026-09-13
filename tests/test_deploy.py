import base64
import json
from pathlib import Path

from morpher.deploy import DeploymentService, build_deployment_package, deploy_all, resolve_template_target
from morpher.storage.paths import StoragePaths


class MemoryCredentials:
    def __init__(self, token: str | None = "t" * 43) -> None:
        self.token = token

    def get(self, site_url: str) -> str | None:
        return self.token

    def set(self, site_url: str, token: str) -> None:
        self.token = token

    def delete(self, site_url: str) -> None:
        self.token = None


class FakeClient:
    seen: list[dict[str, object]] = []

    def __init__(self, base_url: str, *, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token

    def stage_deployment(self, **payload):
        self.__class__.seen.append({"base_url": self.base_url, "token": self.token, **payload})
        return {
            "status": "staged",
            "ref_no": payload["ref_no"],
            "deployment": payload["manifest"]["slug"],
        }


def _storage(tmp_path: Path) -> StoragePaths:
    storage = StoragePaths(root=tmp_path / "storage", project_root=tmp_path)
    storage.ensure()
    return storage


def _write_template(storage: StoragePaths, name: str = "Stay-Residences") -> Path:
    template = storage.output_elementor / f"{name}_template.json"
    template.write_text(
        json.dumps(
            {
                "content": [{"id": "root", "elType": "container", "settings": {}, "elements": [], "isInner": False}],
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

    assert resolve_template_target("Stay-Residences.json", storage) == template.resolve()
    assert resolve_template_target(storage.output_elementor / "Stay-Residences_template.json", storage) == template.resolve()


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


def test_package_reuses_template_and_asset_discovery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    template = _write_template(storage)

    package = build_deployment_package(template, storage)

    assert package.manifest["slug"] == "stay-residences"
    assert package.manifest["title"] == "Stay > Residences"
    assert package.manifest["asset_root"] == "assets/Stay-Residences"
    assert package.manifest["force"] is False
    assert len(str(package.manifest["build_hash"])) == 64
    assert package.assets[0]["path"] == "hero.webp"
    assert base64.b64decode(package.assets[0]["content"]) == b"webp"


def test_deployment_service_stages_package_over_rest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    _write_template(storage)
    FakeClient.seen = []

    service = DeploymentService(
        "http://localhost:8080",
        storage=storage,
        credentials=MemoryCredentials(),
        client_factory=FakeClient,
    )
    result = service.deploy("Stay-Residences")

    assert result.status == "staged"
    assert result.deployment == "stay-residences"
    assert result.ref_no.startswith("MRF-")
    sent = FakeClient.seen[0]
    assert sent["base_url"] == "http://localhost:8080"
    assert sent["token"] == "t" * 43
    assert sent["manifest"]["slug"] == "stay-residences"
    assert sent["template"]["title"] == "Stay > Residences"
    assert sent["assets"][0]["path"] == "hero.webp"


def test_bulk_deploy_uses_same_service_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = _storage(tmp_path)
    _write_template(storage, "One")
    _write_template(storage, "Two")
    (storage.output_elementor / "ignore.json").write_text("{}", encoding="utf-8")
    FakeClient.seen = []

    results = deploy_all(
        target_url="http://localhost:8080",
        storage=storage,
        credentials=MemoryCredentials(),
        client_factory=FakeClient,
    )

    assert [result.template.name for result in results] == ["One_template.json", "Two_template.json"]
    assert all(result.status == "staged" for result in results)
    assert len(FakeClient.seen) == 2
