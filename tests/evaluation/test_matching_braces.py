def extract_first_json_block(text: str) -> str:
    start_idx = text.find('{')
    if start_idx == -1:
        return ""
        
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        # Handle string literals to ignore braces inside quotes
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
                    return text[start_idx:i+1]
                    
    return ""

# Test cases
test_1 = 'To answer the user\'s question, we need to compute their birth chart first.\n\n{"name": "geocode_place_tool", "parameters": {"place_name": "New Delhi"}} \n\nThis will help us determine their geographical coordinate alignment.'
test_2 = 'Hello { "name": "test", "val": "nested { braces } in string" } and trailing text { "another": 1 }'

print("Test 1:", repr(extract_first_json_block(test_1)))
print("Test 2:", repr(extract_first_json_block(test_2)))
