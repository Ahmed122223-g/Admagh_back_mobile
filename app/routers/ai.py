# app/routers/ai.py
import base64
import json
import os
from typing import List, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# --- Pydantic Models ---
class AnalyzedTask(BaseModel):
    title: str = Field(..., description="The concise title of the task.")
    description: str = Field(..., description="A detailed description of the task.")
    priority: Literal['urgent', 'important', 'medium', 'unnecessary'] = Field(..., description="The priority of the task.")
    category: str = Field(..., description="A relevant category for the task (e.g., 'Work', 'Learning', 'Personal').")
    estimated_hours: float = Field(..., description="The estimated time in hours to complete the task.")
    due_date: str = Field(..., description="The suggested due date for the task in 'YYYY-MM-DD' format.")

class UserInput(BaseModel):
    language: str = 'en'
    input_text: Optional[str] = None
    file_base64: Optional[str] = None
    file_mimetype: Optional[str] = None

# --- API Router ---

router = APIRouter(
    prefix="/ai",
    tags=["الذكاء الاصطناعي (Smart Assistant)"],
)

# --- Helper Functions ---

from datetime import date

def get_gemini_prompt(language: str) -> str:
    """Constructs the detailed prompt for the Gemini API."""
    today = date.today().strftime("%Y-%m-%d")
    return f"""
        You are an expert project manager and personal assistant.
        The current date is {today}. Your task is to analyze the user's request and break it down into actionable tasks.

        For EACH task, you MUST provide the following fields in a JSON object:
        - \"title\": A concise name for the task.
        - \"description\": A detailed description.
        - \"priority\": Must be one of: 'urgent', 'important', 'medium', 'unnecessary'.
        - \"category\": A relevant category (e.g., 'Work', 'Learning', 'Personal').
        - \"estimated_hours\": A float representing the time estimate.
        - \"due_date\": A suggested due date in 'YYYY-MM-DD' format. The date must be on or after the current date ({today}).

        IMPORTANT RULES:
        1.  If the user provides a large, high-level goal (e.g., 'learn a new skill'), break it down into at least 3 smaller, sequential sub-tasks. Schedule the first sub-task within the next 1-3 days. Spread subsequent tasks logically over the following days or weeks, not months in the future, unless the goal is exceptionally large.
        2.  If the user provides a simple, single-action request (e.g., 'remind me to buy milk'), create a single task and schedule it for today or tomorrow.
        3.  The user's request language is '{language}'. All text fields in your response ('title', 'description', 'category') MUST be in this language.
        4.  Your response MUST be ONLY a valid JSON array `[]` containing one or more of the task objects. Do NOT include any other text, explanations, or markdown formatting like ```json.
    """

def parse_gemini_response(response: httpx.Response) -> List[AnalyzedTask]:
    """Parses the JSON response from Gemini and validates it."""
    try:
        result = response.json()
        text_content = result["candidates"][0]["content"]["parts"][0]["text"]
        
        # Strip markdown JSON block if present
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0].strip()

        tasks_data = json.loads(text_content)
        
        # Validate that the data is a list of objects matching the Pydantic model
        validated_tasks = [AnalyzedTask(**task) for task in tasks_data]
        return validated_tasks
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        print("Error parsing Gemini response:", response.text)
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {e}")


# --- API Endpoint ---

@router.post("/process-input", response_model=List[AnalyzedTask])
async def process_user_input(data: UserInput):
    """
    Processes user input (text, audio, or image) to generate a list of tasks.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API key is not configured on the server.")

    if not data.input_text and not data.file_base64:
        raise HTTPException(status_code=400, detail="No input provided. Please provide text or a file.")

    prompt = get_gemini_prompt(data.language)
    parts = [{"text": prompt}]

    # --- Prepare Content for Gemini ---
    if data.file_base64 and data.file_mimetype:
        encoded_file = data.file_base64
        
        if "audio" in data.file_mimetype:
            # For audio, we add a specific instruction to transcribe first
            parts.append({"text": "Please first transcribe the following audio file, then perform the task analysis on the transcribed text."})
            parts.append({"inline_data": {"mime_type": data.file_mimetype, "data": encoded_file}})
        elif "image" in data.file_mimetype:
            parts.append({"inline_data": {"mime_type": data.file_mimetype, "data": encoded_file}})
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an audio or image file.")

    if data.input_text:
        parts.append({"text": f"User's text input: \n---\n{data.input_text}---"})

    payload = {"contents": [{"parts": parts}]}

    # --- Call Gemini API ---
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(GEMINI_API_URL, json=payload, params={"key": GEMINI_API_KEY})
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print("Gemini API error response:", e.response.text)
            raise HTTPException(status_code=e.response.status_code, detail=f"Error from AI service: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=504, detail=f"Failed to connect to AI service: {e}")

    return parse_gemini_response(response)