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

# NOTE: this currently has no effect, since the NiceGUI frontend calls this
# backend server-side via the `requests` library (send() -> requests.post(...)),
# not from browser JavaScript. CORS only matters for real browser fetch/XHR
# calls. Left in place in case you later add a JS-based frontend that calls
# this API directly from the browser.
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


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    language: str = "en"
    # FIX: this field didn't exist before, so Pydantic silently dropped any
    # "images" key sent by the frontend and attachments were never seen by
    # the model. Each entry is a data: URI (base64) as produced by the
    # frontend's FileReader.readAsDataURL().
    images: list[str] = []


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

    # FIX: when images are attached, build a multimodal content array
    # (OpenRouter/OpenAI-style: a list of {type: text|image_url} blocks)
    # instead of a plain string, so the model actually receives them.
    # NOTE: this only works if OPENROUTER_MODEL below points at a
    # vision-capable model.
    if req.images:
        content = [{"type": "text", "text": req.message}]
        for img in req.images:
            content.append({"type": "image_url", "image_url": {"url": img}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": req.message})

    # FIX: specific free-tier model slugs on OpenRouter (like the previous
    # "google/gemini-2.0-flash-exp:free") get retired/rotated out with little
    # notice, which is what caused the 404 you hit. "openrouter/free" is
    # OpenRouter's own router: it automatically picks from whichever free
    # models are currently live, and filters for the features you need
    # (image understanding, tool calling), so it won't go stale the same way.
    # If you'd rather pin a specific paid model for reliability/quality,
    # check https://openrouter.ai/models for a current id and swap it in.
    OPENROUTER_MODEL = "openrouter/free"

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
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