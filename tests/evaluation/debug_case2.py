import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.agent import app_graph
from langchain_core.messages import HumanMessage

initial_state = {
    "messages": [HumanMessage(content="I want to know about my career. I was born on Jan 1 1990 at 12:00 PM.")],
    "birth_details": None,
    "chart_data": None,
    "transits_data": None,
    "current_intent": None,
    "error": None
}

print("Invoking graph for case_02...")
start = time.time()
try:
    for event in app_graph.stream(initial_state, config={"recursion_limit": 8}):
        print(f"\n--- Event at {time.time() - start:.2f}s ---")
        print(json.dumps({k: str(v)[:200] for k, v in event.items()}, indent=2))
except Exception as e:
    print(f"Exception after {time.time() - start:.2f}s: {e}")
