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
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabela de mensagens normais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    # Tabela de memórias de longo prazo do Eduardo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memorias_eduardo (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            facto TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def get_memorias(chat_id):
    """Vai buscar todas as memórias guardadas sobre o Eduardo"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT facto FROM memorias_eduardo WHERE chat_id = %s ORDER BY id DESC LIMIT 10", (str(chat_id),))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        return "Nenhuma memória de longo prazo registada ainda."
    
    return "\n".join([f"- {row[0]}" for row in rows])

def salvar_memoria(chat_id, facto):
    """Guarda um novo facto na base de dados se for relevante"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memorias_eduardo (chat_id, facto) VALUES (%s, %s)", (str(chat_id), facto))
    conn.commit()
    cursor.close()
    conn.close()

def analisar_e_guardar_facto(chat_id, user_message):
    """Deteta se o utilizador está a partilhar algo importante para memorizar"""
    msg_lower = user_message.lower()
    gatilhos_memoria = ["meu nome é", "eu gosto de", "o meu projeto", "trabalho com", "eu sou", "prefiro", "tenho um", "o meu objetivo"]
    
    if any(g in msg_lower for g in gatilhos_memoria):
        try:
            prompt_extracao = [
                {"role": "system", "content": "Extrai apenas o facto importante sobre o utilizador contido na frase, de forma curta e direta (ex: 'Gosta de programar em Python', 'O projeto é um bot do Telegram'). Não dês saudações."},
                {"role": "user", "content": user_message}
            ]
            res = groq_client.chat.completions.create(messages=prompt_extracao, model="llama-3.1-8b-instant")
            facto_extraido = res.choices[0].message.content.strip()
            if facto_extraido:
                salvar_memoria(chat_id, facto_extraido)
                print(f"Memória guardada com sucesso: {facto_extraido}")
        except Exception as e:
            print(f"Erro ao extrair memória: {e}")

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

    memories_text = get_memorias(chat_id)

    system_prompt = (
        "IMPORTANTE: Você DEVE responder sempre em Português fluido, claro e natural. "
        "O nome do seu utilizador/amigo é Eduardo. "
        "Você é o Robozim 3.0, um amigo programador altamente inteligente, brincalhão e com um toque saudável de sarcasmo. "
        f"\n[MEMÓRIAS E FACTOS APRENDIDOS SOBRE O EDUARDO]:\n{memories_text}\n"
        "Usa estes factos sempre que relevante para demonstrar que o conheces e te lembras dele. "
        "Sempre que enviar blocos de código ou comandos, use a formatação correta em Markdown (com crases triplas ```)."
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
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(TELEGRAM_API_URL, json=payload)
    if response.status_code != 200:
        payload_fallback = {
            "chat_id": chat_id,
            "text": text
        }
        requests.post(TELEGRAM_API_URL, json=payload_fallback)

def processar_com_groq(current_history, user_message):
    if groq_client:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=current_history,
                model="openai/gpt-oss-20b",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Erro na Groq: {e}")
            return f"Epa mestre, a Groq engasgou-se: {str(e)}"
    
    return "Epa, o cliente da Groq não está configurado!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        try:
            save_message(chat_id, "user", user_message)
            analisar_e_guardar_facto(chat_id, user_message)
            current_history = get_chat_history(chat_id)
            reply_text = processar_com_groq(current_history, user_message)
            save_message(chat_id, "assistant", reply_text)
            enviar_mensagem_telegram(chat_id, reply_text)
        except Exception as e:
            error_msg = f"Erro ao processar a mensagem: {str(e)}"
            print(error_msg)
            enviar_mensagem_telegram(chat_id, error_msg)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 3.0 com Memória Dinâmica online!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
