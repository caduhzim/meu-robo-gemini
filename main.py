import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
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
                    texto_final += f"- *{titulo}*: {corpo}\n  🔗 [Link]({link})\n\n"
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
        "QUANDO HOUVER DADOS DE PESQUISA WEB NO CONTEXTO, VOCÊ DEVE OBRIGATORIAMENTE USÁ-LOS PARA RESPONDER EXATAMENTE AO UTILIZADOR, "
        "sem nunca recusar ou dizer que não tem acesso à internet. "
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

def processar_com_groq(current_history, user_message):
    palavras_pesquisa = [
        "pesquise", "pesquisa", "pesquisar", "busca", "busque", "procura", "procure", 
        "encontre", "achar", "me mostra", "mostre", "trazer", "traga", "consulte", 
        "averigue", "cheque", "verifica", "verifique", "confirma", "confirme", "olha", "vê aí",
        "notícia", "notícias", "últimas", "recente", "recentes", "hoje", "ontem", "amanhã", 
        "agora", "atual", "atualizado", "última hora", "lançamento", "lançou", "saiu", 
        "novidade", "novidades", "estado atual", "agenda", "calendário", "data", "quando",
        "quem é", "quem foi", "quem são", "o que é", "o what foi", "o que são", 
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
        "servidor", "cloud", "terminal", "bash", "linux", "termux", "atualização", "changelog", "release"
    ]
    
    precisa_pesquisar = any(p in user_message.lower() for p in palavras_pesquisa)
    historico_temp = list(current_history)
    
    if precisa_pesquisar:
        print(f"A pesquisar na web por: {user_message}")
        dados_web = pesquisar_duckduckgo(user_message)
        if dados_web:
            contexto_web = f"\n\n[DADOS REAIS OBTIDOS NA WEB PARA RESPONDER AO UTILIZADOR]:\n{dados_web}\nUsa obrigatoriamente estes dados para responder de forma direta e natural."
            historico_temp.append({"role": "system", "content": contexto_web})

    if groq_client:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=historico_temp,
                model="mixtral-8x7b-32768",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Erro na Groq com Mixtral: {e}")
            return f"Epa mestre, a Groq engasgou-se: {str(e)}"
    
    return "Epa, o cliente da Groq não está configurado!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]
        try:
            save_message(chat_id, "user", user_message)
            current_history = get_chat_history(chat_id)
            reply_text = processar_com_groq(current_history, user_message)
            save_message(chat_id, "assistant", reply_text)
            enviar_mensagem_telegram(chat_id, reply_text)
        except Exception as e:
            error_msg = f"Erro ao processar a mensagem: {str(e)}"
            print(error_msg)
            enviar_mensagem_telegram(chat_id, error_msg)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Robozim 3.0 com Mixtral e DuckDuckGo online!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
