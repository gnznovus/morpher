from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_ROOT = REPO_ROOT / "storage"
DEFAULT_DEPLOYMENTS_ROOT = REPO_ROOT / "wp-content" / "plugins" / "morpher-plugin" / "deployments"


def _identity(value: str) -> str:
    name = Path(value).name
    stem = Path(name).stem
    lower = stem.lower()
    for suffix in ("_template", "-template", "_p", "-p"):
        if lower.endswith(suffix):
            stem = stem[: -len(suffix)]
            lower = stem.lower()
            break
    return re.sub(r"[^a-z0-9]+", "", lower)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _matching_paths(root: Path, target: str) -> list[Path]:
    wanted = _identity(target)
    if not wanted or not root.exists():
        return []

    matches: list[Path] = []

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
            if not _inside(child, root):
                continue
            if _identity(child.name) == wanted:
                matches.append(child)
                continue
            if child.is_dir() and not child.is_symlink():
                walk(child)

    walk(root)
    return matches


def _remove_path(path: Path, root: Path) -> None:
    if not _inside(path, root):
        raise ValueError(f"Refusing to remove path outside managed root: {path}")
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def remove_target(
    target: str,
    *,
    storage_root: Path = DEFAULT_STORAGE_ROOT,
    deployments_root: Path = DEFAULT_DEPLOYMENTS_ROOT,
) -> list[Path]:
    removed: list[Path] = []
    for root in (storage_root, deployments_root):
        for path in _matching_paths(root, target):
            _remove_path(path, root)
            removed.append(path)
    return removed


def remove_all(
    *,
    storage_root: Path = DEFAULT_STORAGE_ROOT,
    deployments_root: Path = DEFAULT_DEPLOYMENTS_ROOT,
) -> list[Path]:
    removed: list[Path] = []
    for root in (storage_root, deployments_root):
        if not root.exists():
            continue
        for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            if not _inside(child, root):
                continue
            _remove_path(child, root)
            removed.append(child)
    return removed


def _print_removed(paths: list[Path]) -> None:
    if not paths:
        print("Nothing matched. No files were removed.")
        return
    for path in paths:
        print(f"REMOVED  {path}")
    print(f"\nRemoved {len(paths)} path{'s' if len(paths) != 1 else ''}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="morpher-rm",
        description="Remove Morpher-managed artifacts from storage and staged deployments only.",
    )
    parser.add_argument("target", nargs="?", help="Source/template name to remove everywhere Morpher manages it.")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="remove_everything",
        help="Remove all contents of Morpher storage and deployments after interactive confirmation.",
    )
    args = parser.parse_args()

    if args.remove_everything and args.target:
        parser.error("target and --all cannot be used together")
    if not args.remove_everything and not args.target:
        parser.print_help()
        return

    if args.remove_everything:
        print("This will remove ALL Morpher-managed files from:")
        print(f"  {DEFAULT_STORAGE_ROOT}")
        print(f"  {DEFAULT_DEPLOYMENTS_ROOT}")
        answer = input("\nContinue? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled. Nothing was removed.")
            return
        _print_removed(remove_all())
        return

    _print_removed(remove_target(args.target))


if __name__ == "__main__":
    main()
