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
        base_url="https://aipipe.org/openai/v1"
    )

    prompt = f"""
You are a Python traceback analyzer.

Python code:
{code}

Traceback:
{error}

Find the line number in the user's Python code where the error occurred.

Return ONLY a JSON array of integers.
Example:
[2]

Do not return any explanation or markdown.
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

    # Parse JSON returned by the model
    return [int(x) for x in json.loads(text)]
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
