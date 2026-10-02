import os
import requests
import psycopg2
from flask import Flask, request as flask_request
from groq import Groq

app = Flask(__name__)

# Configurações de Ambiente
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Inicializa o cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# Modelos (Texto com OpenAI e Visão com Qwen)
MODELO_TEXTO = "openai/gpt-oss-20b"
MODELO_VISAO = "qwen/qwen-2.5-vl-7b-instruct"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def save_message(chat_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)",
        (str(chat_id), role, content)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_memorias(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT facto FROM memorias_eduardo WHERE chat_id = %s ORDER BY id DESC LIMIT 10", (str(chat_id),))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        return "Nenhuma memória de longo prazo registada ainda."
    return "\n".join([f"- {row[0]}" for row in rows])

def analisar_e_guardar_facto(chat_id, texto):
    pass

def get_chat_history(chat_id, user_name):
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
        "IMPORTANTE: Responda sempre em Português fluido, natural e informal. "
        f"O nome do utilizador com quem estás a falar é {user_name}. "
        "És o Robozim 3.0, um amigo programador altamente inteligente, brincalhão e com um toque saudável de sarcasmo. "
        f"\n[MEMÓRIAS E FACTOS APRENDIDOS SOBRE O {user_name.upper()}]:\n{memories_text}\n"
        "Usa estes factos de forma subtil para mostrar que te lembras dele. "
        "Sempre que mandares código, usa a formatação correta em Markdown (crases triplas ```)."
    )
    
    history = [{"role": "system", "content": system_prompt}]
    for row in rows:
        if isinstance(row[1], str):
            history.append({"role": row[0], "content": row[1]})
        
    return history

def processar_com_groq(history, user_message, image_url=None):
    if image_url:
        messages = history.copy()
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_message if user_message else "Analisa esta imagem para mim, mestre."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })
        response = groq_client.chat.completions.create(
            model=MODELO_VISAO,
            messages=messages,
            max_tokens=1024
        )
    else:
        messages = history.copy()
        messages.append({"role": "user", "content": user_message})
        response = groq_client.chat.completions.create(
            model=MODELO_TEXTO,
            messages=messages,
            max_tokens=1024
        )
        
    return response.choices[0].message.content

def enviar_mensagem_telegram(chat_id, text):
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def obter_url_foto_telegram(file_id):
    url_file_info = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    resp = requests.get(url_file_info).json()
    if resp.get("ok"):
        file_path = resp["result"]["file_path"]
        return f"[https://api.telegram.org/file/bot](https://api.telegram.org/file/bot){TELEGRAM_TOKEN}/{file_path}"
    return None

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_name = msg["from"].get("first_name", "Amigo")
        
        user_message = msg.get("text", msg.get("caption", ""))
        image_url = None
        
        if "photo" in msg:
            best_photo = msg["photo"][-1]
            file_id = best_photo["file_id"]
            image_url = obter_url_foto_telegram(file_id)

        if user_message or image_url:
            try:
                save_message(chat_id, "user", user_message if user_message else "[Enviou uma imagem]")
                if user_message:
                    analisar_e_guardar_facto(chat_id, user_message)
                
                current_history = get_chat_history(chat_id, user_name)
                reply_text = processar_com_groq(current_history, user_message, image_url)
                
                save_message(chat_id, "assistant", reply_text)
                enviar_mensagem_telegram(chat_id, reply_text)
            except Exception as e:
                error_msg = f"Erro ao processar: {str(e)}"
                print(error_msg)
                enviar_mensagem_telegram(chat_id, error_msg)
                
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
