import os
import threading

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Set OPENROUTER_MODEL in backend/.env to pin a specific model (e.g. google/gemini-3.6-flash).
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

# ChatOpenAI works with any OpenAI-compatible API, so base_url points to OpenRouter.
llm = ChatOpenAI(
    model=MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    max_tokens=250,
    timeout=30,
    max_retries=2,
)

# The agent = model + tools + system prompt + memory (checkpointer).
agent = create_agent(
    model=llm,
    tools=[],  # add your @tool functions here later
    system_prompt=(
        "You are a helpful assistant. "
        "Always read the earlier messages in this conversation before replying. "
        "If you are running a step-by-step exercise or quiz, keep track of which "
        "step you are on: judge the user's latest answer against the question you "
        "most recently asked, and never repeat a question the user has already "
        "answered correctly."
    ),
    checkpointer=InMemorySaver(),  # memory per thread_id, resets on restart
)

# One lock per session_id, so two overlapping messages can't clash.
_locks: dict[str, threading.Lock] = {}


def build_user_content(text: str, images: list[str]):
    """Plain text, or an OpenAI-style multimodal content list when images are attached."""
    if not images:
        return text
    content = [{"type": "text", "text": text}]
    for img in images:
        content.append({"type": "image_url", "image_url": {"url": img}})
    return content


def ask_openrouter(user_text: str, images: list[str], language: str, session_id: str) -> str:
    """Send one turn to the agent. The checkpointer loads and saves this
    session's history using thread_id. Returns the reply text, or an
    "Error: ..." string on failure."""
    lang_name = LANGUAGE_NAMES.get(language, "English")
    # system_prompt is fixed, so the language rule goes into the user message.
    user_text = f"(Reply only in {lang_name}, using natural {lang_name} script.)\n{user_text}"
    content = build_user_content(user_text, images)

    with _locks.setdefault(session_id, threading.Lock()):
        try:
            print("[chat] calling agent...")
            result = agent.invoke(
                {"messages": [HumanMessage(content=content)]},
                config={"configurable": {"thread_id": session_id}},
            )
            last = result["messages"][-1]
            model_used = (getattr(last, "response_metadata", None) or {}).get("model_name")
            print(f"[chat] answered by model: {model_used or MODEL}")
            return last.content
        except Exception as e:
            return f"Error: {str(e)}"