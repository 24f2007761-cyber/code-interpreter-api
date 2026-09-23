import os
import sys
import traceback
from io import StringIO
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str


class ErrorAnalysis(BaseModel):
    error_lines: List[int]


def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    stdout = StringIO()
    stderr = StringIO()

    sys.stdout = stdout
    sys.stderr = stderr

    try:
        exec(code, {})

        output = stdout.getvalue() + stderr.getvalue()

        return {
            "success": True,
            "output": output
        }

    except Exception:
        output = traceback.format_exc()

        return {
            "success": False,
            "output": output
        }

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def analyze_error_with_ai(code: str, error: str) -> List[int]:

    client = OpenAI(
        api_key=os.environ["AIPIPE_TOKEN"],
        base_url="https://aipipe.org/openrouter/v1"
    )

    prompt = f"""
Analyze the following Python code and traceback.

CODE:
{code}

TRACEBACK:
{error}

Identify the exact source-code line number where the error occurred.

Return ONLY valid JSON in this exact format:
{{"error_lines": [3]}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-4.1-nano",
        messages=[
            {
                "role": "system",
                "content": "You identify Python error line numbers."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    import json

    content = response.choices[0].message.content.strip()

    result = json.loads(content)

    return result["error_lines"]

@app.post("/code-interpreter")
def code_interpreter(request: CodeRequest):

    execution = execute_python_code(request.code)

    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    error_lines = analyze_error_with_ai(
        request.code,
        execution["output"]
    )

    return {
        "error": error_lines,
        "result": execution["output"]
    }
