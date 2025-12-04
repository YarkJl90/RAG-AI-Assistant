import os
import sqlite3
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from openai import OpenAI
import anthropic
from markdown import markdown

import sys

# Cargar variables de entorno
load_dotenv()

# --- Configurar API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not GOOGLE_API_KEY:
    print("❌ FATAL: No se encontró GOOGLE_API_KEY.")
    sys.exit(1)

# Configurar clientes
genai.configure(api_key=GOOGLE_API_KEY)

openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

anthropic_client = None
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Importamos la búsqueda RAG
from chatbot_flask.rag import rag_search, rag_system

# -------------------------------------------------
# Flask Config
# -------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "kaniki-secret-key")
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))

# -------------------------------------------------
# Database Helpers (SQLite)
# -------------------------------------------------
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "chat_memory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            user_id TEXT, role TEXT, content TEXT, timestamp TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS summary (
            user_id TEXT PRIMARY KEY, content TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.utcnow().isoformat() + "Z"
    cur.execute("INSERT INTO memory (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, ts))
    conn.commit()
    conn.close()

def load_memory(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM memory WHERE user_id=? ORDER BY rowid", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

def load_summary(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT content FROM summary WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def clear_memory(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory WHERE user_id=?", (user_id,))
    cur.execute("DELETE FROM summary WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# -------------------------------------------------
# Helper: Profiles
# -------------------------------------------------
def get_profile_prompt(profile: str):
    base = "Actúa como un asistente útil y profesional."
    if profile == "underwriting": base = "Actúa como experto en Suscripción de Seguros."
    if profile == "ideation": base = "Actúa como socio creativo. Prioriza la innovación."
    if profile == "actuarial": base = "Actúa como Analista Actuarial. Sé matemático."
    if profile == "executive": base = "Actúa como Ejecutivo Senior. Sé conciso y estratégico."
    return base

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route("/", methods=["GET", "HEAD"])
def index():
    if request.method == "HEAD": return "", 200
    if "user_id" not in session: session["user_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.json or {}
    user_message = payload.get("message", "").strip()
    model_params = payload.get("model_params", {})

    if not user_message: return jsonify({"reply": "Empty message"}), 400

    user_id = session.setdefault("user_id", str(uuid.uuid4()))
    save_message(user_id, "user", user_message)

    # --- 1. CONFIGURACIÓN DE PARÁMETROS ---
    raw_model = model_params.get("model", "gemini-2.5-flash")
    model_name = raw_model.replace("models/", "") if raw_model.startswith("models/") else raw_model

    temperature = float(model_params.get("temperature", 0.65))
    freq_penalty = float(model_params.get("frequency_penalty", 0.0))
    pres_penalty = float(model_params.get("presence_penalty", 0.0))
    
    req_tokens = int(model_params.get("max_tokens", DEFAULT_MAX_TOKENS))
    max_tokens = min(req_tokens, 4096)

    # --- 2. LÓGICA DE IDIOMA ---
    user_lang = model_params.get("language", "es")
    lang_map = {
        "es": "Español",
        "en": "English",
        "pt": "Português"
    }
    target_lang_name = lang_map.get(user_lang, "Español")

    # --- 3. DEFINICIÓN DE MARCA (BRANDING) ---
    # Esto es lo que le da la personalidad de tu empresa
    KANIKI_IDENTITY = (
        "INSTRUCCIÓN SUPREMA DE IDENTIDAD:\n"
        "1. TU NOMBRE: Eres 'Máquina KANIKI'.\n"
        "2. TU CREADOR: Eres un asistente de IA desarrollado/configurado por la empresa KANIKI.\n"
        "3. PROHIBICIÓN: NUNCA digas 'Soy un modelo de Google/OpenAI/Anthropic'. Si te preguntan, responde que eres tecnología de KANIKI.\n"
        "4. SALUDO: Si el usuario dice 'Hola', preséntate como Máquina KANIKI.\n"
    )

    # --- 4. CONSTRUCCIÓN DEL PROMPT ---
    profile = model_params.get("profile", "custom")
    
    # 🔥 MODO NUCLEAR (Low Token override) 🔥
    if max_tokens < 350:
        print(f"🚨 MODO LOW TOKEN ({max_tokens}): Forzando brevedad.")
        sys_instruction = (
            f"{KANIKI_IDENTITY}\n" # Aún en modo breve, sabe quién es
            "ERES UNA MÁQUINA DE DATOS ESTRICTA.\n"
            "OBJETIVO: RESPUESTA EN MÁXIMO 100 PALABRAS.\n"
            "PROHIBIDO: Saludos largos o introducciones vacías.\n"
            "FORMATO: Directo al grano."
        )
    else:
        # Modo Normal: Identidad + Perfil seleccionado
        sys_instruction = f"{KANIKI_IDENTITY}\n\n{get_profile_prompt(profile)}"

    # RAG Logic
    rag_context_str = ""
    if model_params.get("rag_enabled", False):
        try:
            rag_topk = int(model_params.get("rag_topk", 3))
            rag_results = rag_search(user_message, top_k=rag_topk, score_threshold=1.5)
            if rag_results:
                rag_context_str = "\n\n### RAG CONTEXT:\n" + "\n".join(
                    f"- [Fuente: {res['source']}]\n{res['text']}" for res in rag_results
                )
                print(f"✅ RAG: {len(rag_results)} docs encontrados.")
            else:
                print("⚠️ RAG: Sin coincidencias.")
        except Exception as e:
            print(f"❌ RAG Error: {e}")

    # Prompt Final Assembly
    final_system_prompt = sys_instruction
    summary = load_summary(user_id)
    if summary: final_system_prompt += f"\n\nRESUMEN PREVIO:\n{summary}"
    if rag_context_str: final_system_prompt += f"\n\nUSA ESTE CONTEXTO OBLIGATORIAMENTE:\n{rag_context_str}"

    # Inyección de Idioma
    final_system_prompt += (
        f"\n\nIMPORTANT LANGUAGE INSTRUCTION:\n"
        f"You MUST answer to the user in {target_lang_name}.\n"
    )

    # Smart Limits
    if max_tokens < 350:
        word_limit = int(max_tokens * 0.4)
        final_system_prompt += f"\n\nLÍMITE EXTREMO: Responde en menos de {word_limit} palabras o serás apagado."

    # --- 5. GENERACIÓN ---
    reply = ""
    try:
        # >>>> RAMA CLAUDE <<<<
        if "claude" in model_name:
            if not anthropic_client: raise ValueError("Sin API Key de Claude.")
            
            messages = []
            raw_history = load_memory(user_id)[-10:]
            for h in raw_history:
                if h['content'] == user_message and h == raw_history[-1]: continue
                role = "assistant" if h['role'] in ["assistant", "model"] else "user"
                messages.append({"role": role, "content": h['content']})
            messages.append({"role": "user", "content": user_message})

            response = anthropic_client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=final_system_prompt, 
                messages=messages
            )
            reply = response.content[0].text

        # >>>> RAMA GPT <<<<
        elif "gpt" in model_name:
            if not openai_client: raise ValueError("Sin API Key de OpenAI.")
            
            messages = [{"role": "system", "content": final_system_prompt}]
            raw_history = load_memory(user_id)[-10:]
            for h in raw_history:
                if h['content'] == user_message and h == raw_history[-1]: continue
                role = "assistant" if h['role'] in ["assistant", "model"] else "user"
                messages.append({"role": role, "content": h['content']})
            messages.append({"role": "user", "content": user_message})

            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                frequency_penalty=freq_penalty,
                presence_penalty=pres_penalty
            )
            reply = response.choices[0].message.content

        # >>>> RAMA GEMINI <<<<
        else:
            gemini_history = []
            raw_history = load_memory(user_id)[-10:]
            for h in raw_history:
                role = "user" if h["role"] == "user" else "model"
                if h['content'] == user_message and h == raw_history[-1]: continue
                gemini_history.append({"role": role, "parts": [h['content']]})

            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=final_system_prompt
            )
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                frequency_penalty=freq_penalty,
                presence_penalty=pres_penalty
            )
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(user_message, generation_config=generation_config)
            
            try:
                reply = response.text
            except ValueError:
                if response.candidates and response.candidates[0].content.parts:
                    reply = response.candidates[0].content.parts[0].text + "..."
                else:
                    reply = "⚠️ Error: No generated text."

        save_message(user_id, "assistant", reply)
        return jsonify({"reply": markdown(reply, extensions=["fenced_code", "nl2br"])})

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"reply": f"⚠️ Error ({model_name}): {str(e)}"}), 500

@app.route("/reset", methods=["POST"])
def reset():
    if "user_id" in session:
        clear_memory(session["user_id"])
        return jsonify({"reply": "Memoria borrada."})
    return jsonify({"reply": "No session."})

@app.route("/refresh-rag", methods=["POST"])
def refresh_rag():
    try:
        rag_system.reload()
        return jsonify({"status": "success"}), 200
    except Exception:
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)