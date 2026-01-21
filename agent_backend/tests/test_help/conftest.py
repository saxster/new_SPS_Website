"""Shared fixtures and configuration for help module tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file that auto-cleans up."""
    created_files = []

    def _create(content: str):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        f.write(content)
        f.close()
        created_files.append(f.name)
        return Path(f.name)

    yield _create

    # Cleanup
    for filepath in created_files:
        try:
            os.unlink(filepath)
        except OSError:
            pass


@pytest.fixture
def agent_dir():
    """Return the .agent directory path."""
    return Path(__file__).parent.parent.parent
