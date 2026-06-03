"""
gerar_sessao_instagram.py — Gera a sessão do Instagram LOCALMENTE (uma vez).

Por que existe:
    No GitHub Actions o login parte de um IP de datacenter estrangeiro, o que
    quase sempre dispara o "challenge" (verificação) do Instagram. A solução é
    autenticar UMA vez no seu computador (IP residencial), resolver o desafio
    aqui, salvar a sessão e colá-la como secret INSTAGRAM_SESSION no GitHub.
    O instagram_poster.py reaproveita essa sessão e não precisa logar de novo.

Como usar (Windows / PowerShell), na raiz do projeto:

    pip install -r requirements-instagram.txt
    $env:INSTAGRAM_USER = "seu_usuario"
    $env:INSTAGRAM_PASS = "sua_senha"
    py gerar_sessao_instagram.py

Se o Instagram pedir um código (e-mail/SMS), ele será solicitado aqui no
terminal. No fim, o script imprime um texto em base64 — copie TODO ele e
cole no secret INSTAGRAM_SESSION do GitHub
(Settings → Secrets and variables → Actions → New repository secret).
"""
import base64
import os
import sys
from pathlib import Path

try:
    from instagrapi import Client
except ImportError:
    sys.exit("instagrapi não instalado. Rode: pip install -r requirements-instagram.txt")

USER = os.environ.get("INSTAGRAM_USER", "").strip()
PASS = os.environ.get("INSTAGRAM_PASS", "").strip()
SESSION_FILE = Path("session.json")

if not USER or not PASS:
    sys.exit("Defina INSTAGRAM_USER e INSTAGRAM_PASS no ambiente antes de rodar.")


def _code_handler(username, choice):
    """Pede o código de verificação no terminal (challenge interativo)."""
    return input(f"   → Código de verificação enviado ({choice}) para {username}: ").strip()


def main():
    print("🔐 Gerando sessão do Instagram para @" + USER)
    print("─" * 50)

    cl = Client()
    cl.delay_range = [2, 5]
    cl.challenge_code_handler = _code_handler

    # Reaproveita sessão anterior, se existir (refresh em vez de login do zero)
    if SESSION_FILE.exists():
        try:
            cl.load_settings(str(SESSION_FILE))
            print("   Sessão anterior carregada — tentando reaproveitar.")
        except Exception:
            pass

    try:
        cl.login(USER, PASS)
        cl.get_timeline_feed()  # valida
    except Exception as e:
        sys.exit(f"❌ Falha no login: {e}")

    cl.dump_settings(str(SESSION_FILE))
    b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()

    print("\n✅ Sessão criada e salva em session.json (não comite esse arquivo).")
    print("\n" + "=" * 60)
    print("COPIE TODO o texto abaixo e cole no secret INSTAGRAM_SESSION:")
    print("=" * 60 + "\n")
    print(b64)
    print("\n" + "=" * 60)
    print("Depois: GitHub → Settings → Secrets and variables → Actions")
    print("→ New repository secret → Name: INSTAGRAM_SESSION → cole o valor.")
    print("=" * 60)


if __name__ == "__main__":
    main()
