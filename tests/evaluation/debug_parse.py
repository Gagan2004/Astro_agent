import json
import re

content = 'To answer the user\'s question, we need to compute their birth chart first.\n\n{"name": "geocode_place_tool", "parameters": {"place_name": "New Delhi"}} \n\nThis will help us determine their geographical coordinate alignment. I will then compute the birth chart using these coordinates.\n\nBlessings.'

print(f"Content length: {len(content)}")
start_idx = content.find('{')
end_idx = content.rfind('}')
print(f"start_idx: {start_idx}, end_idx: {end_idx}")

json_str = content[start_idx:end_idx+1]
print("Extracted json_str:")
print(repr(json_str))

try:
    data = json.loads(json_str)
    print("Parsed successfully:")
    print(data)
except Exception as e:
    print(f"Failed to parse: {e}")
