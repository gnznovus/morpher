from __future__ import annotations

import threading
import webbrowser

import uvicorn

from .app import create_dashboard_app


def run_dashboard(
    target: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    app = create_dashboard_app(target)
    dashboard_url = f"http://{host}:{port}"

    if open_browser:
        threading.Timer(0.75, webbrowser.open, args=(dashboard_url,)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
