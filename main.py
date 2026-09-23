import os
import json
import traceback
from io import StringIO
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


# Create FastAPI application
app = FastAPI()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request model
class CodeRequest(BaseModel):
    code: str


# Execute Python code
def execute_python_code(code: str) -> dict:
    old_stdout = __import__("sys").stdout
    __import__("sys").stdout = StringIO()

    try:
        exec(code)

        output = __import__("sys").stdout.getvalue()

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
        __import__("sys").stdout = old_stdout


# AI error analysis
def analyze_error_with_ai(code: str, traceback_text: str) -> List[int]:

    client = OpenAI(
        api_key=os.environ["AIPIPE_TOKEN"],
        base_url="https://aipipe.org/openai/v1"
    )

    models = client.models.list()

    print("AVAILABLE MODELS:")

    for model in models.data:
        print(model.id)

    raise Exception("Check Render logs for available models")
# Main API endpoint
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
# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Code Interpreter API is running"
    }
