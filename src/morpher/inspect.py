from __future__ import annotations

import argparse
from pathlib import Path

from morpher.compiler.normalizer import normalize
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.ir.nodes import DesignNode


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


def inspect_path(path: Path) -> str:
    adapter = FigmaJsonAdapter()
    source = adapter.load(path)
    document = normalize(source)

    lines = [f"Morpher IR: {path}", ""]
    lines.extend(_tree_lines(document.root))

    if document.warnings:
        lines.extend(["", f"Warnings ({len(document.warnings)}):"])
        lines.extend(f"- {warning}" for warning in document.warnings)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Morpher Design IR tree.")
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    args = parser.parse_args()

    try:
        print(inspect_path(args.path))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
