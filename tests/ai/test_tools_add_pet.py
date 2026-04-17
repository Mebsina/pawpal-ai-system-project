import pytest
from unittest.mock import patch, MagicMock
from ai.tools.add_pet import add_pet_tool

# ---------------------------------------------------------------------------
# Add Pet Tool
# Test: successful extraction and confirmation payload
# Test: missing pet age triggers a follow-up question
# Test: missing pet name triggers a follow-up question
# Test: duplicate pet name prevention
# Test: invalid species fallback to selection menu
# Test: Ollama service failure fallback
# Test: malformed JSON extraction failure resilience
# Test: chat history context passing
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_add_pet_tool_success(mock_ollama, mock_owner):
    """Ensure valid AI extraction results in a pet add confirmation."""
    json_output = '{"name": "Bella", "species": "dog", "age": 2, "special_needs": ["none"], "confidence": 0.98}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a 2 year old dog named Bella")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_add_confirmation"
    assert result["pet_data"]["name"] == "Bella"
    assert result["pet_data"]["age"] == 2

@pytest.mark.usefixtures("mock_persistence")
def test_add_pet_tool_missing_age(mock_ollama, mock_owner):
    """Ensure missing age triggers a follow-up question."""
    json_output = '{"name": "Bella", "species": "dog", "age": null, "confidence": 0.8}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog named Bella")
    
    assert isinstance(result, str)
    assert "how old is **Bella**" in result

def test_add_pet_tool_ollama_failure(mock_ollama, mock_owner):
    """Ensure API failures are handled gracefully."""
    mock_ollama.side_effect = Exception("Ollama disconnected")
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog")
    assert "trouble connecting to the AI" in result

def test_add_pet_tool_extraction_failure(mock_ollama, mock_owner):
    """Ensure malformed JSON results in a parsing error message."""
    mock_ollama.return_value = mock_ollama.response_class("This is not JSON")
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog")
    assert "couldn't parse the pet details" in result

def test_add_pet_tool_missing_name(mock_ollama, mock_owner):
    """Ensure missing name results in a follow-up question."""
    mock_ollama.return_value = mock_ollama.response_class('{"name": null, "species": "dog", "age": 2, "confidence": 0.9}')
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a 2 year old dog")
    assert "What is their name?" in result

def test_add_pet_tool_duplicate_name(mock_ollama, mock_owner):
    """Ensure duplicate pet names are rejected."""
    # Assuming 'Mochi' is in mock_owner.pets from conftest.py
    mock_ollama.return_value = mock_ollama.response_class('{"name": "Mochi", "species": "dog", "age": 3, "confidence": 0.99}')
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog named Mochi")
    assert "already registered" in result

def test_add_pet_tool_invalid_species(mock_ollama, mock_owner):
    """Ensure invalid species trigger a clarification question."""
    mock_ollama.return_value = mock_ollama.response_class('{"name": "Rex", "species": "dragon", "age": 5, "confidence": 0.9}')
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dragon named Rex")
    assert "something **other**?" in result

def test_add_pet_tool_with_history(mock_ollama, mock_owner):
    """Verify chat history context is respected."""
    mock_ollama.return_value = mock_ollama.response_class('{"name": "Rex", "species": "dog", "age": 2, "confidence": 0.9}')
    history = [{"role": "user", "content": "I have a dog"}]
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        add_pet_tool("his name is Rex", chat_history=history)
    
    called_messages = mock_ollama.call_args.kwargs["messages"]
    assert any(m["content"] == "I have a dog" for m in called_messages)
