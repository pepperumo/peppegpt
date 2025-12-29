"""
Pytest configuration file for backend_rag_pipeline tests.
Sets up environment variables and mocks for all tests.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# Override environment variables for tests BEFORE any imports
# This ensures database state management is disabled and Docker paths are not used
os.environ['RAG_PIPELINE_ID'] = ''  # Disable database state management
os.environ['RAG_WATCH_DIRECTORY'] = ''  # Disable Docker path override
os.environ['RAG_WATCH_FOLDER_ID'] = ''  # Disable Docker folder override


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Fixture to ensure environment variables are set for each test."""
    with patch.dict(os.environ, {
        'RAG_PIPELINE_ID': '',
        'RAG_WATCH_DIRECTORY': '',
        'RAG_WATCH_FOLDER_ID': '',
    }):
        yield


@pytest.fixture(autouse=True)
def mock_state_manager():
    """Fixture to mock the state manager to return None (file-based mode)."""
    with patch('common.state_manager.get_state_manager', return_value=None):
        yield
