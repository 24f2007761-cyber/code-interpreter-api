import os
import traceback
from io import StringIO
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from google.genai import types


# --------------------------------------------------
# FastAPI app
# --------------------------------------------------

app = FastAPI()


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request model
# --------------------------------------------------

class CodeRequest(BaseModel):
    code: str


# --------------------------------------------------
# AI response model
# --------------------------------------------------

class ErrorAnalysis(BaseModel):
    error_lines: List[int]


# --------------------------------------------------
# Part 1: Execute Python code
# --------------------------------------------------

def execute_python_code(code: str) -> dict:
    """
    Execute Python code and return exact output.

    Returns:
        {
            "success": bool,
            "output": str
        }
    """

    import sys

    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)

        output = sys.stdout.getvalue()

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


# --------------------------------------------------
# Part 2: AI Error Analysis
# --------------------------------------------------

def analyze_error_with_ai(code: str, traceback_text: str) -> List[int]:
    """
    Use Gemini to identify the Python error line number(s).
    """

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY")
    )

    prompt = f"""
Analyze this Python code and its error traceback.

Identify the exact line number(s) in the user's Python code
where the error occurred.

CODE:
{code}

TRACEBACK:
{traceback_text}

Return the line number(s) where the error is located.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "error_lines": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.INTEGER
                        )
                    )
                },
                required=["error_lines"]
            )
        )
    )

    result = ErrorAnalysis.model_validate_json(
        response.text
    )

    return result.error_lines


# --------------------------------------------------
# Part 3: API endpoint
# --------------------------------------------------

@app.post("/code-interpreter")
def code_interpreter(request: CodeRequest):

    execution = execute_python_code(request.code)

    # Successful execution
    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    # Error occurred -> call AI
    error_lines = analyze_error_with_ai(
        request.code,
        execution["output"]
    )

    return {
        "error": error_lines,
        "result": execution["output"]
    }


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Code Interpreter API is running"
    }
