from __future__ import annotations

from typing import Protocol

import keyring

from morpher.targets import normalize_target_url


class CredentialStoreError(RuntimeError):
    pass


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
        try:
            value = keyring.get_password(self.SERVICE, self._key(site_url))
        except keyring.errors.KeyringError as exc:
            raise CredentialStoreError("Could not read the Morpher credential vault.") from exc
        return value.strip() if value else None

    def set(self, site_url: str, token: str) -> None:
        value = token.strip()
        if not value:
            raise ValueError("Morpher credential token cannot be empty.")
        try:
            keyring.set_password(self.SERVICE, self._key(site_url), value)
        except keyring.errors.KeyringError as exc:
            raise CredentialStoreError("Could not write the Morpher credential vault.") from exc

    def delete(self, site_url: str) -> None:
        try:
            keyring.delete_password(self.SERVICE, self._key(site_url))
        except keyring.errors.PasswordDeleteError:
            pass
        except keyring.errors.KeyringError as exc:
            raise CredentialStoreError("Could not update the Morpher credential vault.") from exc
