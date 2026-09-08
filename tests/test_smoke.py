from morpher.ir.nodes import DesignNode
from morpher.storage.paths import StoragePaths


def test_package_imports() -> None:
    assert DesignNode is not None
    assert StoragePaths is not None
