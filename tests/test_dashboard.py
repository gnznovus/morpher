from __future__ import annotations

from morpher.dashboard import create_dashboard_app
from morpher.run import main


class DummyCredentials:
    def get(self, site_url: str):
        return None

    def set(self, site_url: str, token: str):
        return None

    def delete(self, site_url: str):
        return None


class DummyPairingService:
    def list_requests(self):
        return ()

    def receive(self, payload):
        class Item:
            request_id = payload["request_id"]
            ref_no = payload["ref_no"]
        return Item()

    def accept(self, request_id):
        raise AssertionError("not used")

    def reject(self, request_id):
        raise AssertionError("not used")


def test_dashboard_app_exposes_local_dashboard_routes() -> None:
    app = create_dashboard_app(
        "http://localhost:8080",
        pairing_service=DummyPairingService(),
    )

    assert app.state.target == "http://localhost:8080"
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
    assert "/api/pairing/requests" in paths
    assert "/pairing/requests" in paths
    assert "/pairing/requests/{request_id}/accept" in paths
    assert "/pairing/requests/{request_id}/reject" in paths
    assert "/deployment/templates" in paths
    assert "/deployment/templates/{template_name}" in paths
    assert "/static" in paths
    assert "/docs" not in paths
    assert "/redoc" not in paths


def test_dashboard_command_routes_to_local_server(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_run_dashboard(target, *, host, port, open_browser):
        seen.update(
            target=target,
            host=host,
            port=port,
            open_browser=open_browser,
        )

    monkeypatch.setattr("morpher.dashboard.run_dashboard", fake_run_dashboard)

    main(
        [
            "dashboard",
            "http://localhost:8080/",
            "--port",
            "9001",
            "--no-browser",
        ]
    )

    assert seen == {
        "target": "http://localhost:8080",
        "host": "127.0.0.1",
        "port": 9001,
        "open_browser": False,
    }
