import sys
import os
import json

# Tambahkan root directory ke sys.path agar folder 'src' bisa terdeteksi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.tavily_client import search_web
try:
    results = search_web('Python langgraph', 1)
    print(json.dumps(results, indent=2))
except Exception as e:
    print("Error:", e)
