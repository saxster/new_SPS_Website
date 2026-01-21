import os
import json
import pytest
import shutil
from pathlib import Path
from skills.newsroom_watcher import NewsroomWatcher
from skills.content_brain import ContentBrain
from shared.models import ArticleDraft

# Mock config to use a temp dir for output
@pytest.fixture
def mock_dirs(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    output = tmp_path / "output"
    drafts.mkdir()
    output.mkdir()
    return drafts, output

def test_newsroom_watcher_end_to_end(mock_dirs, monkeypatch):
    drafts_dir, output_dir = mock_dirs
    
    # 1. Setup Brain (In-Memory for test isolation)
    # This prevents hitting the real DB and errors like 'no such column' if schema differs
    brain = ContentBrain(db_path=":memory:")
    
    # Create a dummy topic in DB to match the article (FK constraint)
    # ContentBrain.mark_as_published needs a topic_id.
    # mark_as_published: UPDATE articles ...; UPDATE topics ... WHERE id = (SELECT topic_id FROM articles...)
    # So we need to ensure the article exists in DB first?
    # NewsroomWatcher._process_file calls: self.brain.mark_as_published(slug)
    # But mark_as_published expects the article to ALREADY exist in the DB (created by GhostWriter).
    # Since we are skipping GhostWriter in this test, we must manually seed the DB.
    
    topic_id = "test-topic-id"
    brain.add_topic_proposal({"topic": "Test Article Integration", "target_audience": "General", "gap_score": 10})
    
    # Seed the article as DRAFT
    draft_data = {
        "title": "Test Article Integration",
        "description": "A test description",
        "author": "Tester",
        "category": "Security",
        "contentType": "Analysis",
        "tags": ["test", "ci"],
        "body": "## Section 1\nContent here.",
        "wordCount": 100,
        "qualityScore": 85.5,
        "revision": 2,
        "sources": [{"id": "S1", "title": "Source 1"}]
    }
    
    # We can use brain.mark_as_drafted to seed it
    brain.mark_as_drafted(topic_id, "test_article", "path/to/fake", draft_data)

    # 2. Create the JSON file
    draft_path = drafts_dir / "test_article.json"
    with open(draft_path, "w") as f:
        # Need to handle date serialization if any?
        # draft_data here doesn't have dates, so json.dump is fine
        json.dump(draft_data, f)
        
    # 3. Patch NewsroomWatcher Config
    import config.manager
    original_get = config.manager.config.get
    
    def mock_get(key, default=None):
        if key == "paths.drafts_dir":
            return str(drafts_dir)
        if key == "paths.output_dir":
            return str(output_dir)
        return original_get(key, default)
        
    monkeypatch.setattr(config.manager.config, "get", mock_get)
    
    # 4. Instantiate Watcher with Injected Brain
    watcher = NewsroomWatcher(brain=brain)
    
    # Run
    watcher.scan_and_publish(skip_quality=True)
    
    # Assert Output
    expected_md = output_dir / "test_article.md"
    assert expected_md.exists()
    
    content = expected_md.read_text()
    
    # Check Frontmatter (YAML format)
    assert 'title: Test Article Integration' in content
    assert 'contentType: Analysis' in content
    
    # Check that draft was moved to archive
    assert not draft_path.exists()
    assert (drafts_dir / "archive" / "test_article.json").exists()
    
    # Check DB status
    cur = brain.conn.cursor()
    cur.execute("SELECT status FROM articles WHERE slug = 'test_article'")
    row = cur.fetchone()
    assert row['status'] == 'PUBLISHED'