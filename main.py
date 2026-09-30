import os
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

# Dicionário para armazenar o histórico de conversas por chat_id
# Cada chat terá uma lista de mensagens (máximo de 10 mensagens para não sobrecarregar)
conversations = {}

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
        
        # Inicializa o histórico deste chat se ele não existir
        if chat_id not in conversations:
            conversations[chat_id] = [
                {"role": "system", "content": "Você é um assistente útil, amigável e conciso."}
            ]
            
        # Adiciona a mensagem do utilizador ao histórico
        conversations[chat_id].append({"role": "user", "content": user_message})
        
        # Mantém apenas as últimas 10 mensagens para evitar estouro de tokens
        if len(conversations[chat_id]) > 11:  # 1 system + 10 interações
            # Mantém a regra do sistema (índice 0) e as últimas 10 mensagens
            conversations[chat_id] = [conversations[chat_id][0]] + conversations[chat_id][-10:]
        
        try:
            # Envia todo o histórico para a Groq
            chat_completion = client.chat.completions.create(
                messages=conversations[chat_id],
                model="openai/gpt-oss-20b",
            )
            
            reply_text = chat_completion.choices[0].message.content
            
            # Adiciona a resposta do bot ao histórico para manter o contexto
            conversations[chat_id].append({"role": "assistant", "content": reply_text})
            
            # Envia a resposta de volta ao Telegram
            send_telegram_message(chat_id, reply_text)
            
        except Exception as e:
            error_msg = f"Erro detalhado da Groq: {str(e)}"
            print(error_msg)
            send_telegram_message(chat_id, error_msg)
            
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot da Groq com memória rodando com sucesso!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
