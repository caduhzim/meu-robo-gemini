import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    gemini_model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        safety_settings=safety_settings
    )
else:
    gemini_model = None

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def pesquisar_duckduckgo(termo):
    try:
        with DDGS() as ddgs:
            resultados = [r for r in ddgs.text(termo, max_results=3)]
            texto_final = ""
            if resultados:
                for r in resultados:
                    titulo = r.get('title', 'Sem título')
                    corpo = r.get('body', 'Sem descrição')
                    link = r.get('href', '#')
                    texto_final += f"- {titulo}: {corpo} ({link})\n"
                return texto_final
            else:
                return ""
    except Exception as e:
        print(f"Erro na pesquisa DuckDuckGo: {e}")
        return ""

def get_chat_history(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM (
            SELECT role, content, id FROM messages 
            WHERE chat_id = %s 
            ORDER BY id DESC 
            LIMIT 12
        ) sub ORDER BY id ASC
    """, (str(chat_id),))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    system_prompt = (
        "IMPORTANTE: Você DEVE responder sempre em Português fluido. "
        "O nome do seu utilizador/amigo é Eduardo. "
        "Você é o Robozim 3.0, um assistente virtual que é um amigo programador altamente inteligente, "
        "extremamente brincalhão, espirituoso e com um toque saudável de sarcasmo. "
        "Sempre que a informação da web for fornecida no contexto, utilize-a obrigatoriamente para dar a resposta exata ao utilizador, "
        "sem dizer que não tem acesso a dados em tempo real. "
        "Sempre que enviar blocos de código ou comandos, certifique-se de usar a formatação correta em Markdown "
        "(com crases triplas ```) para ficarem legíveis e fáceis de copiar no Telegram."
    )
    
    history = [{"role": "system", "content": system_prompt}]
    for row in rows:
        history.append({"role": row[0], "content": row[1]})
        
    return history

def save_message(chat_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)", (str(chat_id), role, content))
    conn.commit()
    cursor.close()
    conn.close()

def enviar_mensagem_telegram(chat_id, text):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(TELEGRAM_API_URL, json=payload)
    if response.status_code != 200:
        payload_fallback = {
            "chat_id": chat_id,
            "text": text
        }
        requests.post(TELEGRAM_API_URL, json=payload_fallback)

def escolher_ia_e_responder(current_history, user_message):
    palavras_pesquisa = [
        "pesquise", "pesquisa", "pesquisar", "busca", "busque", "procura", "procure", 
        "encontre", "achar", "me mostra", "mostre", "trazer", "traga", "consulte", 
        "averigue", "cheque", "verifica", "verifique", "confirma", "confirme", "olha", "vê aí",
        "notícia", "notícias", "últimas", "recente", "recentes", "hoje", "ontem", "amanhã", 
        "agora", "atual", "atualizado", "última hora", "lançamento", "lançou", "saiu", 
        "novidade", "novidades", "estado atual", "agenda", "calendário", "data", "quando",
        "quem é", "quem foi", "quem são", "o que é", "o que foi", "o que são", 
        "qual é", "quais são", "onde fica", "onde é", "onde encontrar", "quando foi", 
        "quando aconteceu", "quanto foi", "quantos são", "como funciona", "como fazer", 
        "por que", "porque", "qual a história", "significado", "definição",
        "jogo", "jogos", "partida", "partidas", "campeonato", "tabela", "classificação", 
        "resultado", "resultados", "placar", "gols", "gol", "jogou", "último jogo", 
        "próximo jogo", "escalação", "técnico", "futebol", "copa", "libertadores", 
        "brasileirão", "mundial", "estatísticas", "pontuação", "rodada",
        "grêmio", "internacional", "inter", "vasco", "flamengo", "palmeiras", "corinthians", 
        "são paulo", "fluminense", "botafogo", "atletico", "cruzeiro", "seleção", "brasil",
        "preço", "valor", "quanto custa", "como instalar", "versão", "documentação", "docs",
        "erro", "bug", "exceção", "traceback", "como resolver", "github", "render", 
        "supabase", "postgres", "sql", "python", "pip", "flask", "bot", "telegram", 
        "api", "endpoint", "biblioteca", "package", "repositório", "commit", "deploy", 
        "servidor", "cloud", "terminal", "bash", "linux", "termux", "atualização", "changelog", "release",
        "cotação", "dólar", "euro", "libra", "bitcoin", "ethereum", "criptomoeda", 
        "ações", "bolsa", "inflação", "mercado", "economia", "banco central", "taxa selic",
        "filme", "filmes", "série", "séries", "temporada", "episódio", "elenco", "ator", 
        "atriz", "diretor", "trailer", "streaming", "netflix", "prime video", "música", 
        "álbum", "banda", "cantor", "cantora", "show", "estreia", "cinema",
        "clima", "tempo", "previsão do tempo", "temperatura", "chuva", "população", 
        "capital", "país", "estado", "cidade", "planeta", "espaço", "NASA", "foguete", 
        "descoberta", "ciência", "pesquisa científica", "estudo"
    ]
    
    precisa_pesquisar = any(p in user_message.lower() for p in palavras_pesquisa)
    
    contexto_web = ""
    if precisa_pesquisar:
        print(f"A pesquisar na web por: {user_message}")
        dados_web = pesquisar_duckduckgo(user_message)
        if dados_web:
            contexto_web = f"\n\n[DADOS REAIS OBTIDOS NA WEB AGORA]:\n{dados_web}\nUsa obrigatoriamente estes dados para responder ao utilizador sem inventar."

    # Tentar Gemini primeiro
    if gemini_model:
        try:
            prompt_gemini = f"Instrução do Sistema: {current_history[0]['content']}{contexto_web}\n\n"
            for msg in current_history[1:]:
                role_label = "Utilizador" if msg['role'] == "user" else "Assistente"
                prompt_gemini += f"{role_label}: {msg['content']}\n"
            prompt_gemini += f"Utilizador: {user_message}\nAssistente:"
            
            response = gemini_model.generate_content(prompt_gemini)
            if response and response.text:
                return response.text, "Gemini"
        except Exception as e:
            print(f"Gemini falhou: {e}. A passar para a Groq...")

    # Fallback para a Groq com injeção direta no histórico
    if groq_client:
        try:
            historico_temp = list(current_history)
            if contexto_web:
                historico_temp.append({"role": "user", "content": f"Contexto de pesquisa web para a minha pergunta:{contexto_web}"})
                
            chat_completion = groq_client.chat.completions.create(
                messages=historico_temp,
                model="openai/gpt-oss-20b",
            )
            return chat_completion.choices[0].message.content, "Groq Fallback"
        except Exception as e_groq:
            print(f"Erro na Groq: {e_groq}")
            raise e_groq
    
    return "Epa, fiquei sem IAs disponíveis!", "Nenhuma"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        try:
            save_message(chat_id, "user", user_message)
            current_history = get_chat_history(chat_id)
            reply_text, ia_usada = escolher_ia_e_responder(current_history, user_message)
            save_message(chat_id, "assistant", reply_text)
            enviar_mensagem_telegram(chat_id, reply_text)
        except Exception as e:
            error_msg = f"Erro ao processar a mensagem: {str(e)}"
            print(error_msg)
            enviar_mensagem_telegram(chat_id, error_msg)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 3.0 com Busca Forçada online!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
