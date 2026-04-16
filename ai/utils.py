"""
utils.py
Dedicated utility functions for isolating and parsing robust JSON logic from conversational text.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

def extract_json(llm_output: str) -> dict | None:
    """
    Extracts strictly validated JSON dictionaries enclosed in markdown from raw LLM responses.
    Ignores conversational boilerplate. Returns None if no valid JSON dictionary is found.
    """
    if not llm_output:
        return None

    # Identify JSON objects wrapped in standard markdown blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_output, re.DOTALL | re.IGNORECASE)
    
    raw_json_str = ""
    if match:
        raw_json_str = match.group(1)
    else:
        # Fallback: Isolate the first major bracket block if markdown formatting was omitted
        fallback_match = re.search(r'(\{.*\})', llm_output, re.DOTALL)
        if fallback_match:
            raw_json_str = fallback_match.group(1)
        else:
            logger.warning("[ai/utils] No identifiable JSON structure extracted from payload.")
            return None

    try:
        data = json.loads(raw_json_str)
        if isinstance(data, dict):
            return data
        else:
            logger.warning("[ai/utils] Extracted JSON resolved to a list or primitive, expecting strict dictionary.")
            return None
    except json.JSONDecodeError as err:
        logger.warning(f"[ai/utils] JSON parsing failure detected: {err}")
        return None
