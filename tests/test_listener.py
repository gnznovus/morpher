import base64
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

    target, replaced, assets_saved, vectors_saved, texts_saved = save_figma_import(
        {"name": "Hero / Desktop", "nodeId": "1:2", "payload": payload},
        storage,
    )

    assert target == storage.figma_import / "Hero-Desktop.json"
    assert replaced is False
    assert assets_saved == 0
    assert vectors_saved == 0
    assert texts_saved == 0
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_save_figma_import_replaces_same_named_snapshot(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    first = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}
    second = {"document": {"id": "1:2", "name": "Hero v2", "type": "FRAME"}}

    save_figma_import({"name": "Hero", "payload": first}, storage)
    target, replaced, assets_saved, vectors_saved, texts_saved = save_figma_import({"name": "Hero", "payload": second}, storage)

    assert replaced is True
    assert assets_saved == 0
    assert vectors_saved == 0
    assert texts_saved == 0
    assert json.loads(target.read_text(encoding="utf-8")) == second


def test_save_figma_import_writes_image_assets(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    payload = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}
    png = b"\x89PNG\r\n\x1a\nexample"

    target, _, assets_saved, vectors_saved, texts_saved = save_figma_import(
        {
            "name": "Hero",
            "payload": payload,
            "assets": [{"imageRef": "abc123", "data": base64.b64encode(png).decode("ascii")}],
        },
        storage,
    )

    asset = storage.figma_asset_dir(target) / "abc123.png"
    assert assets_saved == 1
    assert vectors_saved == 0
    assert texts_saved == 0
    assert asset.read_bytes() == png


def test_save_figma_import_writes_vector_assets(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    payload = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'

    target, _, assets_saved, vectors_saved, texts_saved = save_figma_import(
        {
            "name": "Hero",
            "payload": payload,
            "vectorAssets": [{"sourceId": "45:5306", "data": base64.b64encode(svg).decode("ascii")}],
        },
        storage,
    )

    asset = storage.figma_asset_dir(target) / "45-5306.svg"
    assert assets_saved == 0
    assert vectors_saved == 1
    assert texts_saved == 0
    assert asset.read_bytes() == svg


def test_save_figma_import_writes_text_outline_assets(tmp_path: Path) -> None:
    storage = StoragePaths(tmp_path / "storage")
    payload = {"document": {"id": "1:2", "name": "Hero", "type": "FRAME"}}
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 20"><path d="M0 0h10v10z"/></svg>'

    target, _, assets_saved, vectors_saved, texts_saved = save_figma_import(
        {
            "name": "Hero",
            "payload": payload,
            "textAssets": [{"sourceId": "45:7001", "data": base64.b64encode(svg).decode("ascii")}],
        },
        storage,
    )

    asset = storage.figma_asset_dir(target) / "45-7001.svg"
    assert assets_saved == 0
    assert vectors_saved == 0
    assert texts_saved == 1
    assert asset.read_bytes() == svg


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
