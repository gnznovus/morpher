from __future__ import annotations

import pytest

from morpher.targets import TargetResolutionError, normalize_target_url, resolve_target_url


def test_normalize_target_url_trims_and_removes_trailing_slashes() -> None:
    assert normalize_target_url("  http://localhost:8080///  ") == "http://localhost:8080"


def test_normalize_target_url_preserves_subdirectory_site_path() -> None:
    assert normalize_target_url("https://example.com/site-a/") == "https://example.com/site-a"


def test_normalize_target_url_requires_http_scheme() -> None:
    with pytest.raises(TargetResolutionError, match="http:// or https://"):
        normalize_target_url("example.com")


def test_normalize_target_url_rejects_query_and_fragment() -> None:
    with pytest.raises(TargetResolutionError, match="query string or fragment"):
        normalize_target_url("https://example.com/site?preview=1")


def test_resolve_target_url_prefers_explicit_target() -> None:
    assert (
        resolve_target_url(
            "https://explicit.example.com/",
            working_site_url="https://working.example.com/",
        )
        == "https://explicit.example.com"
    )


def test_resolve_target_url_uses_working_site_when_explicit_target_is_missing() -> None:
    assert (
        resolve_target_url(None, working_site_url="https://working.example.com/")
        == "https://working.example.com"
    )


def test_resolve_target_url_requires_target_when_no_working_site_exists() -> None:
    with pytest.raises(TargetResolutionError, match="no working site is configured"):
        resolve_target_url(None)
