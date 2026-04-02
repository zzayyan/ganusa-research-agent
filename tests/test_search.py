from src.services.tavily_client import search_web
import json

try:
    results = search_web('Python langgraph', 1)
    print(json.dumps(results, indent=2))
except Exception as e:
    print("Error:", e)
