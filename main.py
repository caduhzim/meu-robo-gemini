import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters
from groq import Groq

# Configuração das chaves via Variáveis de Ambiente do Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Inicializa o Flask e o cliente da Groq
app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

# Configuração do Bot do Telegram
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

def handle_message(update, context):
    chat_id = update.message.chat_id
    user_message = update.message.text

    if user_message:
        try:
            # Chamada para a API da Groq usando o modelo Llama 3.3 70B
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
            bot.send_message(chat_id=chat_id, text=reply_text)
            
        except Exception as e:
            # Mostra o erro técnico exato no Telegram para sabermos o motivo exato da falha
            error_msg = f"Erro detalhado da Groq: {str(e)}"
            print(error_msg)
            bot.send_message(chat_id=chat_id, text=error_msg)

# Adiciona o manipulador de mensagens de texto
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot da Groq rodando com sucesso!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
