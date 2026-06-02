import requests
import json
import time

url = "http://localhost:11434/api/generate"
payload = {
    "model": "llama3.1:8b",
    "prompt": "Hello! Introduce yourself briefly as a warm spiritual companion.",
    "stream": False
}

print("Sending request to Ollama...")
start = time.time()
try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Time taken: {time.time() - start:.2f}s")
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(data.get("response"))
except Exception as e:
    print(f"Error: {e}")
