from __future__ import annotations

import argparse
from pathlib import Path

from morpher.compiler.normalizer import normalize
from morpher.inputs.figma_json import FigmaJsonAdapter
from morpher.renderers.css import render_css
from morpher.renderers.html import render_html
from morpher.storage.paths import StoragePaths
from morpher.trace import Trace


def render_path(path: Path) -> tuple[Path, Path, Path]:
    adapter = FigmaJsonAdapter()
    document = normalize(adapter.load(path))

    storage = StoragePaths()
    storage.ensure()
    html_path = storage.html_output(path)
    css_path = storage.css_output(path)

    css = render_css(document.root)
    html = render_html(document.root, stylesheet=css_path.name)

    html_path.write_text(html, encoding="utf-8")
    css_path.write_text(css, encoding="utf-8")

    trace = Trace(path)
    trace.section("HTML RENDER")
    trace.add(f"HTML: {html_path}")
    trace.add(f"CSS: {css_path}")
    trace.add(f"Warnings: {len(document.warnings)}")
    trace.section("RESULT")
    trace.add("HTML/CSS render succeeded")
    trace_path = trace.write()

    return html_path, css_path, trace_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a supported design source to HTML/CSS.")
    parser.add_argument("path", type=Path, help="Path to a supported design source.")
    args = parser.parse_args()

    try:
        html_path, css_path, trace_path = render_path(args.path)
        print(f"HTML: {html_path}")
        print(f"CSS: {css_path}")
        print(f"Trace: {trace_path}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
