from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, replace
from datetime import datetime

from morpher.connections import ConnectionRecord, ConnectionStore
from morpher.credentials import CredentialStore, CredentialStoreError
from morpher.targets import normalize_target_url
from morpher.wordpress import WordPressClient, WordPressClientError


class PairingError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingPairingRequest:
    request_id: str
    ref_no: str
    site_url: str
    site_name: str
    plugin_version: str
    wordpress_version: str
    code: str
    created_at: float
    expires_at: float
    status: str = "pending"
    error: str = ""

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at


class PairingRequestStore:
    def __init__(self) -> None:
        self._items: dict[str, PendingPairingRequest] = {}

    def put(self, request: PendingPairingRequest) -> PendingPairingRequest:
        self._items[request.request_id] = request
        return request

    def get(self, request_id: str) -> PendingPairingRequest | None:
        return self._items.get(request_id)

    def replace(self, request: PendingPairingRequest) -> PendingPairingRequest:
        self._items[request.request_id] = request
        return request

    def all(self) -> tuple[PendingPairingRequest, ...]:
        items = []
        for request in self._items.values():
            if request.status == "pending" and request.expired:
                request = self.replace(replace(request, status="expired"))
            items.append(request)
        return tuple(sorted(items, key=lambda item: item.created_at, reverse=True))


class PairingService:
    def __init__(
        self,
        expected_site_url: str,
        credentials: CredentialStore,
        *,
        store: PairingRequestStore | None = None,
        connections: ConnectionStore | None = None,
        client_factory=WordPressClient,
    ) -> None:
        self.expected_site_url = normalize_target_url(expected_site_url)
        self.credentials = credentials
        self.store = store or PairingRequestStore()
        self.connections = connections or ConnectionStore()
        self.client_factory = client_factory

    def restore_existing_connection(self) -> ConnectionRecord | None:
        existing = self.connections.get(self.expected_site_url)
        if existing is not None:
            return existing

        try:
            token = self.credentials.get(self.expected_site_url)
        except CredentialStoreError:
            return None
        if not token:
            return None

        try:
            health = self.client_factory(self.expected_site_url, token=token).health()
        except (ValueError, WordPressClientError):
            return None

        if not health.connection.paired or not health.connection.ref_no:
            return None

        paired_at = time.time()
        raw_paired_at = health.connection.metadata.get("paired_at")
        if isinstance(raw_paired_at, (int, float)):
            paired_at = float(raw_paired_at)
        elif isinstance(raw_paired_at, str) and raw_paired_at.strip():
            try:
                paired_at = datetime.fromisoformat(raw_paired_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass

        record = ConnectionRecord(
            site_url=self.expected_site_url,
            site_name=health.wordpress.site_name,
            ref_no=health.connection.ref_no,
            plugin_version=health.plugin.version or "",
            wordpress_version=health.wordpress.version,
            paired_at=paired_at,
            credential_key=self.expected_site_url,
        )
        return self.connections.upsert(record)

    def receive(self, payload: dict[str, object]) -> PendingPairingRequest:
        request_id = str(payload.get("request_id") or "").strip()
        ref_no = str(payload.get("ref_no") or "").strip().upper()
        site_url = normalize_target_url(str(payload.get("site_url") or ""))
        code = str(payload.get("code") or "").strip()
        expires_in = int(payload.get("expires_in") or 0)

        if site_url != self.expected_site_url:
            raise PairingError("Pairing request does not match the dashboard target site.")
        if not request_id:
            raise PairingError("Pairing request ID is required.")
        if not ref_no.startswith("MRF-"):
            raise PairingError("Morpher pairing Ref No. is invalid.")
        if len(code) != 6 or not code.isdigit():
            raise PairingError("Morpher pairing proof is invalid.")
        if expires_in <= 0 or expires_in > 600:
            raise PairingError("Morpher pairing request expiry is invalid.")

        now = time.time()
        request = PendingPairingRequest(
            request_id=request_id,
            ref_no=ref_no,
            site_url=site_url,
            site_name=str(payload.get("site_name") or "WordPress").strip() or "WordPress",
            plugin_version=str(payload.get("plugin_version") or "").strip(),
            wordpress_version=str(payload.get("wordpress_version") or "").strip(),
            code=code,
            created_at=now,
            expires_at=now + expires_in,
        )
        return self.store.put(request)

    def accept(self, request_id: str) -> PendingPairingRequest:
        request = self._require_pending(request_id)
        token = secrets.token_urlsafe(32)

        try:
            self.credentials.set(request.site_url, token)
        except (ValueError, CredentialStoreError) as exc:
            failed = replace(request, status="error", error=str(exc))
            self.store.replace(failed)
            raise PairingError(str(exc)) from exc

        client = self.client_factory(request.site_url, token=token)

        try:
            client.complete_pairing(
                request.code,
                token,
                request_id=request.request_id,
                ref_no=request.ref_no,
            )
        except (ValueError, WordPressClientError) as exc:
            failed = replace(request, status="error", error=str(exc))
            self.store.replace(failed)
            raise PairingError(str(exc)) from exc

        connected = replace(request, status="connected", code="", error="")
        self.store.replace(connected)
        self.connections.upsert(
            ConnectionRecord(
                site_url=request.site_url,
                site_name=request.site_name,
                ref_no=request.ref_no,
                plugin_version=request.plugin_version,
                wordpress_version=request.wordpress_version,
                paired_at=time.time(),
                credential_key=request.site_url,
            )
        )

        try:
            client.acknowledge(
                request.ref_no,
                event="pairing.completed",
                status="acknowledged",
                metadata={"request_id": request.request_id},
            )
        except WordPressClientError as exc:
            connected = replace(
                connected,
                error=f"Connected, but acknowledgement failed: {exc}",
            )
            self.store.replace(connected)

        return connected

    def reject(self, request_id: str) -> PendingPairingRequest:
        request = self._require_pending(request_id)
        rejected = replace(request, status="rejected", code="")
        return self.store.replace(rejected)

    def list_requests(self) -> tuple[PendingPairingRequest, ...]:
        runtime = list(self.store.all())
        runtime_sites = {request.site_url for request in runtime}

        for connection in self.connections.all():
            if connection.site_url in runtime_sites:
                continue
            runtime.append(
                PendingPairingRequest(
                    request_id=f"connected:{connection.site_url}",
                    ref_no=connection.ref_no,
                    site_url=connection.site_url,
                    site_name=connection.site_name,
                    plugin_version=connection.plugin_version,
                    wordpress_version=connection.wordpress_version,
                    code="",
                    created_at=connection.paired_at,
                    expires_at=connection.paired_at,
                    status="connected",
                )
            )

        return tuple(sorted(runtime, key=lambda item: item.created_at, reverse=True))

    def _require_pending(self, request_id: str) -> PendingPairingRequest:
        request = self.store.get(request_id)
        if request is None:
            raise PairingError("Pairing request was not found.")
        if request.expired:
            self.store.replace(replace(request, status="expired"))
            raise PairingError("Pairing request has expired.")
        if request.status != "pending":
            raise PairingError(f"Pairing request is already {request.status}.")
        return request
