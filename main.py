import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from google import genai

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Configuração correta com o client do Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)

# Criamos o loop principal da aplicação e a instância do bot
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

application = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    try:
        response = client.interactions.create(
            model="gemini-2.5-flash",  # Ajustado para um modelo padrão estável atual
            input=user_message
        )
        bot_reply = response.output_text
    except Exception as e:
        import traceback
        traceback.print_exc()
        bot_reply = f"Erro técnico: {str(e)}"

    await context.bot.send_message(chat_id=chat_id, text=bot_reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Inicializamos o bot de forma assíncrona logo na subida do script
async def setup_bot():
    await application.initialize()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        print(f"Webhook configurado para: {webhook_url}")

loop.run_until_complete(setup_bot())

@app.route("/")
def home():
    return "Bot do Laboratório está ativo e online via Webhook!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        
        # Executa o update utilizando o event loop global existente sem fechá-lo
        future = asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
        future.result(timeout=10) # Aguarda o processamento com segurança
        
    except Exception as e:
        print(f"Erro no webhook: {e}")
        import traceback
        traceback.print_exc()

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
