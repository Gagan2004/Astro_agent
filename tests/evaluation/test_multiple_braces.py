import json

def extract_json_blocks(text: str):
    """Yields all matched JSON brace blocks from a string."""
    idx = 0
    while True:
        start_idx = text.find('{', idx)
        if start_idx == -1:
            break
            
        brace_count = 0
        in_string = False
        escape = False
        found_block = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            # Handle string literals
            if char == '"' and not escape:
                in_string = not in_string
            elif char == '\\' and in_string:
                escape = not escape
            else:
                escape = False
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        yield text[start_idx:i+1]
                        idx = i + 1
                        found_block = True
                        break
        if not found_block:
            idx = start_idx + 1

# Test
text = 'I will use {our geocoding tool} to find: {"name": "geocode_place_tool", "parameters": {"place_name": "London"}} and some text.'
print("Blocks found:")
for b in extract_json_blocks(text):
    print("-", repr(b))
