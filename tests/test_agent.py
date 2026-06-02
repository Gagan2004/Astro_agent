import sys
import os
import traceback

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.agent import app_graph
from langchain_core.messages import HumanMessage

def test():
    print("Testing agent graph invoke...")
    initial_state = {
        "messages": [HumanMessage(content="Calculate my chart. Born May 15 1993, New Delhi, but I don't know my birth time.")],
        "birth_details": None,
        "chart_data": None,
        "transits_data": None,
        "current_intent": None,
        "error": None
    }
    try:
        result = app_graph.invoke(initial_state)
        print("Success! Result:")
        print(result)
    except Exception as e:
        print("CRITICAL ERROR:")
        print(str(e))
        traceback.print_exc()

if __name__ == "__main__":
    test()
