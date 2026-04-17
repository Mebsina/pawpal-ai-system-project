"""
test_utils.py
Validates the JSON sanitization capacities against varied LLM responses.
"""

import os
import json
from ai.utils import extract_json, validate_schema, check_restricted_keywords, ReliabilityAuditor

# ---------------------------------------------------------------------------
# AI Utilities: JSON Sanitization & Validation
# Test: extract json from clean markdown
# Test: extract json from raw bracketed input
# Test: extract json fails gracefully on garbage
# Test: validate schema success and failure cases
# Test: check restricted keywords guardrail
# Test: reliability auditor lifecycle and aggregation
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
