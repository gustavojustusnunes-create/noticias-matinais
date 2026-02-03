import os
import smtplib
import feedparser
import requests
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time
import sys

# --- 1. CONFIGURAÇÕES ---
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()
GCP_JSON = os.environ.get("GCP_JSON")
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/"
}

# --- 2. SERVIÇOS DE INFRAESTRUTURA ---

def conectar_banco():
    if not GCP_JSON:
        print("❌ ERRO: GCP_JSON não encontrado.")
        return None
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("noticias_db").sheet1
    except Exception as e:
        print(f"❌ Erro Banco: {e}")
        return None

# --- 3. INTELIGÊNCIA ARTIFICIAL (Atualizado para v2.0) ---

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None

    # AQUI ESTÁ A CORREÇÃO: Usamos os modelos que o log mostrou disponíveis
    modelos = [
        "gemini-2.0-flash",       # Tentativa 1: O mais rápido da nova geração
        "gemini-2.0-flash-exp",   # Tentativa 2: Experimental
        "gemini-1.5-flash-latest" # Tentativa 3: Fallback legado
    ]
    
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        # Nota: Mantivemos v1beta pois é onde esses modelos costumam habitar
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                except:
                    return f"<p>Erro leitura JSON ({modelo})</p>"
            else:
                # Se falhar, tenta o próximo silenciosamente (apenas loga)
                print(f"   ⚠️ {modelo} falhou ({response.status_code}). Tentando próximo...") 
                continue

        except Exception as e:
            print(f"   ⚠️ Erro rede {modelo}: {e}")
            continue

    return None

def buscar_e_resumir(tema):
    print(f"      ...Processando {tema}...")
    url = RSS_FEEDS.get(tema)
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries: return "<p>Sem notícias.</p>"
        
        top = feed.entries[:5]
        texto = "\n".join([f"- {e.title}: {e.link}" for e in top])
        
        prompt = f"""
        Atue como editor de newsletter. 
        Resuma estas notícias de {tema} em 2 parágrafos HTML (sem markdown, apenas tags <p>, <b>, etc).
        Seja leve e direto. Comece com um emoji.
        No final, liste os links originais em <ul>.
        Notícias:
        {texto}
        """
        
        resumo = chamar_gemini_api(prompt)
        
        if resumo:
            return resumo
        else:
            links = "".join([f"<li><a href='{n.link}'>{n.title}</a></li>" for n in top])
            return f"<p>IA indisponível. Manchetes:</p><ul>{links}</ul>"

    except Exception:
        return "<p>Erro no feed.</p>"

# --- 4. TEMPLATE E ENVIO ---

def gerar_template_email(nome, conteudos):
    html = f"""
    <html><body style="font-family:sans-serif; padding:20px; background:#f4f4f9;">
    <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px;">
        <h2 style="text-align:center">☕ Briefing Matinal</h2>
        <p>Bom dia, <b>{nome}</b>!</p>
    """
    for tema, texto in conteudos.items():
        cor = "#28a745" if tema == "Mercado" else "#007bff"
        html += f"<div style='margin-bottom:20px; border:1px solid #ddd; padding:15px;'><b style='color:{cor}'>{tema}</b><br>{texto}</div>"
    
    html += "</div></body></html>"
    return html

def enviar_email(destinatario, html):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"☕ Resumo {datetime.now().strftime('%d/%m')}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = destinatario
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Erro SMTP: {e}")
        return False

# --- MAIN ---

def main():
    print("🚀 Iniciando Motor (v3.0 - Gemini 2.0)...")
    
    sheet = conectar_banco()
    if not sheet: return

    usuarios = sheet.get_all_records()
    print(f"📋 {len(usuarios)} usuários.")
    
    cache = {}

    for usr in usuarios:
        nome, email = usr.get('Nome'), usr.get('Email')
        if not nome or not email: continue
        
        print(f"🔄 {nome}...")
        conteudos = {}
        
        for tema in ["Mercado", "Tech", "Motos", "Fofoca"]:
            if usr.get(tema, '').lower() == "sim":
                if tema not in cache:
                    cache[tema] = buscar_e_resumir(tema)
                    time.sleep(1) # Respeitar rate limit
                conteudos[tema] = cache[tema]

        if conteudos and enviar_email(email, gerar_template_email(nome, conteudos)):
            print("   ✅ Enviado.")

if __name__ == "__main__":
    main()
