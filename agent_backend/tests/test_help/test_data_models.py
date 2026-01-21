"""Tests for data model classes."""

from pathlib import Path

import pytest


class TestDataModels:
    """Tests for data model classes."""

    def test_module_doc_dataclass_fields(self):
        """ModuleDoc has all required fields."""
        from scripts.help import ModuleDoc

        module = ModuleDoc(
            name="test",
            qualified_name="pkg.test",
            filepath=Path("/test.py"),
            docstring="Doc",
            brief="Brief",
            classes=[],
            functions=[]
        )

        assert module.name == "test"
        assert module.qualified_name == "pkg.test"
        assert module.filepath == Path("/test.py")
        assert module.docstring == "Doc"
        assert module.brief == "Brief"

    def test_class_doc_dataclass_fields(self):
        """ClassDoc has all required fields."""
        from scripts.help import ClassDoc

        cls = ClassDoc(
            name="MyClass",
            docstring="My class doc.",
            methods=[],
            bases=["Base"]
        )

        assert cls.name == "MyClass"
        assert cls.docstring == "My class doc."
        assert cls.bases == ["Base"]

    def test_function_doc_dataclass_fields(self):
        """FunctionDoc has all required fields."""
        from scripts.help import FunctionDoc

        func = FunctionDoc(
            name="my_func",
            signature="my_func(x: int) -> str",
            docstring="My function.",
            is_method=False
        )

        assert func.name == "my_func"
        assert func.signature == "my_func(x: int) -> str"
        assert func.docstring == "My function."
        assert func.is_method is False
