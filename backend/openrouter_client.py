"""Talks to the AI model via OpenRouter."""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-3.6-flash"

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def build_system_message(language: str) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    return {
        "role": "system",
        "content": (
            f"You are a helpful assistant. Always reply only in {lang_name}, "
            f"using natural {lang_name} script/spelling, regardless of what "
            f"language the user writes in."
        ),
    }


def ask_openrouter(messages: list[dict], max_retries: int = 1) -> str:
    """Send a full conversation to OpenRouter and return the reply text.

    On any failure (network error, bad status code, unexpected response
    shape) this returns a readable "Error: ..." string instead of raising,
    so the endpoint can always send something back to the frontend.

    Automatically retries once on OpenRouter's transient 429 "admission
    control" rate limit, waiting briefly before trying again (capped short
    so a rate-limit doesn't itself make replies feel slow).
    """
    last_error = "Error: unknown failure"

    for attempt in range(max_retries + 1):
        try:
            res = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "max_tokens": 500,
                },
                timeout=30,
            )

            if res.status_code == 429 and attempt < max_retries:
                wait_seconds = int(res.headers.get("Retry-After", 3))
                time.sleep(min(wait_seconds, 5))
                continue

            if res.status_code != 200:
                return f"Error {res.status_code}: {res.text}"

            data = res.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            last_error = f"Error: {str(e)}"

    return last_error