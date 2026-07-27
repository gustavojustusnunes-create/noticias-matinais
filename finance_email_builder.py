"""
finance_email_builder.py — Geração de HTML em Azul Marinho e envio do All News Finance
"""
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_FROM,
    SMTP_HOST, SMTP_PORT, URL_CANCELAMENTO,
    RESEND_API_KEY, RESEND_FROM,
)
from email_builder import obter_indicadores
from finance_feeds import ORDEM_CADERNOS_FINANCE

ICONES_FINANCE = {
    "Mercado & Bolsa": "📊",
    "Empresas & Negócios": "🏢",
    "Macroeconomia": "🌎",
    "Cripto & FinTechs": "🚀",
}


def construir_html_finance(edicao, nome_destinatario="Leitor(a)"):
    """Gera o HTML da newsletter All News Finance com identidade visual Azul Marinho."""
    hoje_formatado = datetime.now().strftime("%d de %B de %Y")

    # Ticker do mercado financeiro (dólar, ibov, btc)
    try:
        painel_html = obter_indicadores()
    except Exception:
        painel_html = ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>All News Finance — {hoje_formatado}</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; }}
  .container {{ max-width: 640px; margin: 0 auto; background-color: #ffffff; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; }}
  .header {{ background: linear-gradient(135deg, #0a2540 0%, #0f3156 100%); padding: 35px 25px; text-align: center; border-bottom: 4px solid #c9a84c; }}
  .header h1 {{ margin: 0; color: #ffffff; font-size: 32px; letter-spacing: 2px; font-family: 'Playfair Display', Georgia, serif; font-weight: 700; }}
  .header .subtitle {{ margin-top: 8px; color: #c9a84c; font-size: 13px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }}
  .date-bar {{ background-color: #0f172a; color: #94a3b8; font-size: 12px; padding: 10px 25px; text-align: center; border-bottom: 1px solid #1e293b; }}
  .ticker-bar {{ background-color: #f1f5f9; padding: 12px 20px; font-size: 12px; text-align: center; border-bottom: 1px solid #e2e8f0; color: #334155; }}
  .content {{ padding: 30px 25px; }}
  .greeting {{ font-size: 16px; color: #334155; margin-bottom: 25px; line-height: 1.6; }}
  .section-title {{ background-color: #0a2540; color: #ffffff; padding: 12px 18px; font-size: 16px; font-weight: 700; border-left: 4px solid #c9a84c; margin: 30px 0 20px 0; border-radius: 4px; letter-spacing: 0.5px; }}
  .news-item {{ margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid #f1f5f9; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-title {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px; line-height: 1.4; }}
  .news-summary {{ font-size: 15px; color: #475569; line-height: 1.65; margin-bottom: 12px; }}
  .news-meta {{ font-size: 12px; color: #64748b; }}
  .news-link {{ color: #0a2540; font-weight: 600; text-decoration: none; border-bottom: 1px dotted #c9a84c; }}
  .footer {{ background-color: #0f172a; color: #94a3b8; font-size: 12px; text-align: center; padding: 30px 25px; line-height: 1.6; }}
  .footer a {{ color: #c9a84c; text-decoration: none; }}
  @media only screen and (max-width: 480px) {{
    .container {{ width: 100% !important; border: none; }}
    .content {{ padding: 20px 15px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>ALL NEWS FINANCE</h1>
    <div class="subtitle">Briefing de Economia, Mercados e Negócios</div>
  </div>
  <div class="date-bar">Edição de {hoje_formatado}</div>
"""

    if painel_html:
        html += f'  <div class="ticker-bar">{painel_html}</div>\n'

    html += f"""  <div class="content">
    <div class="greeting">
      Olá, <b>{nome_destinatario}</b>!<br>
      Confira o que está movendo os mercados, empresas e a economia nesta manhã antes da abertura do pregão.
    </div>
"""

    # Renderiza as 4 seções editoriais
    for secao in ORDEM_CADERNOS_FINANCE:
        noticias = edicao.get(secao, [])
        if not noticias:
            continue

        icone = ICONES_FINANCE.get(secao, "📊")
        html += f"""    <div class="section-title">{icone} {secao.upper()}</div>\n"""

        for item in noticias:
            titulo = item.get("titulo", "")
            resumo = item.get("resumo", "")
            link = item.get("link", "#")
            fonte = item.get("fonte", "Mercado")

            html += f"""    <div class="news-item">
      <div class="news-title"><a href="{link}" style="color: #0f172a; text-decoration: none;">{titulo}</a></div>
      <div class="news-summary">{resumo}</div>
      <div class="news-meta">
        Fonte: {fonte} &bull; <a href="{link}" class="news-link">Ler matéria original &rarr;</a>
      </div>
    </div>\n"""

    html += f"""  </div>
  <div class="footer">
    <b>ALL NEWS FINANCE</b> &mdash; Um braço do All News Journal<br>
    Você recebeu este e-mail porque está inscrito na nossa edição diária financeira.<br>
    <a href="https://allnewsjournal.streamlit.app/">Acessar portal na web</a> &bull; 
    <a href="{URL_CANCELAMENTO}&finance=1">Cancelar assinatura</a>
  </div>
</div>
</body>
</html>"""

    return html


def enviar_email_resend(destinatario, assunto, html_content):
    """Envia email usando a API da Resend (HTTPS)."""
    if not RESEND_API_KEY:
        return False
    try:
        import requests
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": RESEND_FROM,
            "to": [destinatario],
            "subject": assunto,
            "html": html_content,
        }
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"      ⚠️ Resend erro: {e}")
        return False


def enviar_email_smtp(destinatario, assunto, html_content):
    """Envia email usando SMTP com autenticação."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = EMAIL_FROM
        msg["To"] = destinatario
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"      ⚠️ SMTP erro: {e}")
        return False


def enviar_email_finance(destinatario, assunto, html_content):
    """Tenta enviar pelo Resend com fallback para SMTP Gmail."""
    if RESEND_API_KEY and enviar_email_resend(destinatario, assunto, html_content):
        return True
    return enviar_email_smtp(destinatario, assunto, html_content)
