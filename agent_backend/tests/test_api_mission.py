"""
Tests for the /mission/run API endpoint with pillar filtering.

TDD: These tests define the expected behavior before implementation.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add root to path so we can import api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock chromadb before importing api
mock_chromadb = MagicMock()
sys.modules["chromadb"] = mock_chromadb
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()

from fastapi.testclient import TestClient


class TestMissionRunEndpoint:
    """Tests for the /mission/run endpoint with pillar filtering."""

    @pytest.fixture
    def client(self):
        """Create test client with API key authentication."""
        # Set API key for testing
        os.environ["SPS_API_KEY"] = "test-api-key-12345"
        from api import app

        return TestClient(app)

    @pytest.fixture
    def api_key_header(self):
        """Return the API key header for authenticated requests."""
        return {"X-API-Key": "test-api-key-12345"}

    def test_mission_run_accepts_pillars_parameter(self, client, api_key_header):
        """POST /mission/run should accept pillars parameter in request body."""
        with patch("api.run_script") as mock_run:
            response = client.post(
                "/mission/run",
                headers=api_key_header,
                json={"pillars": ["scam_watch", "economic_security"]},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["pillars"] == ["scam_watch", "economic_security"]

    def test_mission_run_accepts_max_articles_parameter(self, client, api_key_header):
        """POST /mission/run should accept max_articles parameter."""
        with patch("api.run_script") as mock_run:
            response = client.post(
                "/mission/run",
                headers=api_key_header,
                json={"max_articles": 5},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["max_articles"] == 5

    def test_mission_run_passes_pillars_to_script(self, client, api_key_header):
        """POST /mission/run should pass pillars as command-line args to script."""
        with patch("api.run_script") as mock_run:
            response = client.post(
                "/mission/run",
                headers=api_key_header,
                json={"pillars": ["scam_watch"]},
            )

            assert response.status_code == 200
            # Verify run_script was called with pillars argument
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            script_args = (
                call_args[0][1]
                if len(call_args[0]) > 1
                else call_args[1].get("args", [])
            )
            assert "--pillars" in script_args
            assert "scam_watch" in script_args

    def test_mission_run_passes_max_articles_to_script(self, client, api_key_header):
        """POST /mission/run should pass max_articles as command-line args."""
        with patch("api.run_script") as mock_run:
            response = client.post(
                "/mission/run",
                headers=api_key_header,
                json={"max_articles": 2},
            )

            assert response.status_code == 200
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            script_args = (
                call_args[0][1]
                if len(call_args[0]) > 1
                else call_args[1].get("args", [])
            )
            assert "--max-articles" in script_args
            assert "2" in script_args

    def test_mission_run_works_without_parameters(self, client, api_key_header):
        """POST /mission/run should work with empty body (defaults)."""
        with patch("api.run_script") as mock_run:
            response = client.post(
                "/mission/run",
                headers=api_key_header,
            )

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "Mission started in background"

    def test_mission_run_requires_api_key(self, client):
        """POST /mission/run should require API key authentication."""
        response = client.post("/mission/run", json={"pillars": ["scam_watch"]})

        # Should fail without API key
        assert response.status_code in [403, 422]

    def test_mission_run_rejects_invalid_api_key(self, client):
        """POST /mission/run should reject invalid API key."""
        response = client.post(
            "/mission/run",
            headers={"X-API-Key": "wrong-key"},
            json={"pillars": ["scam_watch"]},
        )

        assert response.status_code == 403


class TestMissionRequestModel:
    """Tests for the MissionRequest Pydantic model."""

    def test_mission_request_has_pillars_field(self):
        """MissionRequest should have optional pillars field."""
        os.environ["SPS_API_KEY"] = "test-api-key-12345"
        from api import MissionRequest

        request = MissionRequest(pillars=["scam_watch"])
        assert request.pillars == ["scam_watch"]

    def test_mission_request_has_max_articles_field(self):
        """MissionRequest should have max_articles field with default."""
        os.environ["SPS_API_KEY"] = "test-api-key-12345"
        from api import MissionRequest

        request = MissionRequest()
        assert request.max_articles == 3  # Default value

    def test_mission_request_pillars_optional(self):
        """MissionRequest pillars should be optional (None by default)."""
        os.environ["SPS_API_KEY"] = "test-api-key-12345"
        from api import MissionRequest

        request = MissionRequest()
        assert request.pillars is None

    def test_mission_request_accepts_multiple_pillars(self):
        """MissionRequest should accept multiple pillars."""
        os.environ["SPS_API_KEY"] = "test-api-key-12345"
        from api import MissionRequest

        request = MissionRequest(
            pillars=["scam_watch", "economic_security", "personal_security"]
        )
        assert len(request.pillars) == 3
