from __future__ import annotations

from typing import Protocol

import keyring

from morpher.targets import normalize_target_url


class CredentialStore(Protocol):
    def get(self, site_url: str) -> str | None: ...

    def set(self, site_url: str, token: str) -> None: ...

    def delete(self, site_url: str) -> None: ...


class KeyringCredentialStore:
    """Store Morpher site credentials in the operating system credential vault."""

    SERVICE = "morpher"

    def _key(self, site_url: str) -> str:
        return normalize_target_url(site_url)

    def get(self, site_url: str) -> str | None:
        value = keyring.get_password(self.SERVICE, self._key(site_url))
        return value.strip() if value else None

    def set(self, site_url: str, token: str) -> None:
        value = token.strip()
        if not value:
            raise ValueError("Morpher credential token cannot be empty.")
        keyring.set_password(self.SERVICE, self._key(site_url), value)

    def delete(self, site_url: str) -> None:
        try:
            keyring.delete_password(self.SERVICE, self._key(site_url))
        except keyring.errors.PasswordDeleteError:
            pass
