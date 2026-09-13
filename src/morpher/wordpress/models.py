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


@dataclass(frozen=True)
class ElementorHealth:
    ready: bool
    version: str | None


@dataclass(frozen=True)
class WordPressIntegrationsHealth:
    elementor: ElementorHealth


@dataclass(frozen=True)
class WordPressHealth:
    status: str
    service: str
    api_version: str
    plugin: WordPressPluginHealth
    wordpress: WordPressSiteHealth
    integrations: WordPressIntegrationsHealth
    capabilities: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WordPressHealth":
        plugin = payload.get("plugin") or {}
        wordpress = payload.get("wordpress") or {}
        integrations = payload.get("integrations") or {}
        elementor = integrations.get("elementor") or {}
        capabilities = payload.get("capabilities") or []

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
            ),
            integrations=WordPressIntegrationsHealth(
                elementor=ElementorHealth(
                    ready=bool(elementor.get("ready", False)),
                    version=str(elementor["version"]) if elementor.get("version") is not None else None,
                ),
            ),
            capabilities=tuple(str(value) for value in capabilities),
        )
