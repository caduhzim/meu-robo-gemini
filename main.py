import os
from flask import Flask, request
from groq import Groq
import telegram

app = Flask(__name__)

# Configurações usando variáveis de ambiente do Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Inicializa o cliente da Groq e o bot do Telegram
client = Groq(api_key=GROQ_API_KEY)
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Histórico simples de conversas por chat_id
historico_conversas = {}

# System Prompt para definir a personalidade de assistente programador avançado
SYSTEM_PROMPT = {
    "role": "system",
    "content": "Você é um assistente virtual avançado, programador sênior e arquiteto de software. Você ajuda o usuário a criar códigos, estruturar sites, debugar erros e planejar melhorias, respondendo de forma direta, clara e prática pelo Telegram."
}

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        texto_usuario = message.get("text")
        
        if texto_usuario:
            # 1. Inicializa o histórico do chat se ele não existir
            if chat_id not in historico_conversas:
                historico_conversas[chat_id] = [SYSTEM_PROMPT]
            
            # 2. Adiciona a mensagem do usuário
            historico_conversas[chat_id].append({"role": "user", "content": texto_usuario})
            
            # Limita o histórico para manter o system prompt + últimas 10 mensagens
            if len(historico_conversas[chat_id]) > 11:
                historico_conversas[chat_id] = [historico_conversas[chat_id][0]] + historico_conversas[chat_id][-10:]

            try:
                # 3. Chama a API da Groq com o modelo Llama 3.3 70B
                chat_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=historico_conversas[chat_id],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                resposta_ia = chat_completion.choices[0].message.content
                
                # 4. Adiciona a resposta da IA ao histórico
                historico_conversas[chat_id].append({"role": "assistant", "content": resposta_ia})
                
                # 5. Envia a resposta de volta para o Telegram
                bot.send_message(chat_id=chat_id, text=resposta_ia)
                
            except Exception as e:
                print(f"Erro ao chamar a Groq: {e}")
                bot.send_message(chat_id=chat_id, text="Opa, tive um pequeno problema ao processar sua resposta na Groq. Tente novamente em instantes!")

    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot do Telegram com Groq rodando perfeitamente!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
