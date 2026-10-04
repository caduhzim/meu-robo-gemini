import os
import threading
import telebot
from flask import Flask
from huggingface_hub import InferenceClient

# --- Mini servidor web para o Render não dar erro de porta ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot do Telegram a funcionar e a renderizar!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Iniciar o Flask numa thread paralela
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()
# -------------------------------------------------------------

# --- Configuração do Bot e da IA ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Limpa webhooks antigos para evitar conflitos de sessão
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# Cliente Hugging Face (Mistral-7B-Instruct)
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
)

# Personalidade do bot
SYSTEM_PROMPT = (
    "Tu és um programador experiente, extremamente sarcástico, brincalhão e um bocado "
    "impaciente com erros básicos de código. Responde sempre em português de Portugal, "
    "com piadas secas sobre código, mas ajuda no final a resolver o problema do utilizador."
)

@bot.message_handler(func=lambda message: True)
def handle_message(user_message):
    try:
        # Envia indicador de que o bot está a pensar
        bot.send_chat_action(user_message.chat.id, 'typing')
        
        # Gera a resposta usando a Hugging Face API
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

print("Bot iniciado com sucesso e pronto para o combate!")
bot.infinity_polling()

