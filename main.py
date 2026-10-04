import os
import telebot
from huggingface_hub import InferenceClient

# Pega os tokens direto das variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# Limpa qualquer webhook preso no Telegram para evitar conflito de polling
bot.remove_webhook()

# Conecta no Hugging Face usando um modelo de código aberto inteligente
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3", 
    token=HF_TOKEN
)

@bot.message_handler(func=lambda message: True)
def responder(message):
    texto_usuario = message.text
    
    try:
        # Envia a mensagem para a IA com a personalidade de amigo programador sarcástico
        resposta_ia = client.chat_completion(
            messages=[
                {"role": "system", "content": "Você é um amigo programador sarcástico, brincalhão, direto e prestativo."},
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=400,
            temperature=0.7,
        )
        
        texto_resposta = resposta_ia.choices[0].message.content
        
        # Manda a resposta de volta lá no Telegram
        bot.reply_to(message, texto_resposta)
        
    except Exception as e:
        bot.reply_to(message, f"Deu ruim aqui, chefe: {e}")

print("Bot rodando e conectado ao Hugging Face...")
bot.infinity_polling()

