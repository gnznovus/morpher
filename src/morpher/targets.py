from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


class TargetResolutionError(ValueError):
    pass


def normalize_target_url(value: str) -> str:
    """Normalize one explicit Morpher site target without inventing defaults."""
    raw = value.strip()
    if not raw:
        raise TargetResolutionError("Target URL is required.")

    try:
        parsed = urlsplit(raw)
        # Accessing port validates malformed/out-of-range port values.
        _ = parsed.port
    except ValueError as exc:
        raise TargetResolutionError(f"Invalid target URL: {value}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise TargetResolutionError("Target URL must use http:// or https://.")
    if not parsed.hostname:
        raise TargetResolutionError(f"Invalid target URL: {value}")
    if parsed.query or parsed.fragment:
        raise TargetResolutionError("Target URL cannot include a query string or fragment.")

    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, parsed.netloc, path, "", ""))


def resolve_target_url(
    explicit_url: str | None,
    *,
    working_site_url: str | None = None,
) -> str:
    """Resolve explicit target first, then a future working-site target."""
    if explicit_url is not None and explicit_url.strip():
        return normalize_target_url(explicit_url)
    if working_site_url is not None and working_site_url.strip():
        return normalize_target_url(working_site_url)
    raise TargetResolutionError(
        "Target URL is required because no working site is configured."
    )
