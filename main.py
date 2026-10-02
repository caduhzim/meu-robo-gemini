import os
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Modelo de texto oficial
MODELO_TEXTO = "openai/gpt-oss-20b"

def enviar_mensagem_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_name = message["from"].get("first_name", "Mestre")
    
    # Tratamento exclusivo de Texto
    if "text" in message:
        user_text = message["text"]
        try:
            chat_completion = client.chat.completions.create(
                model=MODELO_TEXTO,
                messages=[
                    {
                        "role": "system",
                        "content": f"És o Robozim, um assistente sarcástico, informal, direto e ultra-competente. O teu chefe e mestre é o {user_name}."
                    },
                    {
                        "role": "user",
                        "content": user_text
                    }
                ],
                max_completion_tokens=1024
            )
            resposta = chat_completion.choices[0].message.content
            enviar_mensagem_telegram(chat_id, resposta)
        except Exception as e:
            enviar_mensagem_telegram(chat_id, f"Deu treta no cérebro de texto: {e}")
        return "OK", 200

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

