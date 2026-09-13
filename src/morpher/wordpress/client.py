from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from morpher.targets import normalize_target_url
from morpher.wordpress.models import WordPressHealth


class WordPressClientError(RuntimeError):
    pass


class WordPressClient:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self.base_url = normalize_target_url(base_url)
        self.timeout = timeout

    def health(self) -> WordPressHealth:
        payload = self._get_json("/wp-json/morpher/v1/health")
        return WordPressHealth.from_dict(payload)

    def _get_json(self, path: str) -> dict[str, object]:
        request = Request(
            f"{self.base_url}{path}",
            method="GET",
            headers={"Accept": "application/json"},
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
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise WordPressClientError(
                f"WordPress returned invalid JSON from {request.full_url}."
            ) from exc

        if not isinstance(payload, dict):
            raise WordPressClientError(
                f"WordPress returned an unexpected response from {request.full_url}."
            )

        return payload
