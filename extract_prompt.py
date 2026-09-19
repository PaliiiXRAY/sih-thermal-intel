import json
import sys

transcript_path = r'C:\Users\adity\.gemini\antigravity-ide\brain\f2fba8f2-3e18-4c3b-8d56-0709ccc51bb8\.system_generated\logs\transcript_full.jsonl'
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        user_inputs = [json.loads(line) for line in lines if '"type":"USER_INPUT"' in line]
        if user_inputs:
            last_prompt = user_inputs[-1]['content']
            with open('last_user_prompt.txt', 'w', encoding='utf-8') as out:
                out.write(last_prompt)
            print("Successfully extracted last user prompt.")
        else:
            print("No USER_INPUT found.")
except Exception as e:
    print(f"Error: {e}")
