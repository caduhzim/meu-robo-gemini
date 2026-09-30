import http.server
import socketserver
import threading
import time
import os

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

print("Robô Gemini iniciado e rodando na nuvem!")

while True:
    print("Robô ativo...")
    time.sleep(60)
