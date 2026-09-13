from __future__ import annotations

from types import SimpleNamespace

import pytest

from morpher.run import main


class FakeWordPressClient:
    seen_targets: list[str] = []

    def __init__(self, target: str) -> None:
        self.target = target
        self.seen_targets.append(target)

    def health(self):
        return SimpleNamespace(
            status="ok",
            api_version="v1",
            plugin=SimpleNamespace(version="0.4.0"),
            wordpress=SimpleNamespace(version="7.1"),
            integrations=SimpleNamespace(
                elementor=SimpleNamespace(ready=True, version="4.2.4")
            ),
        )


def test_health_command_normalizes_target_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeWordPressClient.seen_targets = []
    monkeypatch.setattr("morpher.run.WordPressClient", FakeWordPressClient)

    main(["health", "http://localhost:8080/"])

    assert FakeWordPressClient.seen_targets == ["http://localhost:8080"]
    assert capsys.readouterr().out == (
        "HEALTH   http://localhost:8080  ok\n"
        "  Morpher Plugin: 0.4.0\n"
        "  WordPress:      7.1\n"
        "  Elementor:      4.2.4 (ready)\n"
        "  API:            v1\n"
    )


def test_health_command_requires_target_until_working_site_exists() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["health"])

    assert exc_info.value.code == 2


def test_existing_morpher_target_does_not_route_to_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, list[str]] = {}

    def fake_render_main(argv: list[str]) -> None:
        seen["argv"] = argv

    monkeypatch.setattr("morpher.run._render_main", fake_render_main)

    main(["SomeSource"])

    assert seen["argv"] == ["SomeSource"]
