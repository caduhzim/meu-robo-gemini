import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
# Importe aqui a biblioteca do Gemini que você está a utilizar (ex: google.generativeai)
import google.generativeai as genai

app = Flask(__name__)

# Configurações de Tokens (pegando das variáveis de ambiente do Render)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") # URL do seu serviço no Render (ex: https://seu-bot.onrender.com)

# Configurar o Gemini
genai.configure(api_key=GEMINI_API_KEY)
# Usando o modelo atualizado conforme conversamos
model = genai.GenerativeModel('gemini-1.5-flash')

# Inicializar a aplicação do Telegram sem usar Polling
# O segredo para o Webhook no PTB v20+ é construir a aplicação mas NÃO iniciar o updater local
application = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

# Função que lida com as mensagens recebidas
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    try:
        # Aqui você pode injetar a sua lógica de histórico/memória se já tiver estruturada
        response = model.generate_content(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = "Desculpa, tive um problema ao processar a resposta com a IA."
        print(f"Erro no Gemini: {e}")

    await context.bot.send_message(chat_id=chat_id, text=bot_reply)

# Adicionar o handler de mensagens
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/")
def home():
    return "Bot do Laboratório está ativo e online via Webhook!"

# Rota do Webhook que o Telegram vai chamar
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    # Processa a atualização de forma assíncrona/direta no loop do bot
    import asyncio
    asyncio.run(application.process_update(update))
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Configurar o Webhook automaticamente no Telegram assim que o servidor subir
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
        # Força a limpeza de qualquer conflito antigo de getUpdates
        import requests
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
        print(f"Webhook configurado para: {webhook_url}")

    app.run(host="0.0.0.0", port=port)
