import os
import requests
import telebot
from flask import Flask, request as flask_request

# --- Configuração do Flask e do Bot ---
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN)

# Vamos usar a API HTTP direta da Hugging Face para evitar bloqueios de clientes internos
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

SYSTEM_PROMPT = (
    "Você é um programador experiente, extremamente sarcástico, brincalhão e um pouco "
    "impaciente com erros básicos de código. Responda sempre em português do Brasil, "
    "com piadas secas sobre código, mas ajude no final a resolver o problema do usuário."
)

# --- Rota principal para o Render saber que o site está vivo ---
@app.route('/')
def home():
    return "Bot do Telegram com Webhook ativo e funcionando via Hugging Face!"

# --- Rota do Webhook que o Telegram vai chamar ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def receive_webhook():
    if flask_request.headers.get('content-type') == 'application/json':
        json_string = flask_request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Formato inválido", 403

# --- Lógica de resposta do Bot ---
@bot.message_handler(func=lambda message: True)
def handle_message(user_message):
    try:
        bot.send_chat_action(user_message.chat.id, 'typing')
        
        # Estrutura de prompt padrão que o Mistral adora
        prompt = f"[INST] {SYSTEM_PROMPT}\n\nUsuário: {user_message.text} [/INST]"
        
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 500, "temperature": 0.7, "return_full_text": False}
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        res_json = response.json()
        
        # Tratativa da resposta da API HTTP da Hugging Face
        if isinstance(res_json, list) and len(res_json) > 0:
            reply_text = res_json[0].get("generated_text", "O modelo gerou um vazio existencial.")
        elif isinstance(res_json, dict) and "error" in res_json:
            reply_text = f"Erro da Hugging Face: {res_json['error']}"
        else:
            reply_text = str(res_json)
            
        bot.reply_to(user_message, reply_text.strip())
    except Exception as e:
        bot.reply_to(user_message, f"Deu ruim no sistema: {e}. A culpa é dessa sua API esquisita.")

# --- Configurar o Webhook no arranque ---
def setup_webhook():
    if RENDER_EXTERNAL_URL:
        bot.remove_webhook()
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        print(f"Webhook configurado com sucesso para: {webhook_url}")
    else:
        print("Aviso: RENDER_EXTERNAL_URL não encontrada nas variáveis de ambiente.")

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
