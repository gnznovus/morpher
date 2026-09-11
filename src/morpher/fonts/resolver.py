from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from morpher.fonts.metadata import read_font_metadata
from morpher.fonts.model import FontFace
from morpher.fonts.registry import (
    FontRegistry,
    MetadataReader,
    current_font_registry,
    load_cached_font_registry,
    refresh_font_registry,
)
from morpher.ir.typography import FontIntent


ResolutionStatus = Literal["exact", "fallback", "missing"]
LookupProvenance = Literal[
    "cache_hit",
    "resolved_after_refresh",
    "fallback_after_refresh",
    "missing_after_refresh",
]


@dataclass(frozen=True)
class FontRequest:
    family: str
    weight: int
    style: str = "normal"
    flavor: str | None = None


@dataclass(frozen=True)
class FontResolution:
    status: ResolutionStatus
    request: FontRequest
    face: FontFace | None = None
    reason: str | None = None
    provenance: LookupProvenance | None = None


def font_request_from_intent(intent: FontIntent) -> FontRequest:
    """Convert output-agnostic Design IR font intent into a resolver request."""
    return FontRequest(
        family=intent.family,
        weight=intent.weight,
        style=intent.style,
        flavor=intent.flavor,
    )


def resolve_font(registry: FontRegistry, request: FontRequest) -> FontResolution:
    """Resolve a design font request deterministically from a populated registry."""
    family_faces = tuple(
        face for face in registry.faces if face.family.casefold() == request.family.casefold()
    )
    if not family_faces:
        return FontResolution(
            status="missing",
            request=request,
            reason="font family not found in registry",
        )

    requested_style = request.style.casefold()
    requested_flavor = request.flavor.casefold() if request.flavor else None

    exact = next(
        (
            face
            for face in family_faces
            if face.weight == request.weight
            and face.style.casefold() == requested_style
            and (face.flavor.casefold() if face.flavor else None) == requested_flavor
        ),
        None,
    )
    if exact is not None:
        return FontResolution(status="exact", request=request, face=exact)

    def rank(face: FontFace) -> tuple[int, int, int, str]:
        face_flavor = face.flavor.casefold() if face.flavor else None
        if requested_flavor is not None:
            flavor_rank = 0 if face_flavor == requested_flavor else 1
        else:
            flavor_rank = 0 if face_flavor is None else 1
        return (
            0 if face.style.casefold() == requested_style else 1,
            flavor_rank,
            abs(face.weight - request.weight),
            face.key[3] or "",
        )

    face = min(family_faces, key=rank)
    return FontResolution(
        status="fallback",
        request=request,
        face=face,
        reason=(
            f"requested face unavailable; using {face.family} / "
            f"{face.weight} / {face.style}"
            + (f" / {face.flavor}" if face.flavor else "")
        ),
    )


def resolve_font_with_cache(
    root: Path,
    cache_path: Path,
    request: FontRequest,
    *,
    metadata_reader: MetadataReader = read_font_metadata,
) -> FontResolution:
    """Resolve through the registry cache, refreshing exactly once on an exact-face miss.

    A fallback is selected only after the refresh pass. This keeps cache lookup and
    semantic fallback separate: a stale cache cannot silently turn a newly added exact
    face into a fallback.
    """
    registry = current_font_registry()
    if registry.find_face(request.family, request.weight, request.style, request.flavor) is not None:
        result = resolve_font(registry, request)
        return _with_provenance(result, "cache_hit")

    cached = load_cached_font_registry(cache_path)
    if cached is not None and cached.find_face(
        request.family,
        request.weight,
        request.style,
        request.flavor,
    ) is not None:
        result = resolve_font(cached, request)
        return _with_provenance(result, "cache_hit")

    refreshed = refresh_font_registry(
        root,
        metadata_reader=metadata_reader,
        cache_path=cache_path,
    )
    result = resolve_font(refreshed, request)
    provenance: LookupProvenance
    if result.status == "exact":
        provenance = "resolved_after_refresh"
    elif result.status == "fallback":
        provenance = "fallback_after_refresh"
    else:
        provenance = "missing_after_refresh"
    return _with_provenance(result, provenance)


def resolve_font_intent(
    root: Path,
    cache_path: Path,
    intent: FontIntent,
    *,
    metadata_reader: MetadataReader = read_font_metadata,
) -> FontResolution:
    """Resolve a Design IR font intent without exposing source-specific metadata."""
    return resolve_font_with_cache(
        root,
        cache_path,
        font_request_from_intent(intent),
        metadata_reader=metadata_reader,
    )


def _with_provenance(
    resolution: FontResolution,
    provenance: LookupProvenance,
) -> FontResolution:
    return FontResolution(
        status=resolution.status,
        request=resolution.request,
        face=resolution.face,
        reason=resolution.reason,
        provenance=provenance,
    )
