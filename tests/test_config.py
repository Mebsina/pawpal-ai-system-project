"""
test_config.py
Verifies that essential system constants and care guidelines are present and correctly typed.
"""

import pytest
import config

def test_config_model_name_is_set():
    """Assert the default model name is correct."""
    assert isinstance(config.MODEL_NAME, str)
    assert config.MODEL_NAME == "llama3.2:3b"

def test_config_temperatures_are_valid():
    """Ensure temperatures are numeric and within standard bounds."""
    assert isinstance(config.STRICT_TEMPERATURE, (float, int))
    assert 0.0 <= config.STRICT_TEMPERATURE <= 1.0
    assert config.STRICT_TEMPERATURE == 0.0
    
    assert isinstance(config.CHAT_TEMPERATURE, (float, int))
    assert 0.0 <= config.CHAT_TEMPERATURE <= 1.0

def test_config_priority_order_is_deterministic():
    """Validate the priority weight map used by the scheduler."""
    assert isinstance(config.PRIORITY_ORDER, dict)
    assert config.PRIORITY_ORDER["low"] == 1
    assert config.PRIORITY_ORDER["medium"] == 2
    assert config.PRIORITY_ORDER["high"] == 3

def test_config_pet_care_guidelines_present():
    """Verify that species-specific care guidelines are seeded for the Smart Scheduler."""
    guidelines = config.STANDARD_CARE_GUIDELINES
    assert "dog" in guidelines
    assert "cat" in guidelines
    assert "general" in guidelines
    
    # Check that dog guidelines mention feed and walk (load-bearing for tests)
    dog_text = " ".join(guidelines["dog"]).lower()
    assert "feed" in dog_text
    assert "walk" in dog_text
