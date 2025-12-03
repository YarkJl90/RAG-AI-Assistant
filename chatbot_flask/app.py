# chatbot_flask/app.py
import os
import sqlite3
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from markdown import markdown

# Cargar variables de entorno desde .env
load_dotenv()

# --- Optional langdetect ---
try:
    from langdetect import detect
except Exception:
    detect = None

from chatbot_flask.rag import rag_search, rag_system

# -------------------------------------------------
# Flask Config
# -------------------------------------------------
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "kaniki-secret-key")
DEBUG_ERRORS = os.getenv("DEBUG_ERRORS", "false").lower() in ("1", "true", "yes")

DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "250"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -------------------------------------------------
# Database Helpers (SQLite)
# -------------------------------------------------
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "chat_memory.db")


def _table_has_timestamp(cur):
    cur.execute("PRAGMA table_info(memory)")
    cols = [row[1] for row in cur.fetchall()]
    return "timestamp" in cols


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory'")
    exists_memory = cur.fetchone() is not None

    if exists_memory:
        if not _table_has_timestamp(cur):
            print("🧹 Rebuilding old DB...")
            cur.execute("DROP TABLE IF EXISTS memory")
            cur.execute("DROP TABLE IF EXISTS summary")
            conn.commit()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS summary (
            user_id TEXT PRIMARY KEY,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.utcnow().isoformat() + "Z"
    cur.execute(
        "INSERT INTO memory (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, role, content, ts),
    )
    conn.commit()
    conn.close()


def load_memory(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, timestamp FROM memory WHERE user_id=? ORDER BY rowid",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": r, "content": c, "timestamp": t} for r, c, t in rows]


def load_summary(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT content FROM summary WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def save_summary(user_id, summary_text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO summary (user_id, content)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET content = excluded.content
    """, (user_id, summary_text))
    conn.commit()
    conn.close()


def clear_memory(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory WHERE user_id=?", (user_id,))
    cur.execute("DELETE FROM summary WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# -------------------------------------------------
# Helper: Language Detection + Sentiment
# -------------------------------------------------
def detect_language(text):
    if not detect:
        return "und"
    try:
        return detect(text)
    except Exception:
        return "und"


def analyze_sentiment(text):
    return {
        "label": "neutral",
        "score": 0.0,
        "raw_label": "NOT_AVAILABLE"
    }


# -------------------------------------------------
# Summarization
# -------------------------------------------------
def summarize_memory(user_id, threshold=16):
    history = load_memory(user_id)
    if len(history) < threshold:
        return

    text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    prompt = (
        "Summarize the following conversation in concise bullet points. "
        "Preserve context, decisions, actuarial/business details, tasks, and technical points.\n\n"
        f"{text}"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=160,
            messages=[{"role": "user", "content": prompt}],
        )

        summary_text = completion.choices[0].message.content
        save_summary(user_id, summary_text)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM memory WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

    except Exception as e:
        print("⚠️ Summarization failed:", e)


# -------------------------------------------------
# PROFILES (Underwriting / Ideation / Custom)
# -------------------------------------------------
def get_profile_prompt(profile: str):
    if profile == "underwriting":
        return (
            "Bias the reasoning toward conservative actuarial underwriting. "
            "Prioritise risk mitigation, evidence-based conclusions, and regulatory alignment. "
            "Avoid speculative or aggressive recommendations."
        )

    if profile == "ideation":
        return (
            "Bias the reasoning toward creativity, product design, and innovation. "
            "Encourage exploration of new business models, AI use cases, and strategic opportunities."
        )

    return "No special bias. Use standard reasoning."


# -------------------------------------------------
# FIX: ROOT ENDPOINT FOR RENDER
# -------------------------------------------------
@app.route("/", methods=["GET", "HEAD"])
def index():
    # Render probe
    if request.method == "HEAD":
        return "", 200

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    return render_template("index.html")


# -------------------------------------------------
# CHAT ENDPOINT (with model_params)
# -------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    init_db()

    payload = request.json or {}
    user_message = payload.get("message", "").strip()
    model_params = payload.get("model_params", {})

    if not user_message:
        return jsonify({"reply": "Please type a message."}), 400

    user_id = session.setdefault("user_id", str(uuid.uuid4()))
    save_message(user_id, "user", user_message)

    lang = detect_language(user_message)
    sentiment = analyze_sentiment(user_message)

    model_name = model_params.get("model", "gpt-4o-mini")
    temperature = float(model_params.get("temperature", 0.65))
    max_tokens = int(model_params.get("max_tokens", DEFAULT_MAX_TOKENS))
    freq_pen = float(model_params.get("frequency_penalty", 0.0))
    pres_pen = float(model_params.get("presence_penalty", 0.0))
    profile = model_params.get("profile", "custom")

    profile_injection = get_profile_prompt(profile)

    sys_prompt = (
        "You are Máquina KANIKI, an AI assistant specialised in actuarial science, "
        "insurance, banking, investments, analytics, and applied AI. "
        "Mission: Provide Hindsight, Insight, and Foresight. "
        "Respond professionally by default but adapt to user tone. "
        "Avoid words like 'Certainly', 'Of course', 'Sure', 'Absolutely'. "
        f"Profile setting: {profile_injection}"
    )

    messages = [{"role": "system", "content": sys_prompt}]

    # --- RAG Integration ---
    rag_enabled = model_params.get("rag_enabled", False)
    if rag_enabled:
        rag_topk = int(model_params.get("rag_topk", 3))
        rag_results = rag_search(user_message, top_k=rag_topk)
        
        if rag_results:
            rag_context = "\n\n".join(
                f"[DOC {i+1}] Source: {res['source']}\n{res['text']}"
                for i, res in enumerate(rag_results)
            )
            rag_message = {
                "role": "system",
                "content": f"## Contexto Externo (RAG):\n{rag_context}"
            }
            # Insertar después del prompt de sistema principal pero antes del resumen
            messages.append(rag_message)

    summary = load_summary(user_id)
    if summary:
        messages.append({
            "role": "system",
            "content": f"Conversation summary (context only): {summary}"
        })

    history = load_memory(user_id)[-8:]
    messages += [{"role": h["role"], "content": h["content"]} for h in history]

    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            frequency_penalty=freq_pen,
            presence_penalty=pres_pen,
            messages=messages,
        )

        reply = completion.choices[0].message.content
        save_message(user_id, "assistant", reply)

        summarize_memory(user_id)

        reply_html = markdown(reply, extensions=["fenced_code", "nl2br"])

        emotion_payload = sentiment
        emotion_payload["timestamp"] = datetime.utcnow().isoformat() + "Z"

        return jsonify({"reply": reply_html, "emotion": emotion_payload})

    except Exception as e:
        print("ERROR /chat:", e)
        if DEBUG_ERRORS:
            return jsonify({"reply": f"Server error: {e}"}), 500
        return jsonify({"reply": "Server error."}), 500


# -------------------------------------------------
# RESET ENDPOINT
# -------------------------------------------------
@app.route("/reset", methods=["POST"])
def reset():
    uid = session.get("user_id")
    if uid:
        clear_memory(uid)
        return jsonify({"reply": "🧠 Memory cleared successfully."})
    return jsonify({"reply": "No active session found."})


# -------------------------------------------------
# RAG REFRESH ENDPOINT
# -------------------------------------------------
@app.route("/refresh-rag", methods=["POST"])
def refresh_rag():
    """
    Endpoint to manually trigger a reload of the RAG vectorstore.
    """
    try:
        rag_system.reload()
        return jsonify({"status": "success", "message": "RAG system reloaded successfully."}), 200
    except Exception as e:
        print(f"ERROR /refresh-rag: {e}")
        if DEBUG_ERRORS:
            return jsonify({"status": "error", "message": f"Failed to reload RAG system: {e}"}), 500
        return jsonify({"status": "error", "message": "Failed to reload RAG system."}), 500



# -------------------------------------------------
# START SERVER
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
