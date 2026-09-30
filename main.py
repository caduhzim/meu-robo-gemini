import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq

# Configuração das chaves via Variáveis de Ambiente do Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Inicializa o Flask e o cliente da Groq
app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

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
    # Pega as últimas 12 mensagens para a IA ter o contexto recente
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

    # Personalidade: Programador, Sarcástico e Brincalhão
    system_prompt = (
        "Você é o Robozim 2, um assistente virtual que é um amigo programador altamente inteligente, "
        "extremamente brincalhão, espirituoso e com um toque saudável de sarcasmo. "
        "Você adora tecnologia, piadas geeks, mandar umas larachas e rir das situações do dia a dia, "
        "mas sem deixar de ser prestativo e certeiro nas soluções técnicas. "
        "Use um tom descontraído, divertido e cheio de personalidade nas respostas."
    )
    
    history = [{"role": "system", "content": system_prompt}]
    for row in rows:
        history.append({"role": row[0], "content": row[1]})
        
    return history

def save_message(chat_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Guarda TUDO na tabela do Supabase de forma permanente
    cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)", (str(chat_id), role, content))
    conn.commit()
    cursor.close()
    conn.close()

def send_telegram_message(chat_id, text):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(TELEGRAM_API_URL, json=payload)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        
        save_message(chat_id, "user", user_message)
        current_history = get_chat_history(chat_id)
        
        try:
            chat_completion = client.chat.completions.create(
                messages=current_history,
                model="llama-3.1-8b-instant", # Modelo oficial ativo na Groq
            )
            
            reply_text = chat_completion.choices[0].message.content
            save_message(chat_id, "assistant", reply_text)
            send_telegram_message(chat_id, reply_text)
            
        except Exception as e:
            error_msg = f"Erro detalhado da Groq: {str(e)}"
            print(error_msg)
            send_telegram_message(chat_id, error_msg)
            
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 2 rodando com sucesso!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))





