import os
import threading
import telebot
from flask import Flask
from huggingface_hub import InferenceClient

# --- Configuração do Flask (Processo Principal para o Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot do Telegram ativo e em funcionamento!"

# --- Configuração do Bot e da IA ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

SYSTEM_PROMPT = (
    "Tu és um programador experiente, extremamente sarcástico, brincalhão e um bocado "
    "impaciente com erros básicos de código. Responde sempre em português de Portugal, "
    "com piadas secas sobre código, mas ajuda no final a resolver o problema do utilizador."
)

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
        bot.reply_to(user_message, f"Deu tosse no sistema: {e}. Provavelmente culpo a tua última linha de código.")

# Função para correr o bot do Telegram em background
def run_telegram_bot():
    print("A iniciar o polling do Telegram em background...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Inicia o bot do Telegram numa thread separada
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # O Flask fica a correr no processo principal, abraçando imediatamente a porta do Render
    port = int(os.environ.get("PORT", 10000))
    print(f"A iniciar o servidor Flask na porta {port}...")
    app.run(host="0.0.0.0", port=port)

