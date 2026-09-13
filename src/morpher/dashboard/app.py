from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from morpher.credentials import KeyringCredentialStore
from morpher.pairing import PairingError, PairingService
from morpher.wordpress import WordPressClient, WordPressClientError

ClientFactory = Callable[[str], WordPressClient]

_DASHBOARD_ROOT = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_DASHBOARD_ROOT / "templates"))


class PairingRequestPayload(BaseModel):
    request_id: str
    ref_no: str
    site_url: str
    site_name: str = "WordPress"
    plugin_version: str = ""
    wordpress_version: str = ""
    code: str
    expires_in: int


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def create_dashboard_app(
    target: str,
    *,
    client_factory: ClientFactory = WordPressClient,
    pairing_service: PairingService | None = None,
) -> FastAPI:
    app = FastAPI(title="Morpher Dashboard", docs_url=None, redoc_url=None)
    app.state.target = target
    app.state.client_factory = client_factory
    app.state.pairing = pairing_service or PairingService(
        target,
        KeyringCredentialStore(),
        client_factory=client_factory,
    )
    app.state.wordpress_origin = _origin(target)

    if pairing_service is None:
        app.state.pairing.restore_existing_connection()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app.state.wordpress_origin],
        allow_credentials=False,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(_DASHBOARD_ROOT / "static")),
        name="static",
    )

    def render_pairing_requests(request: Request, *, message: str = "") -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="partials/pairing_requests.html",
            context={
                "pairing_requests": app.state.pairing.list_requests(),
                "message": message,
            },
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

    @app.post("/api/pairing/requests")
    def receive_pairing_request(payload: PairingRequestPayload, request: Request) -> JSONResponse:
        origin = request.headers.get("origin", "")
        if origin != app.state.wordpress_origin:
            raise HTTPException(status_code=403, detail="Pairing request origin is not allowed.")
        try:
            pairing = app.state.pairing.receive(payload.model_dump())
        except (ValueError, PairingError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(
            {
                "status": "pending",
                "request_id": pairing.request_id,
                "ref_no": pairing.ref_no,
            }
        )

    @app.get("/pairing/requests", response_class=HTMLResponse)
    def pairing_requests(request: Request) -> HTMLResponse:
        return render_pairing_requests(request)

    @app.post("/pairing/requests/{request_id}/accept", response_class=HTMLResponse)
    def accept_pairing(request_id: str, request: Request) -> HTMLResponse:
        message = ""
        try:
            pairing = app.state.pairing.accept(request_id)
            message = f"{pairing.ref_no} connected."
            if pairing.error:
                message = f"{message} {pairing.error}"
        except PairingError as exc:
            message = str(exc)
        return render_pairing_requests(request, message=message)

    @app.post("/pairing/requests/{request_id}/reject", response_class=HTMLResponse)
    def reject_pairing(request_id: str, request: Request) -> HTMLResponse:
        message = ""
        try:
            pairing = app.state.pairing.reject(request_id)
            message = f"{pairing.ref_no} rejected."
        except PairingError as exc:
            message = str(exc)
        return render_pairing_requests(request, message=message)

    return app
