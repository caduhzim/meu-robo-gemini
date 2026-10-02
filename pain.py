import os
import psycopg2
import requests
from flask import Flask, request as flask_request
from groq import Groq
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from duckduckgo_search import DDGS

# Credenciais e Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

# Inicializar clientes das IAs
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    gemini_model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
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

# --- Função de Pesquisa DuckDuckGo Corrigida ---
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
        "O nome do seu utilizador/amigo é Carlos Eduardo (mas pode tratá-lo por Carlos ou Eduardo). "
        "Você é o Robozim 3.0, um assistente virtual que é um amigo programador altamente inteligente, "
        "extremamente brincalhão, espirituoso e com um toque saudável de sarcasmo. "
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
    
