from __future__ import annotations

import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from morpher.targets import normalize_target_url
from morpher.wordpress.models import WordPressDeployment, WordPressHealth


class WordPressClientError(RuntimeError):
    pass


class WordPressClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("WordPress base URL is required.")
        self.base_url = normalize_target_url(base_url)
        self.token = token.strip() if token else None
        self.timeout = timeout

    def health(self) -> WordPressHealth:
        payload = self._request_json("GET", "/wp-json/morpher/v1/health")
        return WordPressHealth.from_dict(payload)

    def pair(self, code: str) -> str:
        code = code.strip()
        if len(code) != 6 or not code.isdigit():
            raise ValueError("Morpher pairing code must contain exactly six digits.")

        token = secrets.token_urlsafe(32)
        self._request_json(
            "POST",
            "/wp-json/morpher/v1/pairing/complete",
            payload={"code": code, "token": token},
        )
        self.token = token
        return token

    def deployments(self) -> tuple[WordPressDeployment, ...]:
        payload = self._request_json(
            "GET",
            "/wp-json/morpher/v1/deployments",
            authenticated=True,
        )
        rows = payload.get("deployments") or []
        if not isinstance(rows, list):
            raise WordPressClientError("WordPress returned an invalid deployments response.")

        return tuple(
            WordPressDeployment.from_dict(row)
            for row in rows
            if isinstance(row, dict)
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, object] | None = None,
        authenticated: bool = False,
    ) -> dict[str, object]:
        headers = {"Accept": "application/json"}
        data = None

        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")

        if authenticated:
            if not self.token:
                raise WordPressClientError("This WordPress client is not paired with Morpher.")
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers=headers,
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise WordPressClientError(
                f"WordPress request failed with HTTP {exc.code}: {request.full_url}"
            ) from exc
        except URLError as exc:
            raise WordPressClientError(
                f"Could not connect to WordPress at {self.base_url}: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise WordPressClientError(
                f"Could not connect to WordPress at {self.base_url}: {exc}"
            ) from exc

        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise WordPressClientError(
                f"WordPress returned invalid JSON from {request.full_url}."
            ) from exc

        if not isinstance(decoded, dict):
            raise WordPressClientError(
                f"WordPress returned an unexpected response from {request.full_url}."
            )

        return decoded
