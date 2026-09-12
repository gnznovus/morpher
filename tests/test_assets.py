from pathlib import Path

from PIL import Image

from morpher.assets import elementor_asset_keys, prepare_elementor_assets, semantic_asset_names
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


def test_elementor_asset_keys_ignore_standalone_text_assets() -> None:
    root = DesignNode(
        kind="container",
        name="Footer",
        children=[
            DesignNode(kind="text", name="FOLLOW US", source_id="45:5105"),
            DesignNode(kind="icon", name="Social Icons", source_id="45:5106"),
            DesignNode(
                kind="image",
                name="Background",
                image_ref="5fa04d223a6dad37b92a258092f70586be86cd21",
            ),
        ],
    )

    assert elementor_asset_keys(root) == {
        "45-5106",
        "5fa04d223a6dad37b92a258092f70586be86cd21",
    }


def test_prepare_elementor_assets_converts_svg_to_webp_and_omits_text(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "elementor" / "assets" / "Footer"
    output_root = tmp_path / "elementor"
    source_dir.mkdir()

    icon_svg = source_dir / "45-5106.svg"
    icon_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10">'
        '<rect width="20" height="10" fill="#ff5000"/></svg>',
        encoding="utf-8",
    )
    text_svg = source_dir / "45-5105.svg"
    text_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10">'
        '<path d="M0 0h20v10H0z" fill="white"/></svg>',
        encoding="utf-8",
    )

    root = DesignNode(
        kind="container",
        name="Footer",
        children=[
            DesignNode(kind="text", name="FOLLOW US", source_id="45:5105"),
            DesignNode(kind="icon", name="Social Icons", source_id="45:5106"),
        ],
    )

    result = prepare_elementor_assets(
        root,
        [icon_svg, text_svg],
        target_dir,
        output_root,
    )

    assert result == {"45-5106": "assets/Footer/footer-social-icons.webp"}
    assert sorted(path.name for path in target_dir.iterdir()) == ["footer-social-icons.webp"]

    with Image.open(target_dir / "footer-social-icons.webp") as image:
        assert image.format == "WEBP"
        assert image.size == (40, 20)
        assert image.mode in {"RGB", "RGBA"}
