from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from morpher.storage.paths import StoragePaths


@dataclass(frozen=True)
class DeployResult:
    template: Path
    status: str
    deployment: Path | None = None
    error: str | None = None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "morpher-template"


def _template_identity(path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Elementor template {path}: {exc}") from exc

    title = str(payload.get("title") or path.stem.removesuffix("_template"))
    slug = _slugify(path.stem.removesuffix("_template"))
    return title, slug


def _candidate_names(value: str) -> tuple[str, ...]:
    name = Path(value).name
    candidates: list[str] = [name]
    if not name.lower().endswith(".json"):
        candidates.extend((f"{name}.json", f"{name}_template.json"))
    elif not name.lower().endswith("_template.json"):
        candidates.append(f"{name[:-5]}_template.json")
    return tuple(dict.fromkeys(candidates))


def resolve_template_target(value: str | Path, storage: StoragePaths | None = None) -> Path:
    """Resolve a filename or path to one template inside output/elementor only."""
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

    raise ValueError(f"Elementor template not found under {storage.output_elementor}: {value}")


def discover_templates(storage: StoragePaths | None = None) -> list[Path]:
    storage = storage or StoragePaths()
    if not storage.output_elementor.exists():
        return []
    return sorted(
        path.resolve()
        for path in storage.output_elementor.glob("*_template.json")
        if path.is_file()
    )


def _asset_dir_for_template(template: Path, storage: StoragePaths) -> Path:
    stem = template.stem.removesuffix("_template")
    return storage.output_elementor / "assets" / stem


def _build_hash(template: Path, asset_dir: Path) -> str:
    digest = hashlib.sha256()
    digest.update(template.read_bytes())
    if asset_dir.exists():
        for asset in sorted(path for path in asset_dir.rglob("*") if path.is_file()):
            digest.update(asset.relative_to(asset_dir).as_posix().encode("utf-8"))
            digest.update(asset.read_bytes())
    return digest.hexdigest()


def _deployment_root(storage: StoragePaths) -> Path:
    return storage.elementor_font_plugin / "deployments"


def stage_template(
    template: Path,
    storage: StoragePaths | None = None,
    *,
    force: bool = False,
) -> DeployResult:
    storage = storage or StoragePaths()
    try:
        title, slug = _template_identity(template)
        asset_dir = _asset_dir_for_template(template, storage)
        build_hash = _build_hash(template, asset_dir)
        deployment = _deployment_root(storage) / slug
        manifest_path = deployment / "manifest.json"

        if not force and manifest_path.exists():
            try:
                current = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if current.get("build_hash") == build_hash:
                return DeployResult(template=template, status="skipped", deployment=deployment)

        if deployment.exists():
            shutil.rmtree(deployment)
        deployment.mkdir(parents=True, exist_ok=True)

        shutil.copy2(template, deployment / "template.json")
        if asset_dir.exists():
            shutil.copytree(asset_dir, deployment / "assets")

        asset_root = f"assets/{template.stem.removesuffix('_template')}"
        manifest = {
            "schema_version": 1,
            "title": title,
            "slug": slug,
            "type": "container",
            "build_hash": build_hash,
            "force": force,
            "asset_root": asset_root,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return DeployResult(template=template, status="staged", deployment=deployment)
    except (OSError, ValueError) as exc:
        return DeployResult(template=template, status="failed", error=str(exc))


def deploy_all(
    target: str | Path | None = None,
    *,
    force: bool = False,
    storage: StoragePaths | None = None,
) -> list[DeployResult]:
    storage = storage or StoragePaths()
    storage.ensure()
    try:
        templates = [resolve_template_target(target, storage)] if target is not None else discover_templates(storage)
    except ValueError as exc:
        return [DeployResult(template=Path(target or ""), status="failed", error=str(exc))]
    return [stage_template(template, storage, force=force) for template in templates]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage Morpher Elementor templates and assets for WordPress deployment."
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Elementor template filename, basename, or path under output/elementor. Omit for bulk deploy.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Restage templates even when the same build is already staged/deployed.",
    )
    args = parser.parse_args()

    results = deploy_all(args.target, force=args.force)
    if not results:
        print("No Elementor templates found.")
        return

    for result in results:
        if result.status == "staged":
            print(f"DEPLOY   {result.template}  staged for WordPress")
        elif result.status == "skipped":
            print(f"SKIP     {result.template}  already staged/deployed")
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
