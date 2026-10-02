import os
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Modelos oficiais definidos
MODELO_TEXTO = "openai/gpt-oss-20b"
MODELO_VISAO = "qwen/qwen-2.5-vl-7b-instruct"

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
    
    # Tratamento de Imagem (Visão com Qwen)
    if "photo" in message:
        try:
            photo = message["photo"][-1] # Pega a maior resolução
            file_id = photo["file_id"]
            
            # Obter caminho do ficheiro no Telegram
            file_info_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
            r = requests.get(file_info_url)
            file_path = r.json()["result"]["file_path"]
            
            image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            
            caption = message.get("caption", "O que vês nesta imagem?")

            # Chamada à Groq com Qwen para Visão
            chat_completion = client.chat.completions.create(
                model=MODELO_VISAO,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": caption},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_completion_tokens=1024
            )
            resposta = chat_completion.choices[0].message.content
            enviar_mensagem_telegram(chat_id, resposta)
        except Exception as e:
            enviar_mensagem_telegram(chat_id, f"Epá, deu bronca ao processar a imagem: {e}")
        return "OK", 200

    # Tratamento de Texto (GPT-20B)
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
