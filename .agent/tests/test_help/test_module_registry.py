"""Tests for ModuleRegistry - module auto-discovery."""

import pytest


class TestModuleRegistry:
    """Tests for ModuleRegistry - module auto-discovery."""

    def test_scan_finds_python_files(self, agent_dir):
        """ModuleRegistry.scan() discovers Python files in directories."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # Should find at least some modules
        assert len(modules) > 0
        # Should find known modules like content_brain
        assert "content_brain" in modules

    def test_get_returns_module_by_name(self, agent_dir):
        """ModuleRegistry.get() returns module by name."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        registry.scan()

        module = registry.get("content_brain")
        assert module is not None
        assert module.name == "content_brain"

    def test_get_returns_none_for_unknown_module(self, agent_dir):
        """ModuleRegistry.get() returns None for unknown module."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        registry.scan()

        module = registry.get("nonexistent_module_xyz")
        assert module is None

    def test_search_finds_modules_by_docstring_content(self, agent_dir):
        """ModuleRegistry.search() finds modules containing query text."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        registry.scan()

        # Search for something that should be in content_brain
        results = registry.search("persistent")
        assert len(results) >= 1
        # content_brain mentions "persistent memory"
        module_names = [m.name for m in results]
        assert "content_brain" in module_names

    def test_list_all_returns_sorted_modules(self, agent_dir):
        """ModuleRegistry.list_all() returns all modules sorted by name."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        registry.scan()

        modules = registry.list_all()
        assert len(modules) > 0

        # Check they're sorted
        names = [m.name for m in modules]
        assert names == sorted(names)

    def test_excludes_pycache_directories(self, agent_dir):
        """ModuleRegistry excludes __pycache__ directories."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # No module should have pycache in its path
        for module in modules.values():
            assert "__pycache__" not in str(module.filepath)

    def test_excludes_init_files(self, agent_dir):
        """ModuleRegistry excludes __init__.py files."""
        from scripts.help import ModuleRegistry

        registry = ModuleRegistry(agent_dir)
        modules = registry.scan()

        # No module should be __init__
        for module in modules.values():
            assert module.name != "__init__"
