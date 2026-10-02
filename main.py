import os
import requests
from flask import Flask, request
from groq import Groq
from supabase import create_client, Client

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

client = Groq(api_key=GROQ_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MODELO_TEXTO = "openai/gpt-oss-20b"

def enviar_mensagem_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")

def obter_memorias(chat_id):
    try:
        response = supabase.table("memorias_eduardo").select("facto").eq("chat_id", chat_id).order("data_criacao", desc=False).limit(10).execute()
        return [row["facto"] for row in response.data] if response.data else []
    except Exception as e:
        print(f"Erro ao buscar memórias: {e}")
        return []

def guardar_memoria(chat_id, facto):
    try:
        supabase.table("memorias_eduardo").insert({"chat_id": chat_id, "facto": facto}).execute()
    except Exception as e:
        print(f"Erro ao guardar memória: {e}")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_name = "Eduardo"
    
    if "text" in message:
        user_text = message["text"]
        try:
            # Buscar memórias anteriores da base de dados
            memorias = obter_memorias(chat_id)
            
            contexto_memorias = "\n".join(memorias) if memorias else "Nenhuma memória anterior."
            
            mensagens = [
                {
                    "role": "system",
                    "content": f"És o Robozim, um assistente sarcástico, informal, direto e ultra-competente. O teu chefe e mestre é o {user_name}.\nContexto guardado sobre o mestre:\n{contexto_memorias}"
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ]

            chat_completion = client.chat.completions.create(
                model=MODELO_TEXTO,
                messages=mensagens,
                max_completion_tokens=1024
            )
            resposta = chat_completion.choices[0].message.content
            
            # Guardar a interação na tabela memorias_eduardo
            guardar_memoria(chat_id, f"Utilizador disse: {user_text}")
            guardar_memoria(chat_id, f"Robozim respondeu: {resposta}")
            
            enviar_mensagem_telegram(chat_id, resposta)
        except Exception as e:
            enviar_mensagem_telegram(chat_id, f"Deu treta no cérebro com memória: {e}")
        return "OK", 200

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
