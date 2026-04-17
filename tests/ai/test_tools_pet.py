"""
test_tools_pet.py
Verifies pet management AI tools: add, remove, and list functionalities.
"""

import pytest
from unittest.mock import patch, MagicMock
from ai.tools.add_pet import add_pet_tool
from ai.tools.remove_pet import remove_pet_tool
from ai.tools.list_pets import list_pets_tool

# ---------------------------------------------------------------------------
# AI Pet Management Tools
# Test: add pet tool success path
# Test: add pet tool missing age follow-up
# Test: remove pet tool direct name match
# Test: remove pet tool natural language fallback
# Test: list pets tool summary generation
# ---------------------------------------------------------------------------

def test_add_pet_tool_success(mock_persistence, mock_ollama, mock_owner):
    """Ensure valid AI extraction results in a pet add confirmation."""
    json_output = '{"name": "Bella", "species": "dog", "age": 2, "special_needs": ["none"], "confidence": 0.98}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a 2 year old dog named Bella")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_add_confirmation"
    assert result["pet_data"]["name"] == "Bella"
    assert result["pet_data"]["age"] == 2

def test_add_pet_tool_missing_age(mock_persistence, mock_ollama, mock_owner):
    """Ensure missing age triggers a follow-up question."""
    json_output = '{"name": "Bella", "species": "dog", "age": null, "confidence": 0.8}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog named Bella")
    
    assert isinstance(result, str)
    assert "how old is **Bella**" in result

def test_remove_pet_tool_direct_match(mock_persistence, mock_owner):
    """Ensure direct name matches bypass LLM extraction."""
    # Mochi is already in mock_owner.pets
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("Mochi")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_remove_confirmation"
    assert result["pet_name"] == "Mochi"

def test_remove_pet_tool_llm_fallback(mock_persistence, mock_ollama, mock_owner):
    """Ensure natural language removal requests are extracted by LLM."""
    mock_ollama.return_value = mock_ollama.response_class('{"pet_name": "Mochi", "confidence": 0.99}')
    
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("i need to rehome Mochi")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_remove_confirmation"
    assert result["pet_name"] == "Mochi"
    mock_ollama.assert_called_once()

def test_list_pets_tool(mock_persistence, mock_ollama, mock_owner):
    """Ensure listing pets generates a summary string with emojis."""
    mock_ollama.return_value = mock_ollama.response_class("Here are your pets: 🐶 Mochi")
    
    with patch("ai.tools.list_pets.load_data", return_value=mock_owner):
        result = list_pets_tool("show my pets")
    
    assert isinstance(result, str)
    assert "Mochi" in result
    assert "🐶" in result
