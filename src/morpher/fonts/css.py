from __future__ import annotations

from pathlib import Path
from shutil import copy2

from morpher.fonts.model import FontFace, FontSource
from morpher.fonts.resolver import FontResolution


_FORMAT_LABELS = {
    "woff2": "woff2",
    "woff": "woff",
    "otf": "opentype",
    "ttf": "truetype",
    "eot": "embedded-opentype",
}


def package_font_face(face: FontFace, destination: Path) -> dict[FontSource, Path]:
    """Copy a resolved logical face into a Native output font directory."""
    destination.mkdir(parents=True, exist_ok=True)
    packaged: dict[FontSource, Path] = {}
    used_names: set[str] = set()

    for source in face.web_sources():
        name = source.path.name
        if name in used_names:
            name = f"{source.path.stem}-{source.format}{source.path.suffix}"
        used_names.add(name)
        target = destination / name
        copy2(source.path, target)
        packaged[source] = target

    return packaged


def render_font_resolution_css(
    resolution: FontResolution,
    *,
    packaged_sources: dict[FontSource, Path] | None = None,
    css_dir: Path | None = None,
) -> str:
    """Render one resolver result as @font-face CSS plus Morpher diagnostics."""
    if resolution.face is None:
        return _missing_comment(resolution)

    face = resolution.face
    sources = []
    for source in face.web_sources():
        target = packaged_sources.get(source, source.path) if packaged_sources else source.path
        url = _css_url(target, css_dir)
        label = _FORMAT_LABELS.get(source.format, source.format)
        sources.append(f'url("{url}") format("{label}")')

    src = ",\n    ".join(sources)
    lines = [
        "@font-face {",
        f'  font-family: "{_escape(face.family)}";',
        "  src:",
        f"    {src};",
        f"  font-weight: {face.weight};",
        f"  font-style: {face.style};",
        "}",
        "",
        _resolution_comment(resolution),
    ]
    return "\n".join(lines) + "\n"


def _resolution_comment(resolution: FontResolution) -> str:
    request = resolution.request
    requested = f"{request.family} / {request.weight} / {request.style}"
    if request.flavor:
        requested += f" / {request.flavor}"

    if resolution.provenance == "cache_hit":
        detail = "registry cache hit"
    elif resolution.provenance == "resolved_after_refresh":
        detail = "resolved after registry refresh"
    elif resolution.provenance == "fallback_after_refresh":
        face = resolution.face
        assert face is not None
        chosen = f"{face.family} / {face.weight} / {face.style}"
        if face.flavor:
            chosen += f" / {face.flavor}"
        detail = f"fallback after registry refresh → {chosen}"
    else:
        detail = resolution.status
    return f"/* MORPHER FONT: {requested} → {detail} */"


def _missing_comment(resolution: FontResolution) -> str:
    request = resolution.request
    lines = [
        "/* MORPHER WARNING: font not found after registry refresh",
        f' * family: "{request.family}"',
        f" * weight: {request.weight}",
        f" * style: {request.style}",
    ]
    if request.flavor:
        lines.append(f" * flavor: {request.flavor}")
    lines.append(" */")
    return "\n".join(lines) + "\n"


def _css_url(path: Path, css_dir: Path | None) -> str:
    if css_dir is None:
        return path.as_posix()
    try:
        return path.relative_to(css_dir).as_posix()
    except ValueError:
        import os

        return Path(os.path.relpath(path, css_dir)).as_posix()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
