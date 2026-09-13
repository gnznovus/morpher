from __future__ import annotations

from morpher.dashboard import create_dashboard_app
from morpher.run import main


def test_dashboard_app_exposes_local_dashboard_routes() -> None:
    app = create_dashboard_app("http://localhost:8080")

    assert app.state.target == "http://localhost:8080"
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
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
