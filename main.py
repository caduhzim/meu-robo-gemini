import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
import google.generativeai as genai

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

application = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    try:
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = "Desculpa, tive um problema ao processar a resposta com a IA."
        print(f"Erro no Gemini: {e}")

    await context.bot.send_message(chat_id=chat_id, text=bot_reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/")
def home():
    return "Bot do Laboratório está ativo e online via Webhook!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        
        # Obtém ou cria um loop de eventos seguro para a thread atual do Flask
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Inicializa e processa o update sem fechar o loop global
        async def run_async():
            await application.initialize()
            await application.process_update(update)
            
        loop.run_until_complete(run_async())
    except Exception as e:
        print(f"Erro no webhook: {e}")

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
        import requests
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
        print(f"Webhook configurado para: {webhook_url}")

    app.run(host="0.0.0.0", port=port)
