import os
import telebot
from huggingface_hub import InferenceClient
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO DAS VARIÁVEIS DE AMBIENTE ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validação rápida para garantir que nada está faltando
if not all([BOT_TOKEN, HF_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    print("Erro: Alguma variável de ambiente (Token, Hugging Face ou Supabase) não foi configurada!")

# Inicializa o Bot do Telegram
bot = telebot.TeleBot(BOT_TOKEN)

# Inicializa o cliente de IA do Hugging Face (usando um modelo open-source potente)
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3", 
    token=HF_TOKEN
)

# Inicializa o cliente do Supabase (para salvar a memória das conversas)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. FUNÇÃO PARA SALVAR MENSAGEM NO SUPABASE ---
def salvar_no_supabase(user_id, username, mensagem, resposta):
    try:
        dados = {
            "user_id": str(user_id),
            "username": str(username),
            "mensagem_usuario": str(mensagem),
            "resposta_bot": str(resposta)
        }
        # Nota: Certifique-se de que a tabela no Supabase se chama 'historico_chat' 
        # ou ajuste o nome abaixo para o nome da sua tabela.
        supabase.table("historico_chat").insert(dados).execute()
    except Exception as e:
        print(f"Aviso: Não conseguiu salvar no Supabase: {e}")

# --- 3. RECEBIMENTO E RESPOSTA DAS MENSAGENS ---
@bot.message_handler(func=lambda message: True)
def responder(message):
    user_id = message.from_user.id
    username = message.from_user.username or "SemUsername"
    texto_usuario = message.text
    
    print(f"Mensagem recebida de {username}: {texto_usuario}")
    
    try:
        # Envia a mensagem para a IA do Hugging Face com a personalidade configurada
        resposta_ia = client.chat_completion(
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um amigo programador sarcástico, brincalhão, direto e prestativo. Ajuda o usuário (que está programando do celular via Termux) com bom humor e tiradas irônicas, mas entregando o código certo."
                },
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=400,
            temperature=0.7,
        )
        
        texto_resposta = resposta_ia.choices[0].message.content
        
        # Salva o histórico no Supabase em segundo plano
        salvar_no_supabase(user_id, username, texto_usuario, texto_resposta)
        
        # Responde o usuário lá no Telegram
        bot.reply_to(message, texto_resposta)
        
    except Exception as e:
        erro_msg = f"Deu ruim aqui, chefe: {e}"
        print(erro_msg)
        bot.reply_to(message, erro_msg)

# --- 4. INICIALIZAÇÃO DO BOT ---
print("Bot do Telegram ligado, conectado ao Supabase e pronto para rodar com o Hugging Face!")
bot.infinity_polling()

