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
# .strip() remove espaços e quebras de linha invisíveis (Erro comum em Secrets)
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

# --- 3. DIAGNÓSTICO E IA ---

def testar_conexao_google():
    """Verifica quais modelos estão disponíveis para esta Chave."""
    print("🔍 [Diagnóstico] Testando chave e listando modelos...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            modelos = [m['name'].replace('models/', '') for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            print(f"   ✅ Sucesso! Modelos disponíveis: {modelos[:3]}... (+{len(modelos)-3})")
            return True
        else:
            print(f"   ❌ Erro de Permissão/API: {response.status_code}")
            print(f"   ⚠️ Detalhe: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Erro de Conexão no teste: {e}")
        return False

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None

    # Lista ampliada de tentativas
    modelos = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro", 
        "gemini-1.0-pro"
    ]

    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                except:
                    return f"<p>Erro leitura JSON ({modelo})</p>"
            
            # AGORA VAMOS VER O ERRO REAL NO LOG
            elif response.status_code != 200:
                print(f"   ⚠️ Falha em {modelo} ({response.status_code}): {response.text[:100]}...") 
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

        prompt = f"Resuma estas notícias de {tema} em 2 parágrafos HTML (sem markdown) com links no final:\n{texto}"

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
    print("🚀 Iniciando (Modo Raio-X)...")
    
    # Passo 0: Diagnóstico da API
    api_ok = testar_conexao_google()
    if not api_ok:
        print("🚨 ALERTA: A IA provavelmente vai falhar. Verifique a chave no passo acima.")

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
                    time.sleep(1)
                conteudos[tema] = cache[tema]

        if conteudos and enviar_email(email, gerar_template_email(nome, conteudos)):
            print("   ✅ Enviado.")

if __name__ == "__main__":
    main()
