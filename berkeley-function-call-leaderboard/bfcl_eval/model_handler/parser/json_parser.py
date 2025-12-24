import json
import re
import time
import signal 
import sys

class TimeoutException(Exception): pass

def _timeout_handler(signum, frame):
    raise TimeoutException("JSON parsing timed out")


def parse_json_function_call(source_code):
    # --- Your existing regex ---
    json_match = re.search(r"\[\s*{.*?}\s*(?:,\s*{.*?}\s*)*\]", source_code, re.DOTALL)
    if json_match:
        source_code = json_match.group(0)

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
            if "function" in function_call and "parameters" in function_call:
                function_name = function_call["function"]
                arguments = function_call["parameters"]
                function_calls.append({function_name: arguments})
            
    return function_calls
