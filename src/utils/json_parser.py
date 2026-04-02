import json
import re

def extract_json(extracted_text: str) -> dict:
    match = re.search(r"\{.*\}", extracted_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(0))
