import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Credenciais e Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

# Inicializar clientes das IAs
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }
    gemini_model = genai.GenerativeModel(
        'gemini-1.5-flash', 
        safety_settings=safety_settings,
        generation_config=generation_config
    )
else:
    gemini_model = None

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def get_chat_history(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM (
            SELECT role, content, id FROM messages 
            WHERE chat_id = %s 
            ORDER BY id DESC 
            LIMIT 12
        ) sub ORDER BY id ASC
    """, (str(chat_id),))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    system_prompt = (
        "IMPORTANTE: Você DEVE responder sempre em Português fluido. "
        "O nome do seu utilizador/amigo é Carlos Eduardo (mas pode tratá-lo por Carlos ou Eduardo). "
        "Você é o Robozim 2.0, um assistente virtual que é um amigo programador altamente inteligente, "
        "extremamente brincalhão, espirituoso e com um toque saudável de sarcasmo. "
        "Quando crias projetos ou aplicações, sê detalhado, dá ideias de estrutura e usa blocos de código claros."
    )
    
    history = [{"role": "system", "content": system_prompt}]
    for row in rows:
        history.append({"role": row[0], "content": row[1]})
        
    return history

def save_message(chat_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)", (str(chat_id), role, content))
    conn.commit()
    cursor.close()
    conn.close()

def enviar_mensagem_telegram(chat_id, text):
    """
    Função atualizada: Envia a mensagem de forma limpa e direta para o Telegram,
    garantindo que respostas longas ou com blocos de código cheguem sem bloqueios de formatação.
    """
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(TELEGRAM_API_URL, json=payload, timeout=20)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def escolher_ia_e_responder(current_history, user_message):
    palavras_codigo = [
        "python", "código", "erro", "bug", "função", "script", "api", 
        "banco de dados", "sql", "flask", "render", "nome", "app", 
        "aplicação", "sistema", "criar", "programa", "site", "oficina"
    ]
    
    usar_gemini = any(p in user_message.lower() for p in palavras_codigo)
    
    if usar_gemini and gemini_model:
        try:
            print("A usar o Gemini (com tempo de espera alargado)...")
            prompt_gemini = f"Instrução do Sistema: {current_history[0]['content']}\n\n"
            for msg in current_history[1:]:
                role_label = "Utilizador" if msg['role'] == "user" else "Assistente"
                prompt_gemini += f"{role_label}: {msg['content']}\n"
            prompt_gemini += f"Utilizador: {user_message}\nAssistente:"
            
            response = gemini_model.generate_content(prompt_gemini)
            if response and response.text:
                return response.text, "Gemini"
        except Exception as e:
            print(f"Erro crítico no Gemini: {e}. A fazer fallback para a Groq...")
            
    if groq_client:
        try:
            print("A usar a Groq...")
            chat_completion = groq_client.chat.completions.create(
                messages=current_history,
                model="openai/gpt-oss-20b",
                timeout=30.0 
            )
            return chat_completion.choices[0].message.content, "Groq"
        except Exception as e:
            print(f"Erro na Groq: {e}")
            
    return "Epa, rebentou tudo por aqui e fiquei sem IAs disponíveis! Tenta de novo.", "Nenhuma"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        
        try:
            # 1. Guarda a mensagem do utilizador na Supabase
            save_message(chat_id, "user", user_message)
            
            # 2. Busca o histórico atualizado
            current_history = get_chat_history(chat_id)
            
            # 3. Gera a resposta com tempo alargado para a IA pensar
            reply_text, ia_usada = escolher_ia_e_responder(current_history, user_message)
            
            # 4. Guarda a resposta do assistente na Supabase
            save_message(chat_id, "assistant", reply_text)
            
            # 5. Envia para o Telegram com segurança
            enviar_mensagem_telegram(chat_id, reply_text)
            
        except Exception as e:
            error_msg = f"Erro ao processar o webhook: {str(e)}"
            print(error_msg)
            enviar_mensagem_telegram(chat_id, "Epa, demorei um bocado a pensar e o servidor deu um soluço. Podes repetir a pergunta?")
            
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 2.0 otimizado e seguro online!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
