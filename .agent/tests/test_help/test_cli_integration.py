"""Integration tests for CLI behavior."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIIntegration:
    """Integration tests for CLI behavior."""

    def test_main_list_modules_exits_zero(self, agent_dir):
        """Running help.py without args lists modules and exits 0."""
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

    def test_main_specific_module_shows_man_page(self, agent_dir):
        """Running help.py with module name shows man page."""
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

    def test_main_unknown_module_exits_nonzero(self, agent_dir):
        """Running help.py with unknown module exits non-zero."""
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

    def test_main_search_finds_modules(self, agent_dir):
        """Running help.py --search finds relevant modules."""
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

    def test_main_plain_flag_removes_colors(self, agent_dir):
        """Running help.py --plain removes ANSI codes."""
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
