from pathlib import Path

from morpher.assets import semantic_asset_names
from morpher.ir.nodes import DesignNode


def test_semantic_asset_names_preserve_context_and_figma_node_name() -> None:
    root = DesignNode(
        kind="container",
        name="Discovery",
        children=[
            DesignNode(
                kind="image",
                name="Rectangle 1",
                source_id="45:5272",
                image_ref="fde8f092a1964e279bc2edecc233a32e9689e84f",
            ),
            DesignNode(kind="icon", name="Play Icon", source_id="45:5273"),
        ],
    )
    assets = [
        Path("fde8f092a1964e279bc2edecc233a32e9689e84f.jpg"),
        Path("45-5273.svg"),
    ]

    names = semantic_asset_names(root, assets)

    assert names["fde8f092a1964e279bc2edecc233a32e9689e84f"] == "discovery-rectangle-1.jpg"
    assert names["45-5273"] == "discovery-play-icon.svg"
    assert "fde8f092" not in names["fde8f092a1964e279bc2edecc233a32e9689e84f"]


def test_semantic_asset_names_are_deterministic_and_collision_safe() -> None:
    root = DesignNode(
        kind="container",
        name="Discovery",
        children=[
            DesignNode(kind="icon", name="Icon", source_id="1:1"),
            DesignNode(kind="icon", name="Icon", source_id="1:2"),
        ],
    )
    assets = [Path("1-1.svg"), Path("1-2.svg")]

    names = semantic_asset_names(root, assets)

    assert names == {
        "1-1": "discovery-icon.svg",
        "1-2": "discovery-icon-2.svg",
    }


def test_semantic_asset_names_bound_long_figma_text_names_and_keep_traceability() -> None:
    long_name = (
        "MUU IS A NEW, UNPRETENTIOUS YET LUXURIOUS HOTEL BRAND THAT IS BUILT AROUND "
        "A BELIEF THAT HAPPINESS COMES FROM BEING ONESELF THROUGH DYNAMIC ARTISTIC SPACES"
    )
    root = DesignNode(
        kind="container",
        name="Discovery",
        children=[DesignNode(kind="text", name=long_name, source_id="45:5271")],
    )

    names = semantic_asset_names(root, [Path("45-5271.svg")])
    filename = names["45-5271"]

    assert filename.startswith("discovery-muu-is-a-new-unpretentious-yet-luxurious-hotel-brand")
    assert filename.endswith("-45-5271.svg")
    assert len(filename) < 128
