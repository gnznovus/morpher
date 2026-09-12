from pathlib import Path

from morpher.remove import remove_all, remove_target


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_remove_target_clears_matching_artifacts_only(tmp_path: Path):
    storage = tmp_path / "storage"
    deployments = tmp_path / "deployments"

    _write(storage / "figma-import" / "Contact.json")
    _write(storage / "figma-import" / "assets" / "Contact" / "45-1.svg")
    _write(storage / "output" / "elementor" / "Contact_template.json")
    _write(storage / "output" / "elementor" / "assets" / "Contact" / "45-1.webp")
    _write(storage / "output" / "native" / "Contact.css")
    _write(storage / "processed" / "Contact_P.json")
    _write(storage / "figma-import" / "Other.json")
    _write(storage / "output" / "elementor" / "assets" / "Other" / "keep.webp")

    _write(deployments / "contact" / "template.json")
    _write(deployments / "contact" / "assets" / "45-1.webp")
    _write(deployments / "other" / "template.json")

    removed = remove_target("Contact", storage_root=storage, deployments_root=deployments)

    assert removed
    assert not (storage / "figma-import" / "Contact.json").exists()
    assert not (storage / "figma-import" / "assets" / "Contact").exists()
    assert not (storage / "output" / "elementor" / "Contact_template.json").exists()
    assert not (storage / "output" / "elementor" / "assets" / "Contact").exists()
    assert not (storage / "output" / "native" / "Contact.css").exists()
    assert not (storage / "processed" / "Contact_P.json").exists()
    assert not (deployments / "contact").exists()

    assert (storage / "figma-import" / "Other.json").exists()
    assert (storage / "output" / "elementor" / "assets" / "Other" / "keep.webp").exists()
    assert (deployments / "other" / "template.json").exists()


def test_remove_target_normalizes_spaces_hyphens_and_template_suffix(tmp_path: Path):
    storage = tmp_path / "storage"
    deployments = tmp_path / "deployments"

    _write(storage / "figma-import" / "Contact-Us.json")
    _write(storage / "output" / "elementor" / "Contact-Us_template.json")
    _write(deployments / "contact-us" / "template.json")

    remove_target("Contact Us", storage_root=storage, deployments_root=deployments)

    assert not (storage / "figma-import" / "Contact-Us.json").exists()
    assert not (storage / "output" / "elementor" / "Contact-Us_template.json").exists()
    assert not (deployments / "contact-us").exists()


def test_remove_all_clears_contents_but_preserves_managed_roots(tmp_path: Path):
    storage = tmp_path / "storage"
    deployments = tmp_path / "deployments"
    _write(storage / "figma-import" / "Contact.json")
    _write(storage / "output" / "elementor" / "Contact_template.json")
    _write(deployments / "contact" / "template.json")

    removed = remove_all(storage_root=storage, deployments_root=deployments)

    assert removed
    assert storage.exists()
    assert deployments.exists()
    assert list(storage.iterdir()) == []
    assert list(deployments.iterdir()) == []
