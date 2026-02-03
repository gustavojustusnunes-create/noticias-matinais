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

# --- 3. INTELIGÊNCIA ARTIFICIAL (Com Retry Logic) ---

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None

    # Focamos no modelo que sabemos que existe (vimos no log anterior)
    modelos = ["gemini-2.0-flash", "gemini-2.0-flash-exp"]
    
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        
        # Tenta até 3 vezes o mesmo modelo se der erro de "Muitas Requisições" (429)
        for tentativa in range(1, 4):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    try:
                        return response.json()['candidates'][0]['content']['parts'][0]['text']
                    except:
                        return f"<p>Erro leitura JSON ({modelo})</p>"
                
                elif response.status_code == 429:
                    # AQUI ESTÁ A MÁGICA: Se der erro de limite, espera e tenta de novo
                    tempo_espera = 20 * tentativa # Espera 20s, depois 40s...
                    print(f"   ⏳ {modelo} sobrecarregado (429). Esperando {tempo_espera}s para tentar de novo...")
                    time.sleep(tempo_espera)
                    continue # Volta para o início do loop de tentativas
                
                elif response.status_code == 404:
                    # Se não existe, nem adianta tentar de novo, pula para o próximo modelo
                    print(f"   ⚠️ {modelo} não encontrado (404).")
                    break 

                else:
                    print(f"   ⚠️ Falha em {modelo} ({response.status_code}).")
                    break

            except Exception as e:
                print(f"   ⚠️ Erro rede {modelo}: {e}")
                break # Se for erro de rede grave, melhor pular

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
            return f"<p>IA indisponível (Rate Limit). Manchetes:</p><ul>{links}</ul>"

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
    print("🚀 Iniciando Motor (v3.1 - Anti-429 Rate Limit)...")
    
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
                    # AUMENTO DE PAUSA: Espera 10 segundos entre temas para não estourar o limite
                    print("      💤 Respirando 10s para a API...")
                    time.sleep(10) 
                conteudos[tema] = cache[tema]

        if conteudos and enviar_email(email, gerar_template_email(nome, conteudos)):
            print("   ✅ Enviado.")

if __name__ == "__main__":
    main()
