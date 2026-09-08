from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from morpher.compiler.normalizer import normalize
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode
from morpher.trace import Trace


def _label(node: DesignNode) -> str:
    name = node.name or "(unnamed)"
    parts = [f"{name} [{node.kind}]"]

    if node.style.width is not None and node.style.height is not None:
        parts.append(f"{node.style.width:g}x{node.style.height:g}")

    if node.kind == "text" and node.text is not None:
        parts.append(repr(node.text))

    if node.kind == "image" and node.image_ref:
        parts.append(f"imageRef={node.image_ref}")

    return " ".join(parts)


def _tree_lines(node: DesignNode, prefix: str = "", is_last: bool = True, root: bool = True) -> list[str]:
    connector = "" if root else ("└─ " if is_last else "├─ ")
    lines = [f"{prefix}{connector}{_label(node)}"]
    child_prefix = prefix if root else prefix + ("   " if is_last else "│  ")

    for index, child in enumerate(node.children):
        lines.extend(
            _tree_lines(
                child,
                prefix=child_prefix,
                is_last=index == len(node.children) - 1,
                root=False,
            )
        )
    return lines


def _walk(node: DesignNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _summary_lines(root: DesignNode, warning_count: int) -> list[str]:
    nodes = list(_walk(root))
    kinds = Counter(node.kind for node in nodes)
    source_types = Counter(node.source_type or "UNKNOWN" for node in nodes)

    lines = [
        f"Total nodes: {len(nodes)}",
        f"Warnings: {warning_count}",
        "Kinds: " + ", ".join(f"{kind}={count}" for kind, count in sorted(kinds.items())),
        "Source types: "
        + ", ".join(f"{source_type}={count}" for source_type, count in sorted(source_types.items())),
    ]
    return lines


def inspect_path(path: Path) -> tuple[str, Path]:
    adapter = FigmaJsonAdapter()
    source = adapter.load(path)
    document = normalize(source)

    trace = Trace(path)
    trace.section("SUMMARY")
    trace.extend(_summary_lines(document.root, len(document.warnings)))

    trace.section("DESIGN IR")
    trace.extend(_tree_lines(document.root))

    if document.warnings:
        trace.section(f"WARNINGS ({len(document.warnings)})")
        trace.extend(f"- {warning}" for warning in document.warnings)

    output = trace.write()
    return trace.render(), output


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Morpher Design IR tree.")
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    args = parser.parse_args()

    try:
        text, output = inspect_path(args.path)
        print(text, end="")
        print(f"Trace saved: {output}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
