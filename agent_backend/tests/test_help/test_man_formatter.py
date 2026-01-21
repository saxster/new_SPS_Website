"""Tests for ManFormatter - man page style output."""

from pathlib import Path

import pytest


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
