import pytest
from unittest.mock import MagicMock
from skills.ghost_writer import GhostWriterV2
from shared.models import ArticleDraft

def test_ghost_writer_initialization(mock_gemini, mock_brain):
    writer = GhostWriterV2()
    # Inject mocks
    writer.client = mock_gemini
    writer.brain = mock_brain
    writer.researcher.client = mock_gemini
    writer.outliner.client = mock_gemini
    writer.writer.client = mock_gemini
    writer.editor.client = mock_gemini
    
    assert writer.researcher is not None
    assert writer.writer is not None

def test_pipeline_execution(mock_gemini, mock_brain):
    writer = GhostWriterV2()
    writer.client = mock_gemini
    writer.brain = mock_brain
    # We need to ensure sub-agents use the mocked client
    writer.researcher.client = mock_gemini
    writer.outliner.client = mock_gemini
    writer.writer.client = mock_gemini
    writer.editor.client = mock_gemini
    
    topic = {
        "id": "123",
        "topic": "Test Security Guide",
        "content_type": "Guide",
        "target_audience": "CISOs"
    }
    
    result = writer.run_pipeline(topic)
    
    assert result is not None
    assert result["title"] == "Mock Title"
    assert result["qualityScore"] == 95
    
    # Verify call order (implicit via logic flow)
    assert mock_gemini.generate.called # Research & Outline uses generate
    assert mock_gemini.generate_json.called # Writer & Editor use generate_json

def test_writer_validation_failure(mock_gemini):
    """Test that writer handles invalid JSON from LLM."""
    writer = GhostWriterV2()
    writer.writer.client = mock_gemini
    
    # Simulate bad LLM response
    mock_gemini.generate_json.return_value = {"bad_field": "no title"}
    
    topic = {"topic": "Fail", "content_type": "Guide"}
    draft = writer.writer.write_draft(topic, "Outline", "Research")
    
    assert draft is None
