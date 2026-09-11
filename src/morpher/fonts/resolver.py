from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from morpher.fonts.model import FontFace
from morpher.fonts.registry import FontRegistry


ResolutionStatus = Literal["exact", "fallback", "missing"]


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
