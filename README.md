# Chatbot (FastAPI + OpenRouter, Python frontend)

A multilingual chatbot with chat history, image understanding, voice input, and dark mode.

- **Backend**: FastAPI (Python) → calls the AI model via **OpenRouter** (currently `google/gemini-3.6-flash`)
- **Frontend**: **NiceGUI** (Python) — no JavaScript/npm required
- A legacy React frontend also exists in `frontend/` but is no longer the primary UI.

## 1. Backend setup

```
cd backend
python -m venv venv
venv\Scripts\activate      (Windows)
source venv/bin/activate   (Mac/Linux)

pip install -r requirements.txt
```

Rename `.env.example` to `.env` and add your **OpenRouter** API key:
```
OPENROUTER_API_KEY=sk-or-v1-your_key_here
FRONTEND_ORIGIN=http://localhost:5173
```
Get a free key at https://openrouter.ai/keys

Run the backend:
```
uvicorn main:app --reload
```
Backend runs at: http://localhost:8000

## 2. Frontend setup (Python — NiceGUI)

In a **separate terminal**:
```
cd frontend-python
python -m venv venv
venv\Scripts\activate      (Windows)
source venv/bin/activate   (Mac/Linux)

pip install -r requirements.txt
python app.py
```
Frontend runs at: http://localhost:8501

Both the backend and this frontend need to be running at the same time, in two separate terminals.

## Features

- **Multilingual replies** — English, Hindi, Marathi, selectable from the top-right dropdown. The bot always replies in the selected language.
- **Animated robot greeting** — waves and speaks a greeting once when the app starts (not on every page refresh), and again whenever you change the language.
- **Chat history sidebar** — "+ New Chat" to start fresh; past chats are saved once you send your first message in them (empty/unsent chats aren't saved). Each chat has a menu to **Save** (export as `.txt`) or **Delete** it individually.
- **Image understanding** — click the "+" icon to attach an image; the AI can see and answer questions about it.
- **Voice input** — click the mic icon, speak your question, and it's transcribed and sent automatically. Requires Chrome or Edge (uses the Web Speech API).
- **Dark/Light mode** — toggle switch next to the language selector.
- **Export chat** — download button next to the dark mode toggle exports the current conversation as a `.txt` file.
- Chat sessions persist per-browser via NiceGUI's storage, but a **fresh new chat always starts** whenever you run the app or refresh the page.

## Notes

- CORS on the backend is locked to `FRONTEND_ORIGIN` in `backend/.env` — update it if you deploy to a different domain or port.
- The OpenRouter free tier has a limited credit balance; `max_tokens` is capped at 1024 per reply in `backend/main.py` to stay within it. Add credits at https://openrouter.ai/settings/credits if you need longer replies.
- Only image attachments are actually sent to the AI for understanding; other file types (PDF, docx, etc.) are currently just noted by name in the message, not read.