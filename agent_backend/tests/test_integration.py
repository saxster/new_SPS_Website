import pytest
import os
import json
import shutil
from unittest.mock import MagicMock
from pathlib import Path

from skills.content_brain import ContentBrain
from skills.ghost_writer import GhostWriterV2
from skills.newsroom_watcher import NewsroomWatcher
from shared.models import ArticleDraft

@pytest.fixture
def temp_env(tmp_path):
    # Setup temp paths
    db_path = tmp_path / "test_brain.db"
    drafts_dir = tmp_path / "drafts"
    output_dir = tmp_path / "output"
    
    drafts_dir.mkdir()
    output_dir.mkdir()
    
    # Mock Config (Monkeypatching config would be better, but we can inject paths)
    # Since our classes allow DI or config lookup, we rely on the fact that 
    # we can pass 'brain' to components. 
    # For directories, NewsroomWatcher reads from config. We need to patch config.
    
    from config.manager import config
    # We can't easily patch the singleton config without a setter or reload
    # But for this test, let's rely on DI where possible or patch the properties if we could.
    # A cleaner way given our refactor:
    
    # Create Brain
    brain = ContentBrain(db_path=str(db_path))
    
    return {
        "root": tmp_path,
        "brain": brain,
        "drafts": drafts_dir,
        "output": output_dir
    }

def test_full_pipeline_flow(temp_env, monkeypatch):
    """
    Test the flow: Brain -> GhostWriter -> Watcher -> Output
    """
    brain = temp_env['brain']
    drafts_dir = temp_env['drafts']
    output_dir = temp_env['output']
    
    # 1. Setup Mock Agents
    mock_client = MagicMock()
    
    # Mock Writer to return a valid ArticleDraft dict
    valid_draft = {
        "title": "Test Security Article",
        "description": "A test article description",
        "body": "# Heading\n\nContent...",
        "category": "Security",
        "tags": ["test"],
        "wordCount": 500,
        "qualityScore": 95.0
    }
    
    # We need to mock the *SubAgents* of GhostWriter, or mock the run_pipeline output?
    # Mocking run_pipeline is easier for integration test of the *Orchestrator's Handoff*, 
    # but strictly we want to test GhostWriter logic.
    # Let's mock the sub-agents methods.
    
    writer_system = GhostWriterV2(client=mock_client, brain=brain)
    writer_system.researcher.research = MagicMock(return_value=["Fact 1"])
    writer_system.outliner.create_outline = MagicMock(return_value=["Section 1"])
    # The writer agent returns an ArticleDraft-like object (Pydantic model usually)
    # But in GhostWriter code: `draft_obj = self.writer.write_draft(...)`
    # Let's return a valid ArticleDraft object
    writer_system.writer.write_draft = MagicMock(return_value=ArticleDraft(**valid_draft))
    writer_system.editor.review = MagicMock(return_value={"overall_score": 95, "verdict": "PUBLISH"})
    writer_system.art.get_header_image = MagicMock(return_value="http://image.com/img.png")
    
    # Force the config paths for the Save Draft step
    # Since GhostWriter.save_draft uses config.get("paths.drafts_dir"), we need to patch it.
    
    # Mock ConfigManager.get
    original_get = None
    from config.manager import config
    
    def mock_config_get(key, default=None):
        if key == "paths.drafts_dir":
            return str(drafts_dir)
        if key == "paths.output_dir":
            return str(output_dir)
        return default
        
    monkeypatch.setattr(config, "get", mock_config_get)
    
    # 2. Add Topic
    topic = {"topic": "AI Security", "target_audience": "CISOs", "gap_score": 10}
    brain.add_topic_proposal(topic)
    
    # 3. Run GhostWriter
    next_topic = brain.get_next_topic_to_write()
    assert next_topic['topic'] == "AI Security"
    
    result = writer_system.run_pipeline(next_topic)
    assert result is not None
    
    filepath = writer_system.save_draft(next_topic['id'], result)
    assert os.path.exists(filepath)
    
    # Check Brain State -> DRAFTED
    # We need to re-fetch to see status change
    # (Implementation detail: get_next_topic_to_write excludes DRAFTED, so it should return None now)
    assert brain.get_next_topic_to_write() is None
    
    # 4. Run Watcher
    watcher = NewsroomWatcher(brain=brain)
    # We need to ensure watcher uses the patched config (it calls config.get in __init__)
    # Since we instantiated watcher *after* patching, it might be okay if we passed the dir.
    # But Watcher.__init__ calls config.get.
    # Let's re-instantiate watcher to be safe with the patch active.
    watcher.drafts_dir = str(drafts_dir)
    watcher.output_dir = str(output_dir)
    
    watcher.scan_and_publish()
    
    # 5. Verify Output
    # Should be moved to archive
    assert not os.path.exists(filepath) 
    assert len(list((drafts_dir / "archive").glob("*.json"))) == 1
    
    # Markdown should exist
    md_files = list(output_dir.glob("*.md"))
    assert len(md_files) == 1
    
    with open(md_files[0], 'r') as f:
        content = f.read()
        # PyYAML might not quote simple strings, check for the title content
        assert "title: Test Security Article" in content or "title: \"Test Security Article\"" in content
        assert "qualityScore: 95.0" in content