import uuid
import httpx
from nicegui import ui, app

BACKEND_URL = "http://localhost:8000/chat"

# In-memory flag: resets every time you (re)run `python app.py`,
# but stays True across page refreshes within the same running app.
_greeted_once = False

LANGUAGES = [
    {"code": "en", "label": "English", "greeting": "Hi"},
    {"code": "hi", "label": "Hindi", "greeting": "Namaste"},
    {"code": "mr", "label": "Marathi", "greeting": "Namaskar"},
]

# BCP-47 speech-recognition tags per language, used by the mic button
VOICE_LANG_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
}

FILE_PICKER_JS = """
return new Promise((resolve) => {
    const inp = document.getElementById('hidden-file-input');
    inp.value = '';
    inp.onchange = () => {
        const files = Array.from(inp.files);
        if (files.length === 0) { resolve([]); return; }
        Promise.all(files.map(f => new Promise((res) => {
            const reader = new FileReader();
            reader.onload = () => res({name: f.name, type: f.type, data: reader.result});
            reader.readAsDataURL(f);
        }))).then(resolve);
    };
    inp.click();
});
"""

CUSTOM_CSS = """
<style>
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, Helvetica, Arial, sans-serif; background: #f4f6f8; transition: background 0.3s ease; }

.chat-page-row { height: 100vh; width: 100vw; margin: 0; padding: 0; overflow: hidden; }

.sidebar { width: 300px; height: 100vh; background: #202225; color: #eee; padding: 20px 16px; flex-shrink: 0; }
.new-chat-btn {
  width: 100%; font-size: 17px; font-weight: 700; padding: 16px 20px;
  border-radius: 14px; text-transform: none;
}
.history-title { font-size: 13px; text-transform: uppercase; color: #999; margin: 26px 4px 14px; letter-spacing: 0.5px; }
.history-list { width: 100%; gap: 8px; overflow-y: auto; }
.history-item-row {
  display: flex; align-items: center; justify-content: space-between;
  border-radius: 12px; gap: 4px; width: 100%;
}
.history-item-row:hover { background: #2c2f33; }
.history-item-row.active { background: #4a90e2; }
.history-item {
  flex: 1; padding: 14px 16px; font-size: 16px; color: #ccc; cursor: pointer;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.history-item-row.active .history-item { color: white; }
.menu-btn {
  opacity: 0.7; min-width: 28px; width: 28px; height: 28px; padding: 0; color: #ccc;
  font-size: 20px; line-height: 1; flex-shrink: 0; margin-right: 2px;
}
.menu-btn:hover { opacity: 1; }

.character-wrap {
  position: fixed; z-index: 30;
  transition: left 1s ease, top 1s ease, bottom 1s ease, transform 1s ease;
  pointer-events: none;
}
.character-wrap.greeting { left: 50%; top: 45%; bottom: auto; transform: translate(-50%, -50%) scale(1.5); }
.character-wrap.small { left: 20px; top: auto; bottom: 20px; transform: scale(0.55); }
.character-svg { width: 100px; height: 140px; display: block; }
.character-wrap.greeting .character-body { animation: dance 0.6s ease-in-out infinite; }
@keyframes dance {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-8px) rotate(-4deg); }
  50% { transform: translateY(0) rotate(0deg); }
  75% { transform: translateY(-8px) rotate(4deg); }
}
.arm-flip { transform-origin: 27px 52px; transition: transform 0.5s ease; }
.character-wrap.greeting .arm-flip { animation: wavehand 0.6s ease-in-out infinite; }
@keyframes wavehand {
  0%   { transform: rotate(-90deg); }
  25%  { transform: rotate(-60deg); }
  50%  { transform: rotate(-90deg); }
  75%  { transform: rotate(-120deg); }
  100% { transform: rotate(-90deg); }
}

.main-area { flex: 1; height: 100vh; min-width: 0; overflow: hidden; }
.top-bar {
  align-items: center; justify-content: space-between; padding: 22px 32px; background: #fff;
  border-bottom: 1px solid #e2e2e2; width: 100%; gap: 16px; transition: background 0.3s ease, border-color 0.3s ease;
}
.top-right-controls { display: flex; align-items: center; gap: 18px; }
.lang-select { min-width: 140px; }

.page-title { font-size: 32px; font-weight: 800; color: #1a1a1a; margin: 0; }

.mind-prompt {
  position: fixed; left: 50%; top: 45%; transform: translate(-50%, -50%);
  font-size: 44px; font-weight: 700; color: #333; z-index: 14; text-align: center;
  transition: opacity 0.4s ease; pointer-events: none;
}
.mind-prompt.hidden { opacity: 0; }

.messages-area { max-height: 0; opacity: 0; overflow-y: auto; transition: all 0.5s ease; width: 100%; padding: 40px 48px 16px; }
.messages-area.visible { flex: 1; max-height: 100%; opacity: 1; }

.msg-row { width: 100%; max-width: 860px; margin: 16px auto; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.msg-bubble { max-width: 70%; padding: 16px 22px; border-radius: 16px; font-size: 17px; line-height: 1.6; white-space: pre-wrap; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.msg-row.user .msg-bubble { background: #4a90e2; color: white; border-bottom-right-radius: 4px; }
.msg-row.assistant .msg-bubble { background: white; color: #333; border: 1px solid #e8e8e8; border-bottom-left-radius: 4px; }
.msg-img { max-width: 220px; border-radius: 10px; margin-top: 6px; display: block; }

.input-wrap-col { width: 100%; display: flex; justify-content: center; }
.input-area { width: 100%; padding: 24px 48px 60px; align-items: center; flex-wrap: nowrap; justify-content: center; }
.input-area.centered { position: fixed; left: 50%; top: 50%; transform: translate(-50%, 0%); width: auto; padding-top: 30px; justify-content: center; z-index: 16; flex-direction: column; }

.attachment-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; max-width: 700px; }
.attachment-chip {
  background: #e2eefc; color: #2a5fa5; padding: 4px 10px; border-radius: 14px; font-size: 12px;
  display: flex; align-items: center; gap: 6px;
}
.attachment-chip .remove-chip { cursor: pointer; font-weight: bold; }

.input-container { position: relative; flex: 1; max-width: 860px; margin: 0 auto; display: flex; align-items: center; }
.chat-input { width: 100%; font-size: 21px; background: #fff; border-radius: 32px; box-shadow: 0 1px 6px rgba(0,0,0,0.12); }
.chat-input .q-field__control { min-height: 66px !important; padding-left: 62px !important; padding-right: 116px !important; border-radius: 32px !important; }
.chat-input .q-field__control:before, .chat-input .q-field__control:after { border: none !important; }

.attach-btn { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); width: 42px; height: 42px; min-width: 42px; border-radius: 12px; padding: 0; z-index: 3; }
.mic-btn {
  position: absolute; right: 58px; top: 50%; transform: translateY(-50%); width: 40px; height: 40px;
  min-width: 40px; border-radius: 50%; padding: 0; z-index: 10; border: none; background: transparent;
  display: flex; align-items: center; justify-content: center; cursor: pointer; color: #555; font-size: 22px;
  pointer-events: auto;
}
.mic-btn:hover { background: rgba(0,0,0,0.08); }
.mic-btn.recording { color: #ff5f5f; background: rgba(255,95,95,0.12); }
.send-btn-inside { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 44px; height: 44px; min-width: 44px; border-radius: 12px; padding: 0; z-index: 3; }

/* dark mode */
body.dark-mode { background: #17181a; }
body.dark-mode .main-area { background: #17181a; }
body.dark-mode .top-bar { background: #202225; border-color: #333; }
body.dark-mode .welcome-title { color: #eee; }
body.dark-mode .sidebar { background: #101113; }
body.dark-mode .msg-row.assistant .msg-bubble { background: #2c2d30; color: #eee; border-color: #3a3b3e; }
body.dark-mode .chat-input .q-field__control { background: #26272a; }
body.dark-mode .chat-input input { color: #eee; }
body.dark-mode .chat-input .q-field__native::placeholder { color: #888; }
body.dark-mode .page-title { color: #f0f0f0; }
body.dark-mode .attach-btn, body.dark-mode .mic-btn, body.dark-mode .menu-btn { color: #ddd; }
body.dark-mode .history-title { color: #777; }
</style>
"""

ROBOT_SVG = """
<div class="character-body">
<svg viewBox="0 0 100 140" class="character-svg" xmlns="http://www.w3.org/2000/svg">
  <line x1="50" y1="5" x2="50" y2="15" stroke="#888" stroke-width="3"/>
  <circle cx="50" cy="4" r="4" fill="#ff5f5f"/>
  <rect x="30" y="15" width="40" height="30" rx="6" fill="#b0bec5"/>
  <rect x="38" y="25" width="8" height="8" fill="#2196f3"/>
  <rect x="54" y="25" width="8" height="8" fill="#2196f3"/>
  <rect x="32" y="48" width="36" height="45" rx="8" fill="#78909c"/>
  <circle cx="50" cy="68" r="6" fill="#4a90e2"/>
  <rect x="36" y="95" width="10" height="30" rx="3" fill="#555"/>
  <rect x="54" y="95" width="10" height="30" rx="3" fill="#555"/>
  <rect x="68" y="50" width="10" height="32" rx="4" fill="#90a4ae"/>
  <g class="arm-flip">
    <rect x="22" y="50" width="10" height="32" rx="4" fill="#90a4ae"/>
  </g>
</svg>
</div>
"""


def new_session():
    return {"id": str(uuid.uuid4()), "title": "New chat", "messages": []}


@ui.page("/")
def main_page():
    ui.add_head_html('<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">')
    ui.add_head_html(CUSTOM_CSS)
    ui.html('<input type="file" id="hidden-file-input" multiple accept="image/*,.pdf,.txt,.docx" style="display:none">')
    storage = app.storage.user

    if not storage.get("sessions"):
        storage["sessions"] = []
    if "dark" not in storage:
        storage["dark"] = False
    if "language" not in storage:
        storage["language"] = "en"

    # Always start a brand-new (unsaved) chat whenever the app runs or the page refreshes
    draft = new_session()
    storage["draft_session"] = draft
    storage["current_session_id"] = draft["id"]

    dark = ui.dark_mode(value=storage["dark"])
    ui.run_javascript(f"document.body.classList.toggle('dark-mode', {str(storage['dark']).lower()})")
    ui.run_javascript(f"window.__voiceLang = '{VOICE_LANG_MAP.get(storage['language'], 'en-IN')}';")

    pending_attachments = []  # list of {"name", "type", "data"} picked but not yet sent

    def current_session():
        d = storage.get("draft_session")
        if d and d["id"] == storage["current_session_id"]:
            return d
        return next((s for s in storage["sessions"] if s["id"] == storage["current_session_id"]), None)

    def switch_to_new_draft():
        fresh = new_session()
        storage["draft_session"] = fresh
        storage["current_session_id"] = fresh["id"]

    def export_session(sess):
        if not sess:
            return
        lines = [f"{'You' if m['role'] == 'user' else 'Bot'}: {m['text']}" for m in sess["messages"]]
        content = "\n".join(lines) if lines else "No messages yet."
        ui.download(content.encode("utf-8"), filename=f"{sess['title'] or 'chat'}.txt")

    with ui.row().classes("chat-page-row").style("gap:0"):
        with ui.column().classes("sidebar"):
            def start_new_chat():
                switch_to_new_draft()
                render_history.refresh()
                render_chat.refresh()

            ui.button("+ New Chat", on_click=start_new_chat).classes("new-chat-btn")
            ui.label("HISTORY").classes("history-title")

            @ui.refreshable
            def render_history():
                with ui.column().classes("history-list"):
                    for s in storage["sessions"]:
                        active = "active" if s["id"] == storage["current_session_id"] else ""

                        def make_loader(sid):
                            def loader():
                                storage["current_session_id"] = sid
                                render_history.refresh()
                                render_chat.refresh()
                            return loader

                        def make_delete(sid):
                            def deleter():
                                storage["sessions"] = [x for x in storage["sessions"] if x["id"] != sid]
                                if storage["current_session_id"] == sid:
                                    switch_to_new_draft()
                                render_history.refresh()
                                render_chat.refresh()
                            return deleter

                        def make_save(sid):
                            def saver():
                                sess = next((x for x in storage["sessions"] if x["id"] == sid), None)
                                export_session(sess)
                            return saver

                        with ui.row().classes(f"history-item-row {active}"):
                            ui.label(s["title"] or "New chat").classes("history-item").on(
                                "click", make_loader(s["id"])
                            )
                            with ui.button("\u22ee").props("flat round dense").classes("menu-btn"):
                                with ui.menu():
                                    ui.menu_item("Save", on_click=make_save(s["id"]))
                                    ui.menu_item("Delete", on_click=make_delete(s["id"]))

            render_history()

        char_container = ui.html(ROBOT_SVG).classes("character-wrap small")

        with ui.column().classes("main-area").style("gap:0"):
            with ui.row().classes("top-bar"):
                ui.label("Welcome to Chatbot").classes("page-title")
                with ui.row().classes("top-right-controls"):
                    def toggle_dark(e):
                        storage["dark"] = e.value
                        dark.value = e.value
                        ui.run_javascript(
                            f"document.body.classList.toggle('dark-mode', {str(e.value).lower()})"
                        )

                    ui.switch("Dark", value=storage["dark"], on_change=toggle_dark)

                    def export_current():
                        export_session(current_session())

                    ui.button(icon="download", on_click=export_current).props("flat round dense")

                    def on_lang_change(e):
                        storage["language"] = e.value
                        ui.run_javascript(
                            f"window.__voiceLang = '{VOICE_LANG_MAP.get(e.value, 'en-IN')}';"
                        )
                        greet()

                    ui.select(
                        {l["code"]: l["label"] for l in LANGUAGES},
                        value=storage["language"],
                        on_change=on_lang_change,
                    ).classes("lang-select")

            messages_box = ui.column().classes("messages-area")
            mind_prompt = ui.label("What's on your mind?").classes("mind-prompt")
            input_row = ui.row().classes("input-area centered")

            @ui.refreshable
            def render_chat():
                sess = current_session()
                has_started = bool(sess and sess["messages"])
                mind_prompt.classes(replace="mind-prompt hidden" if has_started else "mind-prompt")
                messages_box.classes(replace=f"messages-area {'visible' if has_started else ''}")
                input_row.classes(replace="input-area" if has_started else "input-area centered")
                messages_box.clear()
                with messages_box:
                    for m in (sess["messages"] if sess else []):
                        with ui.row().classes(f'msg-row {m["role"]}'):
                            with ui.column().classes("msg-bubble"):
                                if m.get("text"):
                                    ui.label(m["text"])
                                for img in m.get("images", []):
                                    ui.image(img).classes("msg-img")

            render_chat()

            with input_row:
                with ui.column().classes("input-wrap-col"):

                    @ui.refreshable
                    def render_attachments():
                        if not pending_attachments:
                            return
                        with ui.row().classes("attachment-chips"):
                            for idx, a in enumerate(pending_attachments):
                                with ui.row().classes("attachment-chip"):
                                    ui.label(a["name"])

                                    def make_remove(i):
                                        def remover():
                                            pending_attachments.pop(i)
                                            render_attachments.refresh()
                                        return remover

                                    ui.label("x").classes("remove-chip").on("click", make_remove(idx))

                    render_attachments()

                    with ui.element("div").classes("input-container"):

                        async def pick_files():
                            result = await ui.run_javascript(FILE_PICKER_JS, timeout=120.0)
                            if result:
                                pending_attachments.extend(result)
                                render_attachments.refresh()

                        ui.button(icon="add", on_click=pick_files).props(
                            "flat round dense"
                        ).classes("attach-btn")

                        text_input = ui.input(placeholder="Type your message...").classes("chat-input").props(
                            "debounce=0 outlined id=chat-native-input"
                        )

                        async def send(e=None):
                            msg = text_input.value.strip() if text_input.value else ""
                            if not msg and not pending_attachments:
                                return
                            sess = current_session()
                            history = [{"role": m["role"], "text": m.get("text", "")} for m in sess["messages"]]

                            image_data = [a["data"] for a in pending_attachments if a["type"].startswith("image/")]
                            doc_files = [
                                {"name": a["name"], "type": a["type"], "data": a["data"]}
                                for a in pending_attachments if not a["type"].startswith("image/")
                            ]
                            other_names = [f["name"] for f in doc_files]
                            display_text = msg
                            if other_names:
                                note = " (attached: " + ", ".join(other_names) + ")"
                                display_text = (msg + note) if msg else note.strip()

                            sess["messages"].append(
                                {"role": "user", "text": display_text, "images": image_data}
                            )

                            if storage.get("draft_session") and storage["draft_session"]["id"] == sess["id"]:
                                sess["title"] = (msg or "Attachment")[:30]
                                storage["sessions"].insert(0, sess)
                                storage["draft_session"] = None

                            text_input.value = ""
                            pending_attachments.clear()
                            render_attachments.refresh()
                            render_chat.refresh()
                            render_history.refresh()

                            try:
                                async with httpx.AsyncClient(timeout=90) as client:
                                    res = await client.post(
                                        BACKEND_URL,
                                        json={
                                            "message": msg or "Please describe the attached content.",
                                            "history": history,
                                            "language": storage["language"],
                                            "images": image_data,
                                            "files": doc_files,
                                        },
                                    )
                                reply = res.json().get("reply", "Error: no reply")
                            except Exception as ex:
                                reply = f"Error: {ex}"

                            sess["messages"].append({"role": "assistant", "text": reply})
                            render_chat.refresh()

                        text_input.on("keydown.enter", send)

                        mic_btn_id = "mic-native-btn"

                        def on_voice_result(e):
                            transcript = e.args if isinstance(e.args, str) else (e.args[0] if e.args else "")
                            if transcript:
                                text_input.value = (text_input.value or "") + transcript
                                ui.timer(0.05, send, once=True)

                        def on_voice_error(e):
                            err = e.args if isinstance(e.args, str) else (e.args[0] if e.args else "")
                            if err == "not-allowed":
                                ui.notify("Microphone permission was blocked. Allow it in your browser and click the mic again.", type="warning")
                            elif err == "no-speech":
                                ui.notify("Didn't catch that — try again.", type="warning")
                            elif err:
                                ui.notify(f"Voice input error: {err}", type="warning")

                        ui.on("voice_result", on_voice_result)
                        ui.on("voice_error", on_voice_error)

                        ui.html(f"""
                            <button id="{mic_btn_id}" class="mic-btn material-icons"
                                style="font-family:'Material Icons','Material Icons Round',sans-serif; font-weight:normal; font-style:normal; line-height:1; letter-spacing:normal; text-transform:none; white-space:nowrap; word-wrap:normal; direction:ltr; -webkit-font-feature-settings:'liga'; font-feature-settings:'liga';"
                                title="Voice input" type="button">mic</button>
                        """)

                        ui.add_body_html(f"""
                            <script>
                            (function() {{
                                function wireMicButton() {{
                                    var btn = document.getElementById('{mic_btn_id}');
                                    if (!btn || btn.dataset.wired) return;
                                    btn.dataset.wired = '1';
                                    btn.addEventListener('click', function() {{
                                        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                                        if (!SR) {{
                                            alert('Voice input is not supported in this browser. Please use Chrome or Edge.');
                                            return;
                                        }}
                                        if (btn.classList.contains('recording')) return;
                                        var rec = new SR();
                                        rec.lang = window.__voiceLang || 'en-IN';
                                        rec.continuous = false;
                                        rec.interimResults = false;
                                        rec.maxAlternatives = 1;
                                        btn.classList.add('recording');
                                        rec.onresult = function(event) {{
                                            if (typeof emitEvent === 'function') {{
                                                emitEvent('voice_result', event.results[0][0].transcript);
                                            }}
                                        }};
                                        rec.onerror = function(event) {{
                                            btn.classList.remove('recording');
                                            if (typeof emitEvent === 'function') {{
                                                emitEvent('voice_error', event.error);
                                            }}
                                        }};
                                        rec.onend = function() {{ btn.classList.remove('recording'); }};
                                        try {{ rec.start(); }} catch (err) {{ btn.classList.remove('recording'); }}
                                    }});
                                }}
                                var tries = 0;
                                var timer = setInterval(function() {{
                                    tries++;
                                    var btn = document.getElementById('{mic_btn_id}');
                                    if (btn) {{ wireMicButton(); clearInterval(timer); }}
                                    if (tries > 40) clearInterval(timer);
                                }}, 100);
                            }})();
                            </script>
                        """)

                        ui.button(icon="send", on_click=send).classes("send-btn-inside")

    def greet():
        lang = next(l for l in LANGUAGES if l["code"] == storage["language"])
        char_container.classes(replace="character-wrap greeting")
        # Always use the same fixed voice/accent (en-IN) to say the greeting,
        # regardless of the selected UI language, so "Hi", "Namaste" and
        # "Namaskar" all sound like the same voice rather than switching accents.
        ui.run_javascript(f"""
            const u = new SpeechSynthesisUtterance("{lang['greeting']}");
            u.lang = "en-IN";
            const voices = speechSynthesis.getVoices();
            const v = voices.find(v => v.lang === "en-IN") || voices.find(v => v.lang.startsWith("en")) || voices[0];
            if (v) u.voice = v;
            speechSynthesis.cancel();
            speechSynthesis.speak(u);
        """)
        ui.timer(2.6, lambda: char_container.classes(replace="character-wrap small"), once=True)

    global _greeted_once
    if not _greeted_once:
        _greeted_once = True
        ui.timer(0.3, greet, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8501, storage_secret="change_this_secret_key", title="Chatbot", reload=True)