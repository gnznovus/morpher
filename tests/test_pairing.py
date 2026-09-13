from __future__ import annotations

from types import SimpleNamespace

from morpher.connections import ConnectionStore
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
    health_response = None

    def __init__(self, base_url: str, *, token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token
        self.completed: dict[str, object] | None = None
        self.ack: dict[str, object] | None = None
        self.__class__.instances.append(self)

    def health(self):
        if self.__class__.health_response is None:
            raise AssertionError("No fake health response configured.")
        return self.__class__.health_response

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


def test_pairing_service_accepts_request_and_acknowledges(monkeypatch, tmp_path) -> None:
    FakeWordPressClient.instances.clear()
    credentials = MemoryCredentials()
    connections = ConnectionStore(tmp_path / "connections.json")
    service = PairingService(
        "http://localhost:8080",
        credentials,
        store=PairingRequestStore(),
        connections=connections,
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
    assert connected.code == ""
    assert credentials.get("http://localhost:8080") == "t" * 43
    assert connections.get("http://localhost:8080").ref_no == "MRF-8K4P-27"
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


def test_connection_registry_survives_service_restart(monkeypatch, tmp_path) -> None:
    credentials = MemoryCredentials()
    path = tmp_path / "connections.json"
    first = PairingService(
        "http://localhost:8080",
        credentials,
        connections=ConnectionStore(path),
        client_factory=FakeWordPressClient,
    )
    monkeypatch.setattr("morpher.pairing.secrets.token_urlsafe", lambda size: "t" * 43)
    pending = first.receive(
        {
            "request_id": "request-persist",
            "ref_no": "MRF-SAVE-01",
            "site_url": "http://localhost:8080",
            "site_name": "Morpher Test Site",
            "plugin_version": "0.5.0",
            "wordpress_version": "7.1",
            "code": "123456",
            "expires_in": 300,
        }
    )
    first.accept(pending.request_id)

    restarted = PairingService(
        "http://localhost:8080",
        credentials,
        connections=ConnectionStore(path),
        client_factory=FakeWordPressClient,
    )
    rows = restarted.list_requests()

    assert len(rows) == 1
    assert rows[0].status == "connected"
    assert rows[0].site_name == "Morpher Test Site"
    assert rows[0].ref_no == "MRF-SAVE-01"


def test_existing_keyring_connection_bootstraps_registry(tmp_path) -> None:
    credentials = MemoryCredentials()
    credentials.set("http://localhost:8080", "t" * 43)
    FakeWordPressClient.health_response = SimpleNamespace(
        connection=SimpleNamespace(
            paired=True,
            ref_no="MRF-OLD-01",
            metadata={"paired_at": "2026-09-13T03:00:00+00:00"},
        ),
        wordpress=SimpleNamespace(
            site_name="Morpher Test Site",
            version="7.1",
        ),
        plugin=SimpleNamespace(version="0.5.0"),
    )
    connections = ConnectionStore(tmp_path / "connections.json")
    service = PairingService(
        "http://localhost:8080",
        credentials,
        connections=connections,
        client_factory=FakeWordPressClient,
    )

    restored = service.restore_existing_connection()

    assert restored is not None
    assert restored.ref_no == "MRF-OLD-01"
    assert restored.site_name == "Morpher Test Site"
    assert connections.get("http://localhost:8080") == restored
    FakeWordPressClient.health_response = None


def test_pairing_service_rejects_without_creating_credentials(tmp_path) -> None:
    credentials = MemoryCredentials()
    service = PairingService(
        "http://localhost:8080",
        credentials,
        connections=ConnectionStore(tmp_path / "connections.json"),
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
