from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from morpher.credentials import CredentialStore, CredentialStoreError, KeyringCredentialStore
from morpher.storage.paths import StoragePaths
from morpher.wordpress import WordPressClient, WordPressClientError


class RemoteDeploymentError(RuntimeError):
    pass


@dataclass(frozen=True)
class TemplateCandidate:
    name: str
    path: Path
    title: str
    slug: str


@dataclass(frozen=True)
class TemplateDeploymentResult:
    status: str
    ref_no: str
    slug: str
    title: str
    template_id: int
    build_hash: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "morpher-template"


def _ref_no() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"MRF-{raw[:4]}-{raw[4:]}"


class RemoteTemplateDeploymentService:
    def __init__(
        self,
        target: str,
        *,
        credentials: CredentialStore | None = None,
        storage: StoragePaths | None = None,
        client_factory=WordPressClient,
    ) -> None:
        self.target = target
        self.credentials = credentials or KeyringCredentialStore()
        self.storage = storage or StoragePaths()
        self.client_factory = client_factory

    def templates(self) -> tuple[TemplateCandidate, ...]:
        root = self.storage.output_elementor
        if not root.exists():
            return ()

        items: list[TemplateCandidate] = []
        for path in sorted(root.glob("*_template.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
                continue
            stem = path.stem.removesuffix("_template")
            items.append(
                TemplateCandidate(
                    name=path.name,
                    path=path,
                    title=str(payload.get("title") or stem),
                    slug=_slugify(stem),
                )
            )
        return tuple(items)

    def deploy(self, template_name: str) -> TemplateDeploymentResult:
        candidate = next((item for item in self.templates() if item.name == template_name), None)
        if candidate is None:
            raise RemoteDeploymentError("Elementor template was not found in Morpher output.")

        try:
            raw = candidate.path.read_bytes()
            template = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RemoteDeploymentError(f"Could not read Elementor template: {exc}") from exc

        try:
            token = self.credentials.get(self.target)
        except CredentialStoreError as exc:
            raise RemoteDeploymentError(str(exc)) from exc
        if not token:
            raise RemoteDeploymentError("This WordPress site is not paired with Morpher.")

        ref_no = _ref_no()
        build_hash = hashlib.sha256(raw).hexdigest()
        client = self.client_factory(self.target, token=token)

        try:
            result = client.deploy_template(
                slug=candidate.slug,
                title=candidate.title,
                build_hash=build_hash,
                template=template,
                ref_no=ref_no,
            )
        except (ValueError, WordPressClientError) as exc:
            raise RemoteDeploymentError(str(exc)) from exc

        return TemplateDeploymentResult(
            status=str(result.get("status") or ""),
            ref_no=str(result.get("ref_no") or ref_no),
            slug=str(result.get("slug") or candidate.slug),
            title=str(result.get("title") or candidate.title),
            template_id=int(result.get("template_id") or 0),
            build_hash=str(result.get("build_hash") or build_hash),
        )
