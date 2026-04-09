#!/usr/bin/env python3
"""
YouTube OAuth flow automático.
Abre o navegador, captura o código via servidor local e salva os tokens.

Uso:
  python auth.py setup --client-id ID --client-secret SECRET
  python auth.py setup --from-json /path/to/client_secrets.json
  python auth.py refresh
  python auth.py status
"""

import argparse
import json
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "yt-playlist-organizer"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
REDIRECT_PORT = 8888
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube"


def read_config(key):
    path = CONFIG_DIR / key
    return path.read_text().strip() if path.exists() else None


def write_config(key, value):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / key
    path.write_text(value)
    path.chmod(0o600)


def exchange_code(client_id, client_secret, code):
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def refresh_tokens(client_id, client_secret, refresh_token):
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def cmd_setup(args):
    if args.from_json:
        raw = json.loads(Path(args.from_json).read_text())
        creds = raw.get("installed") or raw.get("web") or raw
        client_id = creds["client_id"]
        client_secret = creds["client_secret"]
    else:
        client_id = args.client_id
        client_secret = args.client_secret

    if not client_id or not client_secret:
        print("ERRO: --client-id e --client-secret são obrigatórios (ou use --from-json)", file=sys.stderr)
        sys.exit(1)

    write_config("client_id", client_id)
    write_config("client_secret", client_secret)

    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    captured_code = []
    server_ready = threading.Event()
    server_error = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                captured_code.append(params["code"][0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px">
                <h2>Autorizado com sucesso!</h2>
                <p>Pode fechar esta aba.</p>
                </body></html>""")
            else:
                error = params.get("error", ["desconhecido"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<html><body>Erro: {error}</body></html>".encode())

    try:
        httpd = HTTPServer(("localhost", REDIRECT_PORT), Handler)
    except OSError as e:
        print(f"ERRO: não foi possível iniciar servidor na porta {REDIRECT_PORT}: {e}", file=sys.stderr)
        sys.exit(1)

    def serve():
        server_ready.set()
        while not captured_code:
            httpd.handle_request()
        httpd.server_close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    server_ready.wait()

    print("Abrindo navegador para autorização...")
    webbrowser.open(auth_url)
    print("Aguardando autorização (pode fechar esta janela após clicar em 'Permitir')...")

    timeout = 120
    start = time.time()
    while not captured_code and time.time() - start < timeout:
        time.sleep(0.5)

    if not captured_code:
        print("ERRO: tempo esgotado aguardando autorização.", file=sys.stderr)
        sys.exit(1)

    code = captured_code[0]
    print("Código capturado. Trocando por tokens...")

    try:
        tokens = exchange_code(client_id, client_secret, code)
    except Exception as e:
        print(f"ERRO ao trocar código por tokens: {e}", file=sys.stderr)
        sys.exit(1)

    write_config("access_token", tokens["access_token"])
    if "refresh_token" in tokens:
        write_config("refresh_token", tokens["refresh_token"])

    print("Autenticação concluída com sucesso!")
    print(f"Tokens salvos em: {CONFIG_DIR}")


def cmd_refresh(args):
    client_id = read_config("client_id")
    client_secret = read_config("client_secret")
    refresh_token = read_config("refresh_token")

    if not all([client_id, client_secret, refresh_token]):
        print("ERRO: credenciais incompletas. Execute 'auth.py setup' primeiro.", file=sys.stderr)
        sys.exit(1)

    try:
        tokens = refresh_tokens(client_id, client_secret, refresh_token)
    except Exception as e:
        print(f"ERRO ao refrescar token: {e}", file=sys.stderr)
        sys.exit(1)

    write_config("access_token", tokens["access_token"])
    print("Token atualizado com sucesso.")


def cmd_status(args):
    keys = ["client_id", "client_secret", "access_token", "refresh_token"]
    for key in keys:
        val = read_config(key)
        status = "OK" if val else "AUSENTE"
        print(f"{key}: {status}")


def main():
    parser = argparse.ArgumentParser(description="YouTube OAuth helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="Configurar OAuth e autorizar")
    p_setup.add_argument("--client-id", default=None)
    p_setup.add_argument("--client-secret", default=None)
    p_setup.add_argument("--from-json", default=None, metavar="FILE",
                         help="Caminho para o arquivo client_secrets.json baixado do Google Cloud")

    sub.add_parser("refresh", help="Refrescar access token usando refresh token")
    sub.add_parser("status", help="Verificar status das credenciais")

    args = parser.parse_args()
    {"setup": cmd_setup, "refresh": cmd_refresh, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
