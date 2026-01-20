"""Tests for DocExtractor - AST-based documentation extraction."""

import pytest


class TestDocExtractor:
    """Tests for DocExtractor - AST-based documentation extraction."""

    def test_extract_returns_module_doc_for_valid_python_file(self, temp_python_file):
        """DocExtractor.extract() returns ModuleDoc for valid Python file."""
        from scripts.help import DocExtractor, ModuleDoc

        temp_path = temp_python_file(
            '"""Module docstring for testing."""\n'
            'def hello(): pass\n'
        )

        extractor = DocExtractor()
        result = extractor.extract(temp_path)

        assert result is not None
        assert isinstance(result, ModuleDoc)
        assert result.docstring == "Module docstring for testing."
        assert result.name == temp_path.stem

    def test_extract_returns_none_for_invalid_syntax(self, temp_python_file):
        """DocExtractor.extract() returns None for invalid Python syntax."""
        from scripts.help import DocExtractor

        temp_path = temp_python_file('def broken(\n')  # Invalid syntax

        extractor = DocExtractor()
        result = extractor.extract(temp_path)
        assert result is None

    def test_extract_captures_class_docstrings(self, temp_python_file):
        """DocExtractor extracts class docstrings."""
        from scripts.help import DocExtractor

        temp_path = temp_python_file(
            '"""Module doc."""\n'
            'class MyClass:\n'
            '    """MyClass does something."""\n'
            '    pass\n'
        )

        extractor = DocExtractor()
        result = extractor.extract(temp_path)

        assert result is not None
        assert len(result.classes) == 1
        assert result.classes[0].name == "MyClass"
        assert result.classes[0].docstring == "MyClass does something."

    def test_extract_captures_function_signatures(self, temp_python_file):
        """DocExtractor extracts function signatures with type hints."""
        from scripts.help import DocExtractor

        temp_path = temp_python_file(
            '"""Module doc."""\n'
            'def greet(name: str, count: int = 1) -> str:\n'
            '    """Greet someone."""\n'
            '    return name * count\n'
        )

        extractor = DocExtractor()
        result = extractor.extract(temp_path)

        assert result is not None
        assert len(result.functions) == 1
        func = result.functions[0]
        assert func.name == "greet"
        assert "name: str" in func.signature
        assert "count: int" in func.signature
        assert "-> str" in func.signature

    def test_extract_captures_class_methods(self, temp_python_file):
        """DocExtractor extracts methods from classes."""
        from scripts.help import DocExtractor

        temp_path = temp_python_file(
            '"""Module doc."""\n'
            'class Calculator:\n'
            '    """A calculator."""\n'
            '    def add(self, a: int, b: int) -> int:\n'
            '        """Add two numbers."""\n'
            '        return a + b\n'
        )

        extractor = DocExtractor()
        result = extractor.extract(temp_path)

        assert result is not None
        assert len(result.classes) == 1
        assert len(result.classes[0].methods) >= 1
        add_method = next(
            (m for m in result.classes[0].methods if m.name == "add"),
            None
        )
        assert add_method is not None
        assert add_method.docstring == "Add two numbers."

    def test_get_brief_extracts_first_sentence(self):
        """DocExtractor._get_brief() extracts first sentence from docstring."""
        from scripts.help import DocExtractor

        extractor = DocExtractor()

        # Test with period
        assert extractor._get_brief("First sentence. More text.") == "First sentence."

        # Test without period
        result = extractor._get_brief("No period here")
        assert "No period" in result

        # Test empty
        assert extractor._get_brief("") == "(No documentation)"

    def test_extract_skips_private_functions(self, temp_python_file):
        """DocExtractor skips functions starting with underscore."""
        from scripts.help import DocExtractor

        temp_path = temp_python_file(
            '"""Module doc."""\n'
            'def public_func(): pass\n'
            'def _private_func(): pass\n'
        )

        extractor = DocExtractor()
        result = extractor.extract(temp_path)

        assert result is not None
        func_names = [f.name for f in result.functions]
        assert "public_func" in func_names
        assert "_private_func" not in func_names
