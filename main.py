import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters
from groq import Groq

# Configuração das chaves via Variáveis de Ambiente do Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Inicializa o Flask e o cliente da Groq
app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

# Configuração moderna do Bot do Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.message.chat_id

    if user_message:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                model="llama-3.3-70b-versatile",
            )
            reply_text = chat_completion.choices[0].message.content
            await update.message.reply_text(reply_text)
            
        except Exception as e:
            error_msg = f"Erro detalhado da Groq: {str(e)}"
            print(error_msg)
            await update.message.reply_text(error_msg)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def process_telegram_update(json_data):
    # Inicializa e processa o update devidamente de forma assíncrona
    await application.initialize()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    asyncio.run(process_telegram_update(json_data))
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot da Groq rodando com sucesso!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
