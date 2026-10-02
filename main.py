import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
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
        print("-> Base de dados inicializada com sucesso!")
    except Exception as e:
        print(f"-> Erro ao inicializar a base de dados: {e}")

init_db()

def get_chat_history(chat_id):
    try:
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
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        rows = []

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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)", (str(chat_id), role, content))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao guardar mensagem: {e}")

def enviar_mensagem_telegram(chat_id, text):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(TELEGRAM_API_URL, json=payload, timeout=20)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        
        try:
            save_message(chat_id, "user", user_message)
            current_history = get_chat_history(chat_id)
            
            if groq_client:
                print("-> A enviar pedido para a Groq (Llama)...")
                chat_completion = groq_client.chat.completions.create(
                    messages=current_history,
                    model="llama-3.3-70b-versatile",
                    timeout=30.0
                )
                reply_text = chat_completion.choices[0].message.content
            else:
                reply_text = "Epa, a chave da Groq não está configurada!"
            
            save_message(chat_id, "assistant", reply_text)
            enviar_mensagem_telegram(chat_id, reply_text)
            
        except Exception as e:
            error_msg = f"ERRO EXATO: {str(e)}"
            print(error_msg)
            enviar_mensagem_telegram(chat_id, error_msg)
            
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 2.0 Llama online com debug ativo!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
