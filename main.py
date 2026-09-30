import os
import asyncio
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Obter chaves das variáveis de ambiente
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Resposta ao comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Sou o teu assistente Gemini no Telegram. Manda-me dúvidas, pedidos de código ou ideias de aplicativos!"
    )

# Processar mensagens enviadas pelo utilizador
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Exibe a indicação "a escrever..." no Telegram
    await update.message.reply_chat_action("typing")
    
    try:
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao processar o teu pedido: {e}")

# Função principal
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("ERRO: TELEGRAM_TOKEN ou GEMINI_API_KEY não configurados.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot do Telegram iniciado e pronto!")
    app.run_polling()

if __name__ == "__main__":
    main()
