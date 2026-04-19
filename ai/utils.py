"""
utils.py
Dedicated utility functions for isolating and parsing robust JSON logic from conversational text.
"""

import json
import re
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class ReliabilityAuditor:
    """
    Automated evaluation module for tracking and scoring AI reliability,
    intent classification certainty, and agentic refinement efficiency.
    """
    METRICS_FILE = "data/reliability_metrics.json"

    @classmethod
    def record_metric(cls, tool: str, confidence: float, turns: int = 1, success: bool = True):
        """
        Persists a reliability event to the local datastore.
        """
        try:
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            
            metrics = []
            if os.path.exists(cls.METRICS_FILE):
                with open(cls.METRICS_FILE, "r") as f:
                    metrics = json.load(f)

            new_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool,
                "confidence": round(confidence, 3),
                "turns": turns,
                "success": success
            }
            metrics.append(new_entry)

            # Limit history to last 1000 entries for performance
            metrics = metrics[-1000:]

            with open(cls.METRICS_FILE, "w") as f:
                json.dump(metrics, f, indent=2)
                
            logger.info(f"[ai/utils] Reliability Metric Logged: {tool} (Conf: {confidence}, Success: {success})")
        except Exception as e:
            logger.error(f"[ai/utils] Failed to record reliability metric: {e}")

    @classmethod
    def get_metrics_summary(cls) -> dict:
        """
        Computes aggregate reliability scores across the system.
        """
        if not os.path.exists(cls.METRICS_FILE):
            return {"score": 0.0, "count": 0, "avg_confidence": 0.0}

        try:
            with open(cls.METRICS_FILE, "r") as f:
                metrics = json.load(f)
            
            if not metrics:
                return {"score": 0.0, "count": 0, "avg_confidence": 0.0}

            success_count = sum(1 for m in metrics if m["success"])
            total_confidence = sum(m["confidence"] for m in metrics)
            count = len(metrics)

            return {
                "score": round(success_count / count, 2),
                "count": count,
                "avg_confidence": round(total_confidence / count, 2),
                "last_update": metrics[-1]["timestamp"] if metrics else None
            }
        except Exception:
            return {"score": 0.0, "count": 0, "avg_confidence": 0.0}

    @classmethod
    def get_per_tool_metrics(cls) -> list[dict]:
        """
        Calculates overall average reliability and confidence grouped by tool.
        """
        if not os.path.exists(cls.METRICS_FILE):
            return []
        
        try:
            with open(cls.METRICS_FILE, "r") as f:
                metrics = json.load(f)
            
            if not metrics:
                return []

            tool_stats = {} # {tool_name: {"total_confidence": float, "successes": int, "count": int}}
            
            for m in metrics:
                tool = m["tool"]
                if tool not in tool_stats:
                    tool_stats[tool] = {"total_confidence": 0.0, "successes": 0, "count": 0}
                
                tool_stats[tool]["total_confidence"] += m["confidence"]
                if m["success"]:
                    tool_stats[tool]["successes"] += 1
                tool_stats[tool]["count"] += 1

            results = []
            for tool, stats in tool_stats.items():
                results.append({
                    "tool": tool,
                    "avg_confidence": round(stats["total_confidence"] / stats["count"], 2),
                    "reliability": round(stats["successes"] / stats["count"], 2),
                    "count": stats["count"]
                })
            
            # Sort by count (usage volume) descending
            return sorted(results, key=lambda x: x["count"], reverse=True)
        except Exception:
            return []


def extract_json(llm_output: str) -> dict | None:
    """
    Extracts strictly validated JSON dictionaries from raw LLM responses.
    Handles markdown blocks, raw strings, and multiple nested instances 
    by prioritizing the most complete structural block.
    """
    if not llm_output:
        return None

    # Step 1: Attempt to isolate JSON from markdown blocks
    # Prioritizes content within ```json or ``` fences
    markdown_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', llm_output, re.DOTALL | re.IGNORECASE)
    
    candidates = []
    if markdown_blocks:
        candidates.extend(markdown_blocks)
    
    # Step 2: Fallback to scanning for any major brace blocks if no fences found
    # This also helps catch blocks if the LLM forgot to close a fence
    brace_matches = re.findall(r'(\{.*\})', llm_output, re.DOTALL)
    if brace_matches:
        candidates.extend(brace_matches)

    # Step 3: Iterate through candidates and find the first one that parses as a dictionary
    for candidate in candidates:
        try:
            # Clean possible trailing boilerplate occasionally returned outside fences
            candidate = candidate.strip()
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    logger.warning(f"[ai/utils] JSON extraction failed for payload: {llm_output[:100]}...")
    return None

def validate_schema(data: dict, required_keys: list[str]) -> bool:
    """
    Enforces strict structural requirements on AI-generated payloads.
    Ensures that all mandatory fields are present and non-null.
    """
    if not isinstance(data, dict):
        return False
        
    for key in required_keys:
        if key not in data or data[key] is None:
            logger.warning(f"[ai/utils] Validation failed: Missing or null critical key '{key}'")
            return False
            
    return True

def check_restricted_keywords(text: str) -> list[str]:
    """
    Scans AI generated output for restricted or biased terminology.
    Identifies if the AI is drifting into medical advice or hallucinating 
    forbidden external resources.
    """
    # Prohibit medical diagnosing or external veterinary references in automated plan responses
    RESTRICTED = [
        "veterinarian", "diagnosis", "doctor", "medical advice",
        "prescription", "treatment", "medicine", "consult"
    ]
    
    findings = []
    clean_text = text.lower()
    for word in RESTRICTED:
        if word in clean_text:
            findings.append(word)
            
    if findings:
        logger.warning(f"[ai/utils] Guardrail Triggered: Restricted keywords detected: {findings}")
        
    return findings
