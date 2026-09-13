import pytest

from morpher.compiler.normalizer import normalize
from morpher.ir.nodes import DesignDocument, DesignNode
from morpher.ir.styles import DesignStyle
from morpher.ir.validation import validate_design_ir


def test_valid_design_ir_has_no_diagnostics() -> None:
    document = DesignDocument(
        root=DesignNode(
            kind="container",
            name="Root",
            source_id="root",
            style=DesignStyle(width=100, height=100),
            children=[
                DesignNode(
                    kind="text",
                    name="Title",
                    source_id="title",
                    text="Hello",
                    style=DesignStyle(font_size=16),
                )
            ],
        )
    )

    result = validate_design_ir(document)

    assert result.valid is True
    assert result.diagnostics == ()


def test_negative_dimensions_and_invalid_opacity_are_errors() -> None:
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(width=-10, opacity=1.5),
    )

    result = validate_design_ir(root)

    assert result.valid is False
    assert {item.code for item in result.errors} == {
        "ir.negative_size",
        "ir.opacity_range",
    }


def test_non_finite_geometry_is_an_error() -> None:
    root = DesignNode(
        kind="container",
        source_id="root",
        style=DesignStyle(x=float("nan"), rotation=float("inf")),
    )

    result = validate_design_ir(root)

    assert result.valid is False
    assert [item.code for item in result.errors] == [
        "ir.non_finite_number",
        "ir.non_finite_number",
    ]


def test_suspicious_but_compilable_states_are_warnings() -> None:
    root = DesignNode(
        kind="container",
        source_id="root",
        children=[
            DesignNode(
                kind="text",
                source_id="same",
                text=None,
                style=DesignStyle(width_mode="fixed"),
            ),
            DesignNode(
                kind="image",
                source_id="same",
            ),
            DesignNode(
                kind="unsupported",
                source_id="unsupported",
            ),
        ],
    )

    result = validate_design_ir(root)

    assert result.valid is True
    assert {item.code for item in result.warnings} == {
        "ir.fixed_width_without_width",
        "ir.text_without_content",
        "ir.duplicate_source_id",
        "ir.image_without_asset",
        "ir.unsupported_node",
    }
    duplicate = next(item for item in result.warnings if item.code == "ir.duplicate_source_id")
    assert duplicate.path_string == "root/1"
    assert duplicate.source_id == "same"


def test_cycle_is_reported_without_recursive_failure() -> None:
    root = DesignNode(kind="container", source_id="root")
    child = DesignNode(kind="container", source_id="child")
    root.children.append(child)
    child.children.append(root)

    result = validate_design_ir(root)

    assert result.valid is False
    assert [item.code for item in result.errors] == ["ir.cycle"]
    assert result.errors[0].path_string == "root/0/0"


def test_normalize_rejects_ir_with_validation_errors() -> None:
    document = DesignDocument(
        root=DesignNode(
            kind="container",
            source_id="root",
            style=DesignStyle(height=-1),
        )
    )

    with pytest.raises(ValueError, match=r"ir\.negative_size at root"):
        normalize(document)


def test_normalize_allows_warning_only_ir() -> None:
    document = DesignDocument(
        root=DesignNode(
            kind="text",
            source_id="root",
            text=None,
        )
    )

    assert normalize(document) is document
