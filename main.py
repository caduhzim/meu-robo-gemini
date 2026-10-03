import os
import requests
from flask import Flask, request
from google import genai
from groq import Groq
from supabase import create_client, Client

app = Flask(__name__)

# Configurações das Credenciais (variáveis de ambiente)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Inicializa o Supabase (Memória)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Inicializa os clientes das IAs
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Estado do Modelo atual (padrão: gemini)
MODELO_ATUAL = "gemini"  # Opções: "gemini" ou "groq"

# Personalidade do Bot
SYSTEM_PROMPT = (
    "Você é o Robozim, um amigo sarcástico, brincalhão e programador. "
    "Você ajuda o Eduardo com código e projetos, mas sempre com tiradas irônicas e descontraídas, "
    "como um bom programador raiz."
)

def buscar_memorias(chat_id):
    """Busca os fatos e aprendizados salvos no Supabase para dar contexto."""
    if not supabase:
        return ""
    try:
        response = supabase.table("memorias_eduardo").select("facto").eq("chat_id", chat_id).order("data_criacao", desc=True).limit(5).execute()
        if response.data:
            memorias = "\n".join([f"- {m['facto']}" for m in response.data])
            return f"\n\nMemórias e aprendizados anteriores com o Eduardo:\n{memorias}"
    except Exception as e:
        print(f"Erro ao buscar memórias: {e}")
    return ""

def salvar_memoria(chat_id, facto):
    """Salva um novo aprendizado ou interação importante no Supabase."""
    if not supabase:
        return
    try:
        supabase.table("memorias_eduardo").insert({"chat_id": chat_id, "facto": facto}).execute()
    except Exception as e:
        print(f"Erro ao salvar memória: {e}")

def perguntar_ia(chat_id, mensagem_usuario):
    """Gera a resposta usando o Gemini ou Groq, injetando a memória persistente."""
    global MODELO_ATUAL
    
    # Comando rápido para alternar modelo via chat se quiser
    if mensagem_usuario.strip().lower() == "/usar groq":
        MODELO_ATUAL = "groq"
        return "Pronto, mestre! Mudei para o Groq. Cuidado para o cérebro dele não derreter de tão rápido."
    elif mensagem_usuario.strip().lower() == "/usar gemini":
        MODELO_ATUAL = "gemini"
        return "Beleza! Voltei para o Gemini. Mais calmo, mas ainda afiado."

    contexto_memoria = buscar_memorias(chat_id)
    prompt_completo = f"{SYSTEM_PROMPT}{contexto_memoria}\n\nMensagem atual do Eduardo: {mensagem_usuario}"

    try:
        if MODELO_ATUAL == "gemini" and gemini_client:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_completo
            )
            resposta = response.text
        elif MODELO_ATUAL == "groq" and groq_client:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + contexto_memoria},
                    {"role": "user", "content": mensagem_usuario}
                ]
            )
            resposta = completion.choices[0].message.content
        else:
            resposta = "Eita, mestre! Nenhuma API válida foi configurada direito."
        
        # Salva a interação relevante na memória
        salvar_memoria(chat_id, f"Usuário disse: {mensagem_usuario} | Resposta: {resposta[:100]}...")
        return resposta

    except Exception as e:
        return f"Deu ruim na IA, mestre: {e}"

def enviar_mensagem_telegram(chat_id, texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
def home():
    return "Robozim com memória persistente está online e operando, mestre!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        texto_usuario = data["message"].get("text", "")
        
        if texto_usuario:
            resposta = perguntar_ia(chat_id, texto_usuario)
            enviar_mensagem_telegram(chat_id, resposta)
            
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

