import json
import re
import time
import signal 
import sys
import multiprocessing

class TimeoutException(Exception): pass

def _timeout_handler(signum, frame):
    raise TimeoutException("JSON parsing timed out")

def _regex_worker(source_code, return_dict):
    # Your exact original regex
    json_match = re.search(r"\[\s*{.*?}\s*(?:,\s*{.*?}\s*)*\]", source_code, re.DOTALL)
    if json_match:
        return_dict['match'] = json_match.group(0)

def extract_json_array(source_code):
    # Find the first '[' or '{' to handle both array and object formats
    start_idx_array = source_code.find('[')
    start_idx_obj = source_code.find('{')
    
    if start_idx_array == -1 and start_idx_obj == -1:
        return source_code
        
    # Start from whichever comes first
    valid_indices = [i for i in (start_idx_array, start_idx_obj) if i != -1]
    start_idx = min(valid_indices)
    
    open_bracket = source_code[start_idx]
    close_bracket = ']' if open_bracket == '[' else '}'
    
    count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(source_code)):
        char = source_code[i]
        
        if not in_string:
            if char == '"':
                in_string = True
            elif char == open_bracket:
                count += 1
            elif char == close_bracket:
                count -= 1
                # If we've closed the outermost bracket, return the exact slice
                if count == 0:
                    return source_code[start_idx:i+1]
        else:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
                
    # Fallback if it ends abruptly without a matching closing bracket
    return source_code[start_idx:]

def parse_json_function_call(source_code):
    # --- Your existing regex ---\
#    source_code = extract_json_array(source_code)
#    json_match = re.search(r"\[\s*{.*?}\s*(?:,\s*{.*?}\s*)*\]", source_code, re.DOTALL)
#    if json_match:
#        source_code = json_match.group(0)

    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    p = multiprocessing.Process(target=_regex_worker, args=(source_code, return_dict))
    
    p.start()
    p.join(2) # Give the regex up to 2 seconds to finish
    
    if p.is_alive():
        # If it's still running, it hit catastrophic backtracking! Kill it and skip.
        p.terminate()
        p.join()
        print(f"--- JSON Parser: Regex Catastrophic Backtracking TIMEOUT. Skipping sample. ---")
        return []

    if 'match' in return_dict:
        source_code = return_dict['match']


    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(5)

    start_time = time.time()
    try:
        json_dict = json.loads(source_code)
        signal.alarm(0) 
    except json.JSONDecodeError as e:
        signal.alarm(0) 
        print(f"--- JSON Parser: JSONDecodeError ---") 
        return []
    except TimeoutException as e:
        signal.alarm(0) 
        print(f"--- JSON Parser: TIMEOUT ---") 
        return [] 
    except Exception as e: 
        signal.alarm(0)
        print(f"--- JSON Parser: UNEXPECTED ERROR during loads(): {e} ---") # Optional: Add logging
        return []


    parse_duration = time.time() - start_time
    print(f"JSON parsing took {parse_duration:.6f} seconds.") # Your existing print

    function_calls = []
    if not isinstance(json_dict, list): 
        if isinstance(json_dict, dict):
            json_dict = [json_dict] # Wrap single object in a list
        else:
            print(f"--- JSON Parser: Expected list or dict after loads(), got {type(json_dict)} ---")
            return [] # Cannot process non-list/dict types

    for function_call in json_dict:
        if isinstance(function_call, dict):
            # Support both "function"/"parameters" and "name"/"arguments" naming conventions
            function_name = function_call.get("function") or function_call.get("name")
            arguments = function_call.get("parameters") or function_call.get("arguments")

            if function_name and arguments is not None:
                # If arguments is a string (stringified JSON), parse it into a dict
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        # If string parsing fails, keep it as is or handle appropriately
                        print(f"--- JSON Parser: Warning - Could not parse stringified arguments for {function_name} ---")
                        pass

                function_calls.append({function_name: arguments})
            
    return function_calls
