import json
import re
import time
import signal 
import sys

class TimeoutException(Exception): pass

def _timeout_handler(signum, frame):
    raise TimeoutException("JSON parsing timed out")


def parse_json_function_call(source_code):
    # --- Regex to extract JSON list ---
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
        print(f"--- JSON Parser: UNEXPECTED ERROR during loads(): {e} ---") 
        return []


    parse_duration = time.time() - start_time
    print(f"JSON parsing took {parse_duration:.6f} seconds.") 

    function_calls = []
    if not isinstance(json_dict, list): 
        if isinstance(json_dict, dict):
            json_dict = [json_dict] # Wrap single object in a list
        else:
            print(f"--- JSON Parser: Expected list or dict after loads(), got {type(json_dict)} ---")
            return [] 

    for function_call in json_dict:
        if isinstance(function_call, dict):
            # Support both "function"/"parameters" and "name"/"arguments" naming conventions
            function_name = function_call.get("function") or function_call.get("name")
            arguments = function_call.get("parameters") or function_call.get("arguments")

            if function_name and arguments is not None:
                # STRICT MODE: We pass arguments exactly as found.
                # If the model outputted a string (e.g. "arguments": "{...}"), we pass the string.
                # This will intentionally fail the AST Checker, marking the generation as Invalid.
                function_calls.append({function_name: arguments})
            
    return function_calls
