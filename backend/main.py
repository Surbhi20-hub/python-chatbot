import base64
import io
import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str  # "user" or "assistant"
    text: str


class FileAttachment(BaseModel):
    name: str
    type: str
    data: str  # base64 data URL, e.g. "data:application/pdf;base64,...."


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    language: str = "en"
    images: list[str] = []  # base64 data URLs, e.g. "data:image/png;base64,...."
    files: list[FileAttachment] = []


def extract_file_text(f: FileAttachment) -> str:
    """Decode a base64 data URL and pull out readable text, per file type."""
    try:
        raw_b64 = f.data.split(",", 1)[1] if "," in f.data else f.data
        raw_bytes = base64.b64decode(raw_b64)

        if f.type == "text/plain" or f.name.lower().endswith(".txt"):
            return raw_bytes.decode("utf-8", errors="ignore")

        if f.type == "application/pdf" or f.name.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except ImportError:
                return "[Could not read PDF: install with 'pip install pypdf']"
            reader = PdfReader(io.BytesIO(raw_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        if f.name.lower().endswith(".docx"):
            try:
                import docx
            except ImportError:
                return "[Could not read .docx: install with 'pip install python-docx']"
            document = docx.Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in document.paragraphs)

        return f"[Unsupported file type: {f.type or 'unknown'}]"
    except Exception as e:
        return f"[Could not read file {f.name}: {e}]"


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


@app.post("/chat")
def chat(req: ChatRequest):
    lang_name = LANGUAGE_NAMES.get(req.language, "English")

    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. Always reply only in {lang_name}, using natural {lang_name} script/spelling, regardless of what language the user writes in.",
        }
    ]
    messages += [{"role": m.role, "content": m.text} for m in req.history]

    user_text = req.message
    if req.files:
        file_sections = []
        for f in req.files:
            extracted = extract_file_text(f)
            # Keep each file's content within a reasonable size so the request stays small
            extracted = extracted[:8000]
            file_sections.append(f"--- Content of {f.name} ---\n{extracted}")
        user_text = user_text + "\n\n" + "\n\n".join(file_sections)

    if req.images:
        content = [{"type": "text", "text": user_text}]
        for img in req.images:
            content.append({"type": "image_url", "image_url": {"url": img}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_text})

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-3.6-flash",
                "messages": messages,
                "max_tokens": 1024,
            },
            timeout=30,
        )
        if res.status_code != 200:
            return {"reply": f"Error {res.status_code}: {res.text}"}
        data = res.json()
        reply = data["choices"][0]["message"]["content"]
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}


@app.get("/")
def root():
    return {"status": "backend running"}