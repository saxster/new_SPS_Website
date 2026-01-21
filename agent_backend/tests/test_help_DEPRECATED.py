"""
Tests for the help.py module - Linux man-style documentation viewer.

Tests for:
- DocExtractor: AST-based documentation extraction
- ModuleRegistry: Auto-discovery of modules
- ManFormatter: Man page style formatting
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDocExtractor:
    """Tests for DocExtractor - AST-based documentation extraction."""

    def test_extract_returns_module_doc_for_valid_python_file(self):
        """DocExtractor.extract() returns ModuleDoc for valid Python file."""
        from scripts.help import DocExtractor, ModuleDoc

        # Create a temporary Python file with docstring
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Module docstring for testing."""\n')
            f.write('def hello(): pass\n')
            temp_path = Path(f.name)

        try:
            extractor = DocExtractor()
            result = extractor.extract(temp_path)

            assert result is not None
            assert isinstance(result, ModuleDoc)
            assert result.docstring == "Module docstring for testing."
            assert result.name == temp_path.stem
        finally:
            os.unlink(temp_path)

    def test_extract_returns_none_for_invalid_syntax(self):
        """DocExtractor.extract() returns None for invalid Python syntax."""
        from scripts.help import DocExtractor

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('def broken(\n')  # Invalid syntax
            temp_path = Path(f.name)

        try:
            extractor = DocExtractor()
            result = extractor.extract(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_extract_captures_class_docstrings(self):
        """DocExtractor extracts class docstrings."""
        from scripts.help import DocExtractor

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Module doc."""\n')
            f.write('class MyClass:\n')
            f.write('    """MyClass does something."""\n')
            f.write('    pass\n')
            temp_path = Path(f.name)

        try:
            extractor = DocExtractor()
            result = extractor.extract(temp_path)

            assert result is not None
            assert len(result.classes) == 1
            assert result.classes[0].name == "MyClass"
            assert result.classes[0].docstring == "MyClass does something."
        finally:
            os.unlink(temp_path)

    def test_extract_captures_function_signatures(self):
        """DocExtractor extracts function signatures with type hints."""
        from scripts.help import DocExtractor

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Module doc."""\n')
            f.write('def greet(name: str, count: int = 1) -> str:\n')
            f.write('    """Greet someone."""\n')
            f.write('    return name * count\n')
            temp_path = Path(f.name)

        try:
            extractor = DocExtractor()
            result = extractor.extract(temp_path)

            assert result is not None
            assert len(result.functions) == 1
            func = result.functions[0]
            assert func.name == "greet"
            assert "name: str" in func.signature
            assert "count: int" in func.signature
            assert "-> str" in func.signature
        finally:
            os.unlink(temp_path)

    def test_extract_captures_class_methods(self):
        """DocExtractor extracts methods from classes."""
        from scripts.help import DocExtractor

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Module doc."""\n')
            f.write('class Calculator:\n')
            f.write('    """A calculator."""\n')
            f.write('    def add(self, a: int, b: int) -> int:\n')
            f.write('        """Add two numbers."""\n')
            f.write('        return a + b\n')
            temp_path = Path(f.name)

        try:
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
        finally:
            os.unlink(temp_path)

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

    def test_extract_skips_private_functions(self):
        """DocExtractor skips functions starting with underscore."""
        from scripts.help import DocExtractor

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Module doc."""\n')
            f.write('def public_func(): pass\n')
            f.write('def _private_func(): pass\n')
            temp_path = Path(f.name)

        try:
            extractor = DocExtractor()
            result = extractor.extract(temp_path)

            assert result is not None
            func_names = [f.name for f in result.functions]
            assert "public_func" in func_names
            assert "_private_func" not in func_names
        finally:
            os.unlink(temp_path)


class TestModuleRegistry:
    """Tests for ModuleRegistry - module auto-discovery."""

    def test_scan_finds_python_files(self):
        """ModuleRegistry.scan() discovers Python files in directories."""
        from scripts.help import ModuleRegistry

        # Use the actual .agent directory
        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # Should find at least some modules
        assert len(modules) > 0
        # Should find known modules like content_brain
        assert "content_brain" in modules

    def test_get_returns_module_by_name(self):
        """ModuleRegistry.get() returns module by name."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        registry.scan()

        module = registry.get("content_brain")
        assert module is not None
        assert module.name == "content_brain"

    def test_get_returns_none_for_unknown_module(self):
        """ModuleRegistry.get() returns None for unknown module."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        registry.scan()

        module = registry.get("nonexistent_module_xyz")
        assert module is None

    def test_search_finds_modules_by_docstring_content(self):
        """ModuleRegistry.search() finds modules containing query text."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        registry.scan()

        # Search for something that should be in content_brain
        results = registry.search("persistent")
        assert len(results) >= 1
        # content_brain mentions "persistent memory"
        module_names = [m.name for m in results]
        assert "content_brain" in module_names

    def test_list_all_returns_sorted_modules(self):
        """ModuleRegistry.list_all() returns all modules sorted by name."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        registry.scan()

        modules = registry.list_all()
        assert len(modules) > 0

        # Check they're sorted
        names = [m.name for m in modules]
        assert names == sorted(names)

    def test_excludes_pycache_directories(self):
        """ModuleRegistry excludes __pycache__ directories."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # No module should have pycache in its path
        for module in modules.values():
            assert "__pycache__" not in str(module.filepath)

    def test_excludes_init_files(self):
        """ModuleRegistry excludes __init__.py files."""
        from scripts.help import ModuleRegistry

        agent_dir = Path(__file__).parent.parent
        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # No module should be __init__
        for module in modules.values():
            assert module.name != "__init__"


class TestManFormatter:
    """Tests for ManFormatter - man page style output."""

    def test_format_module_includes_name_section(self):
        """ManFormatter.format_module() includes NAME section."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test_module",
            qualified_name="skills.test_module",
            filepath=Path("/fake/path.py"),
            docstring="A test module for testing.",
            brief="A test module for testing.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "NAME" in output
        assert "test_module" in output
        assert "A test module for testing." in output

    def test_format_module_includes_synopsis_section(self):
        """ManFormatter.format_module() includes SYNOPSIS section."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test_module",
            qualified_name="skills.test_module",
            filepath=Path("/fake/path.py"),
            docstring="Test module.",
            brief="Test module.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "SYNOPSIS" in output
        assert "from skills.test_module import" in output

    def test_format_module_includes_description_section(self):
        """ManFormatter.format_module() includes DESCRIPTION section."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test_module",
            qualified_name="skills.test_module",
            filepath=Path("/fake/path.py"),
            docstring="Full description here.\nWith multiple lines.",
            brief="Full description here.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "DESCRIPTION" in output
        assert "Full description here." in output
        assert "With multiple lines." in output

    def test_format_module_includes_classes_section(self):
        """ManFormatter.format_module() includes CLASSES section when present."""
        from scripts.help import ManFormatter, ModuleDoc, ClassDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test_module",
            qualified_name="skills.test_module",
            filepath=Path("/fake/path.py"),
            docstring="Test module.",
            brief="Test module.",
            classes=[
                ClassDoc(
                    name="TestClass",
                    docstring="A test class.",
                    methods=[],
                    bases=["BaseClass"]
                )
            ],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "CLASSES" in output
        assert "TestClass" in output
        assert "A test class." in output

    def test_format_module_includes_files_section(self):
        """ManFormatter.format_module() includes FILES section."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test_module",
            qualified_name="skills.test_module",
            filepath=Path("/fake/path/test_module.py"),
            docstring="Test module.",
            brief="Test module.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "FILES" in output
        assert "test_module.py" in output

    def test_format_list_shows_all_modules(self):
        """ManFormatter.format_list() shows all modules with briefs."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        modules = [
            ModuleDoc(
                name="alpha",
                qualified_name="skills.alpha",
                filepath=Path("/fake/alpha.py"),
                docstring="Alpha module.",
                brief="Alpha module.",
                classes=[],
                functions=[]
            ),
            ModuleDoc(
                name="beta",
                qualified_name="skills.beta",
                filepath=Path("/fake/beta.py"),
                docstring="Beta module.",
                brief="Beta module.",
                classes=[],
                functions=[]
            ),
        ]

        output = formatter.format_list(modules)
        assert "alpha" in output
        assert "beta" in output
        assert "Alpha module." in output
        assert "Beta module." in output
        assert "Total: 2 modules" in output

    def test_format_search_results_shows_matches(self):
        """ManFormatter.format_search_results() shows matching modules."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        results = [
            ModuleDoc(
                name="content_brain",
                qualified_name="skills.content_brain",
                filepath=Path("/fake/content_brain.py"),
                docstring="Persistent memory for content.",
                brief="Persistent memory for content.",
                classes=[],
                functions=[]
            ),
        ]

        output = formatter.format_search_results("persistent", results)
        assert "persistent" in output
        assert "content_brain" in output
        assert "Found 1 matching module" in output

    def test_format_search_results_handles_no_matches(self):
        """ManFormatter.format_search_results() handles empty results."""
        from scripts.help import ManFormatter

        formatter = ManFormatter(use_color=False)
        output = formatter.format_search_results("xyznonexistent", [])
        assert "No matches found" in output

    def test_color_output_includes_ansi_codes(self):
        """ManFormatter with color=True includes ANSI codes."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=True)
        module = ModuleDoc(
            name="test",
            qualified_name="test",
            filepath=Path("/test.py"),
            docstring="Test.",
            brief="Test.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        # ANSI escape codes start with \033[
        assert "\033[" in output

    def test_plain_output_no_ansi_codes(self):
        """ManFormatter with use_color=False has no ANSI codes."""
        from scripts.help import ManFormatter, ModuleDoc

        formatter = ManFormatter(use_color=False)
        module = ModuleDoc(
            name="test",
            qualified_name="test",
            filepath=Path("/test.py"),
            docstring="Test.",
            brief="Test.",
            classes=[],
            functions=[]
        )

        output = formatter.format_module(module)
        assert "\033[" not in output


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


class TestCLIIntegration:
    """Integration tests for CLI behavior."""

    def test_main_list_modules_exits_zero(self):
        """Running help.py without args lists modules and exits 0."""
        import subprocess

        agent_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, str(agent_dir / "scripts" / "help.py"), "--no-pager"],
            capture_output=True,
            text=True,
            cwd=str(agent_dir)
        )

        # Should succeed
        assert result.returncode == 0
        # Should show modules
        assert "modules" in result.stdout.lower()

    def test_main_specific_module_shows_man_page(self):
        """Running help.py with module name shows man page."""
        import subprocess

        agent_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(agent_dir / "scripts" / "help.py"),
                "content_brain",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            cwd=str(agent_dir)
        )

        # Should succeed
        assert result.returncode == 0
        # Should show man page sections
        assert "NAME" in result.stdout
        assert "content_brain" in result.stdout

    def test_main_unknown_module_exits_nonzero(self):
        """Running help.py with unknown module exits non-zero."""
        import subprocess

        agent_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(agent_dir / "scripts" / "help.py"),
                "nonexistent_module_xyz",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            cwd=str(agent_dir)
        )

        # Should fail
        assert result.returncode != 0
        # Should show error
        assert "not found" in result.stderr.lower()

    def test_main_search_finds_modules(self):
        """Running help.py --search finds relevant modules."""
        import subprocess

        agent_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(agent_dir / "scripts" / "help.py"),
                "--search", "fact",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            cwd=str(agent_dir)
        )

        # Should succeed
        assert result.returncode == 0
        # Should show search results
        assert "Search results" in result.stdout or "fact" in result.stdout.lower()

    def test_main_plain_flag_removes_colors(self):
        """Running help.py --plain removes ANSI codes."""
        import subprocess

        agent_dir = Path(__file__).parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(agent_dir / "scripts" / "help.py"),
                "content_brain",
                "--plain",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            cwd=str(agent_dir)
        )

        assert result.returncode == 0
        # Should not have ANSI codes
        assert "\033[" not in result.stdout
