from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WordPressPluginHealth:
    version: str | None


@dataclass(frozen=True)
class WordPressSiteHealth:
    version: str
    site_url: str
    site_name: str


@dataclass(frozen=True)
class ElementorHealth:
    ready: bool
    version: str | None


@dataclass(frozen=True)
class WordPressIntegrationsHealth:
    elementor: ElementorHealth


@dataclass(frozen=True)
class WordPressConnectionHealth:
    paired: bool
    ref_no: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class WordPressHealth:
    status: str
    service: str
    api_version: str
    plugin: WordPressPluginHealth
    wordpress: WordPressSiteHealth
    integrations: WordPressIntegrationsHealth
    connection: WordPressConnectionHealth
    capabilities: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WordPressHealth":
        plugin = payload.get("plugin") or {}
        wordpress = payload.get("wordpress") or {}
        integrations = payload.get("integrations") or {}
        elementor = integrations.get("elementor") or {}
        connection = payload.get("connection") or {}
        capabilities = payload.get("capabilities") or []
        metadata = connection.get("metadata") or {}

        return cls(
            status=str(payload.get("status") or ""),
            service=str(payload.get("service") or ""),
            api_version=str(payload.get("api_version") or ""),
            plugin=WordPressPluginHealth(
                version=str(plugin["version"]) if plugin.get("version") is not None else None,
            ),
            wordpress=WordPressSiteHealth(
                version=str(wordpress.get("version") or ""),
                site_url=str(wordpress.get("site_url") or ""),
                site_name=str(wordpress.get("site_name") or "WordPress"),
            ),
            integrations=WordPressIntegrationsHealth(
                elementor=ElementorHealth(
                    ready=bool(elementor.get("ready", False)),
                    version=str(elementor["version"]) if elementor.get("version") is not None else None,
                ),
            ),
            connection=WordPressConnectionHealth(
                paired=bool(connection.get("paired", False)),
                ref_no=str(connection.get("ref_no") or "").strip().upper(),
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
            ),
            capabilities=tuple(str(value) for value in capabilities),
        )


@dataclass(frozen=True)
class WordPressDeployment:
    deployment: str
    slug: str
    title: str
    status: str
    template_id: int
    error: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WordPressDeployment":
        return cls(
            deployment=str(payload.get("deployment") or ""),
            slug=str(payload.get("slug") or ""),
            title=str(payload.get("title") or ""),
            status=str(payload.get("status") or ""),
            template_id=int(payload.get("template_id") or 0),
            error=str(payload.get("error") or ""),
        )
