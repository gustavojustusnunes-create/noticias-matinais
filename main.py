import os
import smtplib
import feedparser
import requests  # <--- MUDANÇA: Usaremos requests direto
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time
import sys

# --- 1. CONFIGURAÇÕES E CONSTANTES ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
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
        print("❌ ERRO CRÍTICO: GCP_JSON não encontrado.")
        sys.exit(1)
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("noticias_db").sheet1
    except Exception as e:
        print(f"❌ Erro ao conectar no Banco de Dados: {e}")
        return None

# --- 3. LÓGICA DE NEGÓCIO (API PURA) ---

def chamar_gemini_api(prompt):
    """Faz uma chamada POST direta para a API do Google (bypass SDK)."""
    if not GEMINI_KEY:
        print("❌ Sem chave de API.")
        return None

    # Endpoint oficial da API v1beta
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            dados = response.json()
            # Extrai o texto da resposta JSON complexa do Google
            try:
                texto = dados['candidates'][0]['content']['parts'][0]['text']
                return texto
            exceptKeyError:
                return f"<p>Erro ao ler resposta da IA.</p>"
        else:
            print(f"⚠️ Erro HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Erro de conexão: {e}")
        return None

def buscar_e_resumir(tema):
    print(f"      ...Lendo notícias de {tema}...")
    url = RSS_FEEDS.get(tema)
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return "<p>Nenhuma notícia relevante encontrada hoje.</p>"
        
        top_noticias = feed.entries[:5]
        texto_cru = "\n".join([f"- {entry.title}: {entry.link}" for entry in top_noticias])

        prompt = f"""
        Atue como um editor de newsletter.
        Tema: {tema}
        Notícias:
        {texto_cru}

        Instruções:
        1. Resuma em 2 parágrafos curtos.
        2. Use <b>negrito</b> para destaques.
        3. Adicione 1 emoji no início.
        4. No final, crie uma lista <ul> com os links.
        5. Retorne APENAS o HTML.
        """

        # Chamada direta
        resumo = chamar_gemini_api(prompt)
        
        if resumo:
            return resumo
        else:
            # Fallback se a API falhar
            lista_links = "".join([f"<li><a href='{n.link}'>{n.title}</a></li>" for n in top_noticias])
            return f"<p>IA indisponível. Manchetes:</p><ul>{lista_links}</ul>"

    except Exception as e:
        print(f"⚠️ Erro geral em {tema}: {e}")
        return "<p>Erro ao processar feed.</p>"

def gerar_template_email(nome, conteudos_html):
    blocos = ""
    for tema, html_tema in conteudos_html.items():
        cor = "#007bff"
        if tema == "Mercado": cor = "#28a745"
        if tema == "Fofoca": cor = "#e83e8c"
        
        blocos += f"""
        <div style="margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <div style="background:{cor}; color:white; padding:10px;"><b>{tema}</b></div>
            <div style="padding:15px; background:#fff;">{html_tema}</div>
        </div>
        """

    return f"""
    <html><body style="font-family:sans-serif; background:#f4f4f9; padding:20px;">
    <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px;">
        <h2>☕ Briefing Matinal</h2>
        <p>Bom dia, <b>{nome}</b>!</p>
        {blocos}
    </div></body></html>
    """

def enviar_email(destinatario, nome, html_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Briefing IA <{EMAIL_SENDER}>"
        msg['To'] = destinatario
        msg['Subject'] = f"☕ Resumo: {datetime.now().strftime('%d/%m')}"
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Erro SMTP: {e}")
        return False

# --- 4. EXECUTOR PRINCIPAL ---

def main():
    print("🚀 Iniciando Motor (Modo API Pura)...")
    
    sheet = conectar_banco()
    if not sheet: return

    usuarios = sheet.get_all_records()
    print(f"📋 {len(usuarios)} usuários.")
    
    cache_resumos = {}

    for usuario in usuarios:
        nome = usuario.get('Nome')
        email = usuario.get('Email')
        
        if not nome or not email: continue
        print(f"🔄 {nome}...")
        
        conteudos = {}
        for tema in ["Mercado", "Tech", "Motos", "Fofoca"]:
            if usuario.get(tema, '').lower() == "sim":
                if tema not in cache_resumos:
                    print(f"   🤖 Gerando: {tema}")
                    cache_resumos[tema] = buscar_e_resumir(tema)
                    time.sleep(1)
                conteudos[tema] = cache_resumos[tema]

        if conteudos:
            enviar_email(email, nome, gerar_template_email(nome, conteudos))
            print("   ✅ Enviado.")

if __name__ == "__main__":
    main()
