"""
conftest.py
Global fixtures for AI layer testing, isolating external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from core.models import Owner, Pet

@pytest.fixture
def mock_owner():
    """Provides a sterile Owner object for each test."""
    owner = Owner(name="Test Owner", available_minutes=1440)
    owner.pets = [Pet(name="Mochi", species="dog", age=3)]
    return owner

@pytest.fixture
def mock_session_state():
    """Simulates Streamlit session state with synchronized attribute/dict access."""
    class SessionState(dict):
        def __getattr__(self, key):
            return self.get(key)
        def __setattr__(self, key, value):
            self[key] = value
            
    state = SessionState()
    # Explicitly set the initial state to ensure it's tracked
    state.active_intent = None
    
    with patch("streamlit.session_state", state):
        yield state

@pytest.fixture
def mock_ollama():
    """Intercepts Ollama chat calls."""
    class MockMessage:
        def __init__(self, content):
            self.content = content
    class MockResponse:
        def __init__(self, content):
            self.message = MockMessage(content)
            
    with patch("ollama.chat") as mock:
        mock.response_class = MockResponse
        yield mock

@pytest.fixture
def mock_persistence(mock_owner):
    """Bypasses physical disk I/O for PawPal data."""
    # Patch the sources and the core exports
    with patch("core.persistence.load_data", return_value=mock_owner), \
         patch("core.persistence.save_data"), \
         patch("core.load_data", return_value=mock_owner), \
         patch("core.save_data"):
        yield
