import http.server
import socketserver
import threading
import time
import os

# Servidor Web para manter o serviço gratuito do Render ativo
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

print("Robô Gemini iniciado e rodando na nuvem!")

# Lógica do robô em loop contínuo
while True:
    print("Robô ativo e aguardando tarefas...")
    time.sleep(60)  # Aguarda 60 segundos antes de cada ciclo
