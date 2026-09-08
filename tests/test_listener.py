import json
from pathlib import Path

import pytest

from morpher.listener import safe_stem, save_figma_import
from morpher.storage.paths import StoragePaths


def test_safe_stem_normalizes_figma_name() -> None:
    assert safe_stem("Hero / Desktop") == "Hero-Desktop"
    assert safe_stem("  ") == "figma-node"


def test_save_figma_import_writes_payload(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    payload = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}

    target, replaced = save_figma_import(
        {"name": "Hero / Desktop", "nodeId": "1:2", "payload": payload},
        storage,
    )

    assert target == storage.figma_import / "Hero-Desktop.json"
    assert replaced is False
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_save_figma_import_replaces_same_named_snapshot(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    first = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}
    second = {"document": {"id": "1:2", "name": "Hero v2", "type": "FRAME"}}

    save_figma_import({"name": "Hero", "payload": first}, storage)
    target, replaced = save_figma_import({"name": "Hero", "payload": second}, storage)

    assert replaced is True
    assert json.loads(target.read_text(encoding="utf-8")) == second


@pytest.mark.parametrize(
    "envelope",
    [
        {},
        {"name": "Hero", "payload": []},
        {"name": "Hero", "payload": {}},
    ],
)
def test_save_figma_import_rejects_invalid_envelopes(tmp_path: Path, envelope: dict) -> None:
    storage = StoragePaths(tmp_path / "storage")
    with pytest.raises(ValueError):
        save_figma_import(envelope, storage)
