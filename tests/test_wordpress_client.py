from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from morpher.wordpress import WordPressClient, WordPressClientError


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_health_reads_morpher_wordpress_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "status": "ok",
        "service": "morpher-wordpress",
        "api_version": "v1",
        "plugin": {"version": "0.4.0"},
        "wordpress": {"version": "7.1", "site_url": "http://localhost:8080"},
        "integrations": {
            "elementor": {"ready": True, "version": "4.2.4"},
        },
        "capabilities": ["health"],
    }
    seen: dict[str, object] = {}

    def fake_urlopen(request, *, timeout):
        seen["url"] = request.full_url
        seen["accept"] = request.get_header("Accept")
        seen["timeout"] = timeout
        return FakeResponse(payload)

    monkeypatch.setattr("morpher.wordpress.client.urlopen", fake_urlopen)

    health = WordPressClient("http://localhost:8080/", timeout=2.5).health()

    assert seen == {
        "url": "http://localhost:8080/wp-json/morpher/v1/health",
        "accept": "application/json",
        "timeout": 2.5,
    }
    assert health.status == "ok"
    assert health.service == "morpher-wordpress"
    assert health.api_version == "v1"
    assert health.plugin.version == "0.4.0"
    assert health.wordpress.version == "7.1"
    assert health.wordpress.site_url == "http://localhost:8080"
    assert health.integrations.elementor.ready is True
    assert health.integrations.elementor.version == "4.2.4"
    assert health.connection.paired is False
    assert health.capabilities == ("health",)


def test_pair_generates_token_and_sends_pairing_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    generated_token = "a" * 43
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        "morpher.wordpress.client.secrets.token_urlsafe",
        lambda size: generated_token,
    )

    def fake_urlopen(request, *, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["content_type"] = request.get_header("Content-type")
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "status": "connected",
                "site_url": "http://localhost:8080",
                "api_version": "v1",
            }
        )

    monkeypatch.setattr("morpher.wordpress.client.urlopen", fake_urlopen)

    client = WordPressClient("http://localhost:8080")
    token = client.pair("123456")

    assert token == generated_token
    assert client.token == generated_token
    assert seen == {
        "url": "http://localhost:8080/wp-json/morpher/v1/pairing/complete",
        "method": "POST",
        "content_type": "application/json",
        "payload": {"code": "123456", "token": generated_token},
    }


def test_pair_rejects_invalid_pairing_code() -> None:
    with pytest.raises(ValueError, match="six digits"):
        WordPressClient("http://localhost:8080").pair("12345")


def test_deployments_sends_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "b" * 43
    seen: dict[str, object] = {}

    def fake_urlopen(request, *, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        return FakeResponse(
            {
                "deployments": [
                    {
                        "deployment": "home",
                        "slug": "home",
                        "title": "Home",
                        "status": "imported",
                        "template_id": 42,
                        "error": "",
                    }
                ]
            }
        )

    monkeypatch.setattr("morpher.wordpress.client.urlopen", fake_urlopen)

    deployments = WordPressClient(
        "http://localhost:8080",
        token=token,
    ).deployments()

    assert seen == {
        "url": "http://localhost:8080/wp-json/morpher/v1/deployments",
        "authorization": f"Bearer {token}",
    }
    assert len(deployments) == 1
    assert deployments[0].title == "Home"
    assert deployments[0].template_id == 42


def test_deployments_requires_paired_client() -> None:
    with pytest.raises(WordPressClientError, match="not paired"):
        WordPressClient("http://localhost:8080").deployments()


def test_health_wraps_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, *, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr("morpher.wordpress.client.urlopen", fake_urlopen)

    with pytest.raises(WordPressClientError, match="Could not connect to WordPress"):
        WordPressClient("http://localhost:8080").health()


def test_health_rejects_non_object_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "morpher.wordpress.client.urlopen",
        lambda request, *, timeout: FakeResponse(["unexpected"]),
    )

    with pytest.raises(WordPressClientError, match="unexpected response"):
        WordPressClient("http://localhost:8080").health()


def test_client_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base URL"):
        WordPressClient("   ")
