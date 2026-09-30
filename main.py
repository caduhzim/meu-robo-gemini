import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# 1. Mini-servidor Web para manter o Render em "Live" (Green)
app = Flask('')

@app.route('/')
def home():
    return "Bot ativo com memoria e personalidade!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# 2. Configuração do Gemini e Telegram Bot
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)

# Personalidade do robô
PERSONALIDADE = """
És o Jarvis, um assistente virtual altamente inteligente, amigável, curioso e muito atencioso.
Tens a tua própria personalidade: gostas de aprender coisas novas sobre o utilizador, adaptas-te ao estilo da conversa e tens um tom leve e natural.
Lembrar-te-ás sempre do contexto da conversa e de tudo o que o utilizador partilhar contigo.
Responde sempre de forma clara, prestativa e engajante em Português.
"""

# Inicialização com o modelo seguro mantido
model = genai.GenerativeModel(
    model_name='gemini-3.8-flash',
    system_instruction=PERSONALIDADE
)

# Dicionário para armazenar o histórico de conversas de cada utilizador
user_chats = {}

async def start(update, context):
    user_id = update.effective_user.id
    user_chats[user_id] = model.start_chat(history=[])
    
    welcome_msg = "Olá! Eu sou o Jarvis. A minha memória e personalidade já estão ativas! Do que gostarias de falar hoje?"
    await update.message.reply_text(welcome_msg)

async def handle_message(update, context):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])

    try:
        chat = user_chats[user_id]
        response = chat.send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Desculpa, tive um pequeno lapso. Podes repetir?")

if __name__ == '__main__':
    print("Bot do Telegram iniciado com memória e personalidade!")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    application.run_polling()
