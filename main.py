import os
import telebot
from flask import Flask, request
from huggingface_hub import InferenceClient

# --- Configuração do Flask e do Bot ---
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN)

client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

SYSTEM_PROMPT = (
    "Você é um programador experiente, extremamente sarcástico, brincalhão e um pouco "
    "impaciente com erros básicos de código. Responda sempre em português do Brasil, "
    "com piadas secas sobre código, mas ajude no final a resolver o problema do usuário."
)

# --- Rota principal para o Render saber que o site está vivo ---
@app.route('/')
def home():
    return "Bot do Telegram com Webhook ativo e funcionando!"

# --- Rota do Webhook que o Telegram vai chamar ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def receive_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
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
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message.text}
            ],
            max_tokens=500,
            temperature=0.7
        )
        reply_text = response.choices[0].message.content
        bot.reply_to(user_message, reply_text)
    except Exception as e:
        bot.reply_to(user_message, f"Deu ruim no sistema: {e}. Provavelmente a culpa é da sua última linha de código.")

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

