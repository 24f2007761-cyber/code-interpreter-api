import os
import json
from typing import List
from openai import OpenAI


def analyze_error_with_ai(code: str, traceback_text: str) -> List[int]:

    client = OpenAI(
        api_key=os.environ["AIPIPE_TOKEN"],
        base_url="https://aipipe.org/openai/v1"
    )

    prompt = f"""
Analyze this Python code and traceback.

CODE:
{code}

TRACEBACK:
{traceback_text}

Identify the exact line number(s) where the error occurred.

Return ONLY a JSON array of integers.
Example:
[2]
"""

    response = client.chat.completions.create(
        model="openai/gpt-4.1-nano",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    text = response.choices[0].message.content.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return [int(x) for x in json.loads(text)]
