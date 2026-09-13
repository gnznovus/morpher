from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from morpher.credentials import CredentialStore, CredentialStoreError, KeyringCredentialStore
from morpher.storage.paths import StoragePaths
from morpher.targets import resolve_target_url
from morpher.wordpress import WordPressClient, WordPressClientError


class DeploymentError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeploymentCandidate:
    name: str
    path: Path
    title: str
    slug: str


@dataclass(frozen=True)
class DeploymentPackage:
    ref_no: str
    manifest: dict[str, object]
    template: dict[str, object]
    assets: list[dict[str, str]]


@dataclass(frozen=True)
class DeployResult:
    template: Path
    status: str
    ref_no: str = ""
    deployment: str = ""
    error: str | None = None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "morpher-template"


def _ref_no() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"MRF-{raw[:4]}-{raw[4:]}"


def _template_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentError(f"Could not read Elementor template {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
        raise DeploymentError(f"Invalid Elementor template payload: {path}")
    return payload


def _candidate_names(value: str) -> tuple[str, ...]:
    name = Path(value).name
    candidates: list[str] = [name]
    if not name.lower().endswith(".json"):
        candidates.extend((f"{name}.json", f"{name}_template.json"))
    elif not name.lower().endswith("_template.json"):
        candidates.append(f"{name[:-5]}_template.json")
    return tuple(dict.fromkeys(candidates))


def resolve_template_target(value: str | Path, storage: StoragePaths | None = None) -> Path:
    storage = storage or StoragePaths()
    root = storage.output_elementor.resolve()
    raw = Path(value)

    candidates: list[Path] = []
    if raw.parent != Path("."):
        candidates.extend(raw.parent / name for name in _candidate_names(raw.name))
    else:
        candidates.extend(root / name for name in _candidate_names(raw.name))

    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved

    raise DeploymentError(f"Elementor template not found under {storage.output_elementor}: {value}")


def discover_templates(storage: StoragePaths | None = None) -> list[Path]:
    storage = storage or StoragePaths()
    if not storage.output_elementor.exists():
        return []
    return sorted(
        path.resolve()
        for path in storage.output_elementor.glob("*_template.json")
        if path.is_file()
    )


def deployment_candidates(storage: StoragePaths | None = None) -> tuple[DeploymentCandidate, ...]:
    storage = storage or StoragePaths()
    items: list[DeploymentCandidate] = []
    for path in discover_templates(storage):
        try:
            payload = _template_payload(path)
        except DeploymentError:
            continue
        stem = path.stem.removesuffix("_template")
        items.append(
            DeploymentCandidate(
                name=path.name,
                path=path,
                title=str(payload.get("title") or stem),
                slug=_slugify(stem),
            )
        )
    return tuple(items)


def _asset_dir_for_template(template: Path, storage: StoragePaths) -> Path:
    stem = template.stem.removesuffix("_template")
    return storage.output_elementor / "assets" / stem


def _asset_payload(asset_dir: Path) -> list[dict[str, str]]:
    if not asset_dir.exists():
        return []
    assets: list[dict[str, str]] = []
    for path in sorted(item for item in asset_dir.rglob("*") if item.is_file()):
        raw = path.read_bytes()
        assets.append(
            {
                "path": path.relative_to(asset_dir).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content": base64.b64encode(raw).decode("ascii"),
            }
        )
    return assets


def build_deployment_package(
    template: Path,
    storage: StoragePaths | None = None,
    *,
    force: bool = False,
) -> DeploymentPackage:
    storage = storage or StoragePaths()
    payload = _template_payload(template)
    stem = template.stem.removesuffix("_template")
    slug = _slugify(stem)
    title = str(payload.get("title") or stem)
    asset_dir = _asset_dir_for_template(template, storage)
    assets = _asset_payload(asset_dir)

    digest = hashlib.sha256(template.read_bytes())
    for asset in assets:
        digest.update(asset["path"].encode("utf-8"))
        digest.update(asset["sha256"].encode("ascii"))

    manifest: dict[str, object] = {
        "schema_version": 1,
        "title": title,
        "slug": slug,
        "type": str(payload.get("type") or "container"),
        "build_hash": digest.hexdigest(),
        "force": force,
        "asset_root": f"assets/{stem}",
    }
    return DeploymentPackage(
        ref_no=_ref_no(),
        manifest=manifest,
        template=payload,
        assets=assets,
    )


def stage_template(
    template: Path,
    target_url: str,
    storage: StoragePaths | None = None,
    *,
    force: bool = False,
    credentials: CredentialStore | None = None,
    client_factory=WordPressClient,
) -> DeployResult:
    storage = storage or StoragePaths()
    credentials = credentials or KeyringCredentialStore()
    try:
        package = build_deployment_package(template, storage, force=force)
        token = credentials.get(target_url)
        if not token:
            raise DeploymentError("This WordPress site is not paired with Morpher.")
        result = client_factory(target_url, token=token).stage_deployment(
            ref_no=package.ref_no,
            manifest=package.manifest,
            template=package.template,
            assets=package.assets,
        )
        return DeployResult(
            template=template,
            status=str(result.get("status") or "staged"),
            ref_no=str(result.get("ref_no") or package.ref_no),
            deployment=str(result.get("deployment") or package.manifest["slug"]),
        )
    except (DeploymentError, CredentialStoreError, ValueError, WordPressClientError, OSError) as exc:
        return DeployResult(template=template, status="failed", error=str(exc))


def deploy_all(
    target: str | Path | None = None,
    *,
    target_url: str,
    force: bool = False,
    storage: StoragePaths | None = None,
    credentials: CredentialStore | None = None,
    client_factory=WordPressClient,
) -> list[DeployResult]:
    storage = storage or StoragePaths()
    storage.ensure()
    try:
        templates = [resolve_template_target(target, storage)] if target is not None else discover_templates(storage)
    except DeploymentError as exc:
        return [DeployResult(template=Path(target or ""), status="failed", error=str(exc))]
    return [
        stage_template(
            template,
            target_url,
            storage,
            force=force,
            credentials=credentials,
            client_factory=client_factory,
        )
        for template in templates
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage Morpher Elementor templates and assets through the WordPress REST connection."
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Elementor template filename, basename, or path under output/elementor. Omit for bulk staging.",
    )
    parser.add_argument(
        "--site",
        dest="site_url",
        help="Connected WordPress site URL. Required until a working site is configured.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Stage the deployment even when it has the same build hash as an existing staged package.",
    )
    args = parser.parse_args(argv)

    try:
        target_url = resolve_target_url(args.site_url)
    except ValueError as exc:
        parser.error(str(exc))
        return

    results = deploy_all(args.target, target_url=target_url, force=args.force)
    if not results:
        print("No Elementor templates found.")
        return

    for result in results:
        if result.status == "staged":
            print(f"STAGED   {result.template}  {result.ref_no}")
        elif result.status == "skipped":
            print(f"SKIP     {result.template}  already staged")
        else:
            print(f"FAILED   {result.template}  {result.error}")

    staged = sum(result.status == "staged" for result in results)
    skipped = sum(result.status == "skipped" for result in results)
    failed = sum(result.status == "failed" for result in results)
    print(f"\nResult: staged={staged} skipped={skipped} failed={failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
