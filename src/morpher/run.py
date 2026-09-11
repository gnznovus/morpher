from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from morpher.inspect import inspect_path
from morpher.render import render_path
from morpher.storage.paths import StoragePaths
from morpher.storage.scanner import scan_sources


@dataclass(frozen=True)
class RunResult:
    source: Path
    status: str
    warnings: int = 0
    error: str | None = None


def _outputs_exist(source: Path, storage: StoragePaths) -> bool:
    """A source is processed only when all currently required outputs exist."""
    return (
        storage.fidelity_html_output(source).exists()
        and storage.fidelity_css_output(source).exists()
        and storage.native_html_output(source).exists()
        and storage.native_css_output(source).exists()
        and storage.elementor_output(source).exists()
    )


def clean_outputs(storage: StoragePaths | None = None) -> None:
    """Delete generated output only; source/import/processed data is never touched."""
    storage = storage or StoragePaths()
    output_root = storage.root / "output"

    if output_root.exists():
        shutil.rmtree(output_root)

    # Recreate the renderer-owned output structure so the workspace is ready
    # for the next render without touching any source-side storage.
    storage.output_html_fidelity.mkdir(parents=True, exist_ok=True)
    storage.output_html_native.mkdir(parents=True, exist_ok=True)
    storage.output_elementor.mkdir(parents=True, exist_ok=True)


def run_source(source: Path, storage: StoragePaths, *, force: bool = False) -> RunResult:
    if not force and _outputs_exist(source, storage):
        return RunResult(source=source, status="skipped")

    try:
        # Inspect exactly once so the rich diagnostic trace remains the canonical trace.
        inspect_path(source)
        outputs = render_path(source)
        return RunResult(source=source, status="processed", warnings=outputs.warning_count)
    except (OSError, ValueError) as exc:
        return RunResult(source=source, status="failed", error=str(exc))


def run_all(*, force: bool = False, storage: StoragePaths | None = None) -> list[RunResult]:
    storage = storage or StoragePaths()
    storage.ensure()

    # Font discovery is lazy. The font resolver checks the persisted registry
    # first and only runs the gatherer after a requested face misses the cache.

    # Preserved Figma imports have priority; generic input remains the second queue.
    sources = scan_sources(
        (storage.figma_import, storage.input),
        (".json",),
    )
    return [run_source(source, storage, force=force) for source in sources]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and render all pending Morpher sources."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess sources even when their required outputs already exist.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete generated storage/output content only, then exit.",
    )
    args = parser.parse_args()

    if args.clean:
        clean_outputs()
        print("CLEAN    storage/output")
        return

    results = run_all(force=args.force)
    if not results:
        print("No supported sources found.")
        return

    for result in results:
        if result.status == "processed":
            print(f"PROCESS  {result.source}  warnings={result.warnings}")
        elif result.status == "skipped":
            print(f"SKIP     {result.source}  outputs already exist")
        else:
            print(f"FAILED   {result.source}  {result.error}")

    processed = sum(result.status == "processed" for result in results)
    skipped = sum(result.status == "skipped" for result in results)
    failed = sum(result.status == "failed" for result in results)
    print(f"\nResult: processed={processed} skipped={skipped} failed={failed}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
