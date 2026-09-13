from __future__ import annotations

import base64
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
    asset_count: int = 0
    asset_url: str = ""


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

    def _assets_for(self, candidate: TemplateCandidate) -> tuple[list[dict[str, str]], str]:
        stem = candidate.path.stem.removesuffix("_template")
        root = self.storage.output_elementor / "assets" / stem
        if not root.exists():
            return [], f"assets/{stem}"

        assets: list[dict[str, str]] = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            raw = path.read_bytes()
            assets.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "content": base64.b64encode(raw).decode("ascii"),
                }
            )
        return assets, f"assets/{stem}"

    def deploy(self, template_name: str) -> TemplateDeploymentResult:
        candidate = next((item for item in self.templates() if item.name == template_name), None)
        if candidate is None:
            raise RemoteDeploymentError("Elementor template was not found in Morpher output.")

        try:
            raw = candidate.path.read_bytes()
            template = json.loads(raw.decode("utf-8"))
            assets, asset_root = self._assets_for(candidate)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RemoteDeploymentError(f"Could not read Elementor deployment: {exc}") from exc

        try:
            token = self.credentials.get(self.target)
        except CredentialStoreError as exc:
            raise RemoteDeploymentError(str(exc)) from exc
        if not token:
            raise RemoteDeploymentError("This WordPress site is not paired with Morpher.")

        ref_no = _ref_no()
        digest = hashlib.sha256(raw)
        for asset in assets:
            digest.update(asset["path"].encode("utf-8"))
            digest.update(asset["sha256"].encode("ascii"))
        build_hash = digest.hexdigest()
        client = self.client_factory(self.target, token=token)

        try:
            result = client.deploy_template(
                slug=candidate.slug,
                title=candidate.title,
                build_hash=build_hash,
                template=template,
                ref_no=ref_no,
                asset_root=asset_root,
                assets=assets,
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
            asset_count=int(result.get("asset_count") or 0),
            asset_url=str(result.get("asset_url") or ""),
        )
