"""
test_utils.py
Validates the JSON sanitization capacities against varied LLM responses.
"""

import os
import json
from unittest.mock import patch, MagicMock
from ai.utils import extract_json, validate_schema, check_restricted_keywords, ReliabilityAuditor

# ---------------------------------------------------------------------------
# AI Utilities: JSON Sanitization & Validation
# Test: extract json from clean markdown blocks
# Test: extract json from raw bracketed input (no markdown)
# Test: extract json fails gracefully on non-json text
# Test: extract json edge cases (None, empty string, multiple blocks)
# Test: validate schema success and failure cases (missing/null keys)
# Test: check restricted keywords content guardrail
# Test: reliability auditor lifecycle and metrics aggregation
# Test: reliability auditor resilience (missing/corrupt/read-only files)
# ---------------------------------------------------------------------------

def test_extract_json_with_clean_markdown():
    """Ensure standard markdown blocks correctly resolve to python structures."""
    payload = "Here is the output:\n```json\n{\"time\": \"14:00\", \"pet\": \"Mochi\"}\n```\nHope this helps!"
    result = extract_json(payload)
    assert result == {"time": "14:00", "pet": "Mochi"}

def test_extract_json_with_missing_markdown():
    """Ensure raw brackets fallback functions appropriately."""
    payload = "I forgot markdown but here: {\"time\": null, \"pet\": \"Luna\"} let me know."
    result = extract_json(payload)
    assert result == {"time": None, "pet": "Luna"}

def test_extract_json_fails_gracefully():
    """Ensure random conversational garbage resolves safely to None."""
    payload = "I am not exactly sure what time you mean. Can you clarify?"
    result = extract_json(payload)
    assert result is None

# ---------------------------------------------------------------------------
# AI Utilities: Schema Validation
# ---------------------------------------------------------------------------

def test_validate_schema_success():
    """Ensure complete payloads pass structural validation."""
    data = {"title": "Walk", "pet": "Mochi", "confidence": 0.9}
    required = ["title", "pet"]
    assert validate_schema(data, required) is True

def test_validate_schema_missing_key():
    """Ensure missing mandatory keys trigger validation failure."""
    data = {"title": "Walk"}
    required = ["title", "pet"]
    assert validate_schema(data, required) is False

def test_validate_schema_null_value():
    """Ensure null values for mandatory keys trigger validation failure."""
    data = {"title": "Walk", "pet": None}
    required = ["title", "pet"]
    assert validate_schema(data, required) is False

# ---------------------------------------------------------------------------
# AI Utilities: Content Guardrails
# ---------------------------------------------------------------------------

def test_check_restricted_keywords_triggered():
    """Ensure medical terminology triggers the content guardrail."""
    payload = "You should consult a veterinarian for a medical diagnosis."
    findings = check_restricted_keywords(payload)
    assert "veterinarian" in findings
    assert "diagnosis" in findings

def test_check_restricted_keywords_clean():
    """Ensure standard pet care advice passes the guardrail."""
    payload = "I suggest taking Mochi for a 30 minute walk."
    findings = check_restricted_keywords(payload)
    assert len(findings) == 0

# ---------------------------------------------------------------------------
# AI Utilities: Reliability Auditor
# ---------------------------------------------------------------------------

def test_reliability_auditor_lifecycle(tmp_path, monkeypatch):
    """Verify metrics are correctly recorded and aggregated in a sandbox environment."""
    # Redirect auditor to a temporary test file
    test_file = tmp_path / "test_metrics.json"
    monkeypatch.setattr(ReliabilityAuditor, "METRICS_FILE", str(test_file))
    
    # 1. Start empty
    summary = ReliabilityAuditor.get_metrics_summary()
    assert summary["count"] == 0
    
    # 2. Record success
    ReliabilityAuditor.record_metric("Test_Tool", confidence=1.0, success=True)
    summary = ReliabilityAuditor.get_metrics_summary()
    assert summary["count"] == 1
    assert summary["score"] == 1.0
    
    # 3. Record failure
    ReliabilityAuditor.record_metric("Test_Tool", confidence=0.0, success=False)
    summary = ReliabilityAuditor.get_metrics_summary()
    assert summary["count"] == 2
    assert summary["score"] == 0.5
    
    # 4. Check per-tool metrics
    tool_metrics = ReliabilityAuditor.get_per_tool_metrics()
    assert len(tool_metrics) == 1
    assert tool_metrics[0]["tool"] == "Test_Tool"
    assert tool_metrics[0]["reliability"] == 0.5

def test_extract_json_edge_cases():
    """Verify robustness against empty or malformed candidates."""
    assert extract_json(None) is None
    assert extract_json("") is None
    
    # Payload with markdown blocks mixed with garbage
    payload = "Try this: {invalid json} then this: ```json\n{\"valid\": \"json\"}\n```"
    result = extract_json(payload)
    assert result == {"valid": "json"}

def test_reliability_auditor_empty_cases(tmp_path, monkeypatch):
    """Verify behavior when metrics file is missing or empty."""
    test_file = tmp_path / "empty_metrics.json"
    monkeypatch.setattr(ReliabilityAuditor, "METRICS_FILE", str(test_file))
    
    # 1. No file exists
    assert ReliabilityAuditor.get_per_tool_metrics() == []
    assert ReliabilityAuditor.get_metrics_summary()["count"] == 0
    
    # 2. File exists but is empty list
    with open(test_file, "w") as f:
        json.dump([], f)
    assert ReliabilityAuditor.get_per_tool_metrics() == []
    assert ReliabilityAuditor.get_metrics_summary()["count"] == 0

def test_reliability_auditor_error_resilience(tmp_path, monkeypatch):
    """Ensure the auditor doesn't crash on corrupted files."""
    test_file = tmp_path / "corrupt.json"
    monkeypatch.setattr(ReliabilityAuditor, "METRICS_FILE", str(test_file))
    
    with open(test_file, "w") as f:
        f.write("definitely not json")
    
    # Should catch exception and return defaults
    assert ReliabilityAuditor.get_metrics_summary()["count"] == 0
    assert ReliabilityAuditor.get_per_tool_metrics() == []

def test_reliability_auditor_record_failure(tmp_path, monkeypatch):
    """Ensure recording failure is caught (e.g., read-only filesystem)."""
    test_file = tmp_path / "readonly.json"
    monkeypatch.setattr(ReliabilityAuditor, "METRICS_FILE", str(test_file))
    
    # Create the directory but maybe mock the open to fail
    from unittest.mock import mock_open
    with patch("builtins.open", side_effect=PermissionError("Read only")):
        # Should not crash, but log error
        ReliabilityAuditor.record_metric("Fail", 0.5)
