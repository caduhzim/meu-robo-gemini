import os
import sqlite3
import requests
from flask import Flask, request as flask_request
from groq import Groq

# Configuração das chaves via Variáveis de Ambiente do Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Inicializa o Flask e o cliente da Groq
app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Configuração da Base de Dados SQLite
DB_NAME = "bot_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela para guardar as mensagens de cada chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# Inicializa a base de dados ao arrancar a aplicação
init_db()

def get_chat_history(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC", (str(chat_id),))
    rows = cursor.fetchall()
    conn.close()

    # Mensagem de sistema padrão no início
    history = [{"role": "system", "content": "Você é um assistente útil, amigável e conciso."}]
    
    for row in rows:
        history.append({"role": row[0], "content": row[1]})
        
    return history

def save_message(chat_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (str(chat_id), role, content))
    conn.commit()
    
    # Mantém apenas as últimas 12 mensagens por chat para não inchar a base de dados nem exceder tokens
    cursor.execute("""
        DELETE FROM messages WHERE id NOT IN (
            SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 12
        ) AND chat_id = ?
    """, (str(chat_id), str(chat_id)))
    
    conn.commit()
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
        
        # Guarda a mensagem do utilizador na BD
        save_message(chat_id, "user", user_message)
        
        # Recupera o histórico completo deste chat
        current_history = get_chat_history(chat_id)
        
        try:
            # Envia o histórico completo para a Groq
            chat_completion = client.chat.completions.create(
                messages=current_history,
                model="openai/gpt-oss-20b",
            )
            
            reply_text = chat_completion.choices[0].message.content
            
            # Guarda a resposta do assistente na BD
            save_message(chat_id, "assistant", reply_text)
            
            # Envia a resposta de volta ao Telegram
            send_telegram_message(chat_id, reply_text)
            
        except Exception as e:
            error_msg = f"Erro detalhado da Groq: {str(e)}"
            print(error_msg)
            send_telegram_message(chat_id, error_msg)
            
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot da Groq com SQLite rodando com sucesso!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
