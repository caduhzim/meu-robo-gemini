import http.server
import socketserver
import threading
import time
import os

# Cria um servidor HTTP simples em segundo plano para o Render aceitar o Web Service gratuito
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# O TEU CÓDIGO DO GEMINI COMEÇA AQUI:
print("Robô Gemini iniciado com sucesso!")

while True:
    # Coloca aqui a lógica principal do teu robô
    time.sleep(60)
