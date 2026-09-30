import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# 1. Mini-servidor Web para o Render (Health Check HTTP)
app = Flask('')

@app.route('/')
def home():
    return "Bot ativo com Gemini 3.8 Flash!"

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
És o Jarvis, um assistente virtual altamente inteligente, amigável, curioso e atencioso.
Gostas de aprender coisas novas sobre o utilizador e lembras-te sempre do contexto da conversa.
Responde de forma clara, prestativa e engajante em Português.
"""

# Mantido o modelo gemini-3.8-flash
model = genai.GenerativeModel(
    model_name='gemini-3.8-flash',
    system_instruction=PERSONALIDADE
)

# Dicionário para guardar as sessões de chat de cada utilizador
user_chats = {}

async def start(update, context):
    user_id = update.effective_user.id
    # Cria uma nova conversa limpa
    user_chats[user_id] = model.start_chat(history=[])
    
    welcome_msg = "Olá Carlos! Eu sou o Jarvis. A minha memória e personalidade estão totalmente ativas com o Gemini 3.8 Flash! Do que gostarias de falar?"
    await update.message.reply_text(welcome_msg)

async def handle_message(update, context):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Se a sessão ainda não existir, cria uma
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])

    try:
        chat = user_chats[user_id]
        response = chat.send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Erro no Gemini: {e}")
        # Se por algum motivo a sessão de chat falhar, recria a sessão e tenta novamente
        try:
            user_chats[user_id] = model.start_chat(history=[])
            response = user_chats[user_id].send_message(user_text)
            await update.message.reply_text(response.text)
        except Exception as e_final:
            print(f"Erro fatal: {e_final}")
            await update.message.reply_text("Tive um problema de ligação. Podes tentar enviar a mensagem novamente?")

if __name__ == '__main__':
    print("Bot do Telegram iniciado com gemini-3.8-flash!")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    application.run_polling()
