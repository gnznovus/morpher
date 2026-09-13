from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from morpher.wordpress import WordPressClient, WordPressClientError

ClientFactory = Callable[[str], WordPressClient]

_DASHBOARD_ROOT = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_DASHBOARD_ROOT / "templates"))


def create_dashboard_app(
    target: str,
    *,
    client_factory: ClientFactory = WordPressClient,
) -> FastAPI:
    app = FastAPI(title="Morpher Dashboard", docs_url=None, redoc_url=None)
    app.state.target = target
    app.state.client_factory = client_factory
    app.mount(
        "/static",
        StaticFiles(directory=str(_DASHBOARD_ROOT / "static")),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="index.html",
            context={"target": app.state.target},
        )

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request) -> HTMLResponse:
        health_data = None
        error = None
        try:
            health_data = app.state.client_factory(app.state.target).health()
        except (ValueError, WordPressClientError) as exc:
            error = str(exc)

        return _TEMPLATES.TemplateResponse(
            request=request,
            name="partials/health.html",
            context={
                "target": app.state.target,
                "health": health_data,
                "error": error,
            },
        )

    return app
