from __future__ import annotations

from morpher.pairing import PairingRequestStore, PairingService


class MemoryCredentials:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, site_url: str) -> str | None:
        return self.values.get(site_url)

    def set(self, site_url: str, token: str) -> None:
        self.values[site_url] = token

    def delete(self, site_url: str) -> None:
        self.values.pop(site_url, None)


class FakeWordPressClient:
    instances: list["FakeWordPressClient"] = []

    def __init__(self, base_url: str, *, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token
        self.completed: dict[str, object] | None = None
        self.ack: dict[str, object] | None = None
        self.__class__.instances.append(self)

    def complete_pairing(self, code, token, *, request_id=None, ref_no=None):
        self.completed = {
            "code": code,
            "token": token,
            "request_id": request_id,
            "ref_no": ref_no,
        }
        return {"status": "connected"}

    def acknowledge(self, ref_no, *, event, status="acknowledged", metadata=None):
        self.ack = {
            "ref_no": ref_no,
            "event": event,
            "status": status,
            "metadata": metadata,
        }
        return {"status": status}


def test_pairing_service_accepts_request_and_acknowledges(monkeypatch) -> None:
    FakeWordPressClient.instances.clear()
    credentials = MemoryCredentials()
    service = PairingService(
        "http://localhost:8080",
        credentials,
        store=PairingRequestStore(),
        client_factory=FakeWordPressClient,
    )
    monkeypatch.setattr("morpher.pairing.secrets.token_urlsafe", lambda size: "t" * 43)

    pending = service.receive(
        {
            "request_id": "request-1",
            "ref_no": "MRF-8K4P-27",
            "site_url": "http://localhost:8080/",
            "site_name": "Morpher Test",
            "plugin_version": "0.5.0",
            "wordpress_version": "7.1",
            "code": "123456",
            "expires_in": 300,
        }
    )
    connected = service.accept(pending.request_id)

    assert connected.status == "connected"
    assert credentials.get("http://localhost:8080") == "t" * 43
    client = FakeWordPressClient.instances[-1]
    assert client.completed == {
        "code": "123456",
        "token": "t" * 43,
        "request_id": "request-1",
        "ref_no": "MRF-8K4P-27",
    }
    assert client.ack == {
        "ref_no": "MRF-8K4P-27",
        "event": "pairing.completed",
        "status": "acknowledged",
        "metadata": {"request_id": "request-1"},
    }


def test_pairing_service_rejects_without_creating_credentials() -> None:
    credentials = MemoryCredentials()
    service = PairingService(
        "http://localhost:8080",
        credentials,
        client_factory=FakeWordPressClient,
    )
    pending = service.receive(
        {
            "request_id": "request-2",
            "ref_no": "MRF-TEST-01",
            "site_url": "http://localhost:8080",
            "site_name": "Morpher Test",
            "code": "654321",
            "expires_in": 300,
        }
    )

    rejected = service.reject(pending.request_id)

    assert rejected.status == "rejected"
    assert credentials.values == {}
