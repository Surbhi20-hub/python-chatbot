
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from file_utils import FileAttachment, extract_file_text
from openrouter_client import ask_openrouter

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:8501")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str  # identifies the conversation; LangChain keeps its memory keyed on this
    language: str = "en"
    images: list[str] = []  # base64 data URLs, e.g. "data:image/png;base64,...."
    files: list[FileAttachment] = []


@app.post("/chat")
def chat(req: ChatRequest):
    user_text = req.message
    if req.files:
        file_sections = []
        for f in req.files:
            extracted = extract_file_text(f)
            # Keep each file's content within a reasonable size so the request stays small
            extracted = extracted[:8000]
            file_sections.append(f"--- Content of {f.name} ---\n{extracted}")
        user_text = user_text + "\n\n" + "\n\n".join(file_sections)

    reply = ask_openrouter(user_text, req.images, req.language, req.session_id)
    return {"reply": reply}


@app.get("/")
def root():
    return {"status": "backend running"}
