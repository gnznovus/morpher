from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from morpher.remote_deploy import RemoteTemplateDeploymentService
from morpher.storage.paths import StoragePaths
from morpher.wordpress import WordPressClient


class MemoryCredentials:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def get(self, site_url: str) -> str | None:
        return self.token

    def set(self, site_url: str, token: str) -> None:
        self.token = token

    def delete(self, site_url: str) -> None:
        self.token = None


class FakeClient:
    seen: dict[str, object] = {}

    def __init__(self, base_url: str, *, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token

    def deploy_template(self, **payload):
        self.__class__.seen = {
            "base_url": self.base_url,
            "token": self.token,
            **payload,
        }
        return {
            "status": "imported",
            "ref_no": payload["ref_no"],
            "slug": payload["slug"],
            "title": payload["title"],
            "template_id": 205,
            "build_hash": payload["build_hash"],
            "asset_count": len(payload.get("assets") or []),
            "asset_url": "http://localhost:8080/wp-content/uploads/morpher-assets/happennings",
        }


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self) -> bytes:
        return self.body


def test_remote_deploy_sends_generated_elementor_template_and_assets(tmp_path: Path) -> None:
    storage = StoragePaths(root=tmp_path / "storage", project_root=tmp_path)
    storage.output_elementor.mkdir(parents=True)
    template_path = storage.output_elementor / "happennings_template.json"
    payload = {
        "title": "Happennings",
        "type": "container",
        "content": [
            {
                "id": "real-node",
                "elType": "container",
                "settings": {"background_image": {"url": "assets/happennings/photo.webp"}},
            }
        ],
        "page_settings": [],
    }
    template_path.write_text(json.dumps(payload), encoding="utf-8")

    asset_dir = storage.output_elementor / "assets" / "happennings"
    asset_dir.mkdir(parents=True)
    asset_bytes = b"real-asset-bytes"
    (asset_dir / "photo.webp").write_bytes(asset_bytes)

    service = RemoteTemplateDeploymentService(
        "http://localhost:8080",
        credentials=MemoryCredentials("t" * 43),
        storage=storage,
        client_factory=FakeClient,
    )

    templates = service.templates()
    assert len(templates) == 1
    assert templates[0].name == "happennings_template.json"

    result = service.deploy("happennings_template.json")

    assert result.status == "imported"
    assert result.template_id == 205
    assert result.asset_count == 1
    assert FakeClient.seen["token"] == "t" * 43
    assert FakeClient.seen["slug"] == "happennings"
    assert FakeClient.seen["template"] == payload
    assert FakeClient.seen["asset_root"] == "assets/happennings"
    assets = FakeClient.seen["assets"]
    assert isinstance(assets, list)
    assert assets[0]["path"] == "photo.webp"
    assert base64.b64decode(assets[0]["content"]) == asset_bytes
    assert str(FakeClient.seen["ref_no"]).startswith("MRF-")


def test_wordpress_client_posts_template_assets_with_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    template = {"title": "Happennings", "content": [{"id": "node"}]}
    assets = [{"path": "photo.webp", "sha256": "abc", "content": "cmVhbA=="}]

    def fake_urlopen(request, *, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["authorization"] = request.get_header("Authorization")
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "status": "imported",
                "ref_no": "MRF-ABCD-12",
                "slug": "happennings",
                "title": "Happennings",
                "template_id": 205,
                "build_hash": "hash-1",
                "asset_count": 1,
            }
        )

    monkeypatch.setattr("morpher.wordpress.client.urlopen", fake_urlopen)

    result = WordPressClient("http://localhost:8080", token="t" * 43).deploy_template(
        slug="happennings",
        title="Happennings",
        build_hash="hash-1",
        template=template,
        ref_no="MRF-ABCD-12",
        asset_root="assets/happennings",
        assets=assets,
    )

    assert seen["url"] == "http://localhost:8080/wp-json/morpher/v1/deployments/template"
    assert seen["method"] == "POST"
    assert seen["authorization"] == f"Bearer {'t' * 43}"
    assert seen["payload"] == {
        "slug": "happennings",
        "title": "Happennings",
        "build_hash": "hash-1",
        "ref_no": "MRF-ABCD-12",
        "template": template,
        "asset_root": "assets/happennings",
        "assets": assets,
    }
    assert result["template_id"] == 205
