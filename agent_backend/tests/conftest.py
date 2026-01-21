import pytest
from unittest.mock import MagicMock
import sys
import os

# Add root to path so we can import skills
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from skills.gemini_client import GeminiAgent
from skills.content_brain import ContentBrain

@pytest.fixture
def mock_gemini():
    mock = MagicMock(spec=GeminiAgent)
    mock.generate.return_value = "Mocked research content..."
    mock.generate_json.return_value = {
        "title": "Mock Title",
        "description": "Mock Desc",
        "topic": "Test Topic",
        "category": "Security",
        "content_type": "Guide",
        "tags": ["test"],
        "word_count": 1000,
        "sources": [{"id": "1", "title": "Src"}],
        "body": "# Heading\n\nContent...",
        "overall_score": 95,
        "verdict": "PUBLISH"
    }
    return mock

@pytest.fixture
def mock_brain():
    mock = MagicMock(spec=ContentBrain)
    return mock
