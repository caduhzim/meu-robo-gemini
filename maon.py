import os
import requests

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("Erro: A variável de ambiente GEMINI_API_KEY não foi configurada.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

print("--- Robô Assistente Iniciado ---")
print("Digite 'sair' para encerrar.\n")

while True:
    pergunta = input("Você: ")
    if pergunta.lower() == "sair":
        break

    payload = {
        "contents": [{"parts": [{"text": pergunta}]}]
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            resposta_texto = data['candidates'][0]['content']['parts'][0]['text']
            print(f"\nIA: {resposta_texto}\n")
        else:
            print(f"\nErro da API ({response.status_code}): {data}\n")
    except Exception as e:
        print(f"\nErro de conexão/código: {e}\n")
