from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from morpher.inspect import inspect_path
from morpher.render import RenderOutputs, render_path
from morpher.storage.paths import StoragePaths
from morpher.storage.scanner import scan_sources


@dataclass(frozen=True)
class RunResult:
    source: Path
    status: str
    warnings: int = 0
    error: str | None = None
    outputs: RenderOutputs | None = None


def _outputs_exist(source: Path, storage: StoragePaths) -> bool:
    """A source is processed only when all currently required outputs exist."""
    return (
        storage.fidelity_html_output(source).exists()
        and storage.fidelity_css_output(source).exists()
        and storage.native_html_output(source).exists()
        and storage.native_css_output(source).exists()
        and storage.elementor_output(source).exists()
    )


def _existing_outputs(source: Path, storage: StoragePaths) -> RenderOutputs:
    return RenderOutputs(
        fidelity_html=storage.fidelity_html_output(source),
        fidelity_css=storage.fidelity_css_output(source),
        native_html=storage.native_html_output(source),
        native_css=storage.native_css_output(source),
        elementor=storage.elementor_output(source),
        warning_count=0,
    )


def _print_outputs(outputs: RenderOutputs) -> None:
    if outputs.fidelity_html is not None:
        print(f"  Fidelity HTML: {outputs.fidelity_html}")
    if outputs.fidelity_css is not None:
        print(f"  Fidelity CSS:  {outputs.fidelity_css}")
    if outputs.native_html is not None:
        print(f"  Native HTML:   {outputs.native_html}")
    if outputs.native_css is not None:
        print(f"  Native CSS:    {outputs.native_css}")
    print(f"  Elementor:     {outputs.elementor}")


def _font_warning_message(css_comment: str) -> str:
    warning = css_comment.strip()
    if warning.startswith("/*") and warning.endswith("*/"):
        warning = warning[2:-2].strip()
    return warning


def _source_candidate_names(value: str) -> tuple[str, ...]:
    name = Path(value).name
    candidates = [name]
    if not name.lower().endswith(".json"):
        candidates.append(f"{name}.json")
    return tuple(dict.fromkeys(candidates))


def _allowed_source_roots(storage: StoragePaths) -> tuple[Path, Path]:
    return storage.figma_import.resolve(), storage.input.resolve()


def _source_path_candidates(value: str | Path, storage: StoragePaths) -> list[Path]:
    raw = Path(value)
    names = _source_candidate_names(raw.name)
    figma_root, input_root = _allowed_source_roots(storage)

    if raw.parent == Path("."):
        return [root / name for root in (figma_root, input_root) for name in names]

    candidates: list[Path] = [raw.parent / name for name in names]

    # Friendly storage-root aliases mirror how users refer to Morpher's queues.
    # `figma-import/Foo`, `input/Foo`, and their `storage/...` forms all resolve
    # against the same strict source roots.
    parts = raw.parts
    if parts and parts[0].lower() in {"figma-import", "input"}:
        candidates.extend(storage.root / raw.parent / name for name in names)

    return candidates


def resolve_source_target(value: str | Path, storage: StoragePaths | None = None) -> Path:
    """Resolve a friendly Morpher source target inside figma-import/input only.

    Figma imports keep the same priority as bulk processing. Bare names may omit the
    `.json` extension. Explicit relative paths are accepted only when they resolve
    underneath one of Morpher's source roots.
    """
    storage = storage or StoragePaths()
    roots = _allowed_source_roots(storage)

    for candidate in _source_path_candidates(value, storage):
        resolved = candidate.resolve()
        if not any(_is_within(resolved, root) for root in roots):
            continue
        if resolved.is_file() and resolved.suffix.lower() == ".json":
            return resolved

    raise ValueError(
        f"Morpher source not found under {storage.figma_import} or {storage.input}: {value}"
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
        return RunResult(
            source=source,
            status="skipped",
            outputs=_existing_outputs(source, storage),
        )

    try:
        # Inspect exactly once so the rich diagnostic trace remains the canonical trace.
        inspect_path(source)
        outputs = render_path(source)
        return RunResult(
            source=source,
            status="processed",
            warnings=outputs.warning_count,
            outputs=outputs,
        )
    except (OSError, ValueError) as exc:
        return RunResult(source=source, status="failed", error=str(exc))


def run_all(
    target: str | Path | None = None,
    *,
    force: bool = False,
    storage: StoragePaths | None = None,
) -> list[RunResult]:
    storage = storage or StoragePaths()
    storage.ensure()

    # Font discovery is lazy. The font resolver checks the persisted registry
    # first and only runs the gatherer after a requested face misses the cache.

    if target is not None:
        try:
            sources = [resolve_source_target(target, storage)]
        except ValueError as exc:
            return [RunResult(source=Path(target), status="failed", error=str(exc))]
    else:
        # Preserved Figma imports have priority; generic input remains the second queue.
        sources = scan_sources(
            (storage.figma_import, storage.input),
            (".json",),
        )
    return [run_source(source, storage, force=force) for source in sources]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and render Morpher sources."
    )
    parser.add_argument(
        "target",
        nargs="?",
        help=(
            "Source filename, basename, or path under figma-import/input. "
            "Omit for bulk processing."
        ),
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
        if args.target is not None:
            parser.error("target cannot be used with --clean")
        clean_outputs()
        print("CLEAN    storage/output")
        return

    results = run_all(args.target, force=args.force)
    if not results:
        print("No supported sources found.")
        return

    for result in results:
        if result.status == "processed":
            print(f"PROCESS  {result.source}  warnings={result.warnings}")
            if result.outputs is not None:
                _print_outputs(result.outputs)
        elif result.status == "skipped":
            print(f"SKIP     {result.source}  outputs already exist")
            if result.outputs is not None:
                _print_outputs(result.outputs)
        else:
            print(f"FAILED   {result.source}  {result.error}")

    processed = sum(result.status == "processed" for result in results)
    skipped = sum(result.status == "skipped" for result in results)
    failed = sum(result.status == "failed" for result in results)
    print(f"\nResult: processed={processed} skipped={skipped} failed={failed}")

    font_warnings = sorted(
        {
            _font_warning_message(warning)
            for result in results
            if result.outputs is not None
            for warning in result.outputs.font_warnings
        }
    )
    for warning in font_warnings:
        print(warning)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
