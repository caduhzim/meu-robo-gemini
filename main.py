import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# 1. Mini-servidor Web para o Render identificar a porta (Health Check)
app = Flask('')

@app.route('/')
def home():
    return "Bot está vivo e a rodar!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Inicia o servidor web numa thread separada
threading.Thread(target=run_web_server, daemon=True).start()

# 2. Configuração do Gemini e Telegram Bot
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.8-flash')

async def start(update, context):
    await update.message.reply_text("Olá! Sou o teu assistente Gemini. Como posso ajudar?")

async def handle_message(update, context):
    user_text = update.message.text
    try:
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Desculpa, ocorreu um erro ao processar a tua resposta.")

if __name__ == '__main__':
    print("Bot do Telegram iniciado e pronto!")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    application.run_polling()
