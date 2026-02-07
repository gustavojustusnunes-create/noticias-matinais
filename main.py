import os
import smtplib
import feedparser
import requests
import yfinance as yf  # Nova lib para mercado financeiro
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

# NOVAS FONTES E TEMAS
RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/",
    "Politica": "https://g1.globo.com/rss/g1/politica/",      # Novo
    "Esportes": "https://ge.globo.com/rss/ge/",                # Novo
    "Ciencia": "https://gizmodo.uol.com.br/category/ciencia/feed/", # Novo
    "Mundo": "https://g1.globo.com/rss/g1/mundo/"              # Novo
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

# --- 3. MÓDULO FINANCEIRO (NOVO) ---

def obter_indicadores():
    """Busca Dólar, Bitcoin e Ibovespa em tempo real."""
    print("      💰 Coletando dados de mercado...")
    html_painel = ""
    
    try:
        # 1. Moedas via API Awesome (Mais rápido que yfinance para câmbio)
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL")
        if resp.status_code == 200:
            dados = resp.json()
            dolar = float(dados['USDBRL']['bid'])
            btc = float(dados['BTCBRL']['bid'])
            
            # Formatação visual
            var_dolar = float(dados['USDBRL']['pctChange'])
            cor_dolar = "green" if var_dolar >= 0 else "red"
            seta_dolar = "▲" if var_dolar >= 0 else "▼"

            html_painel += f"""
            <span style="margin-right: 15px;">🇺🇸 <b>USD:</b> R$ {dolar:.2f} <span style="color:{cor_dolar}; font-size:12px;">{seta_dolar} {var_dolar}%</span></span>
            <span style="margin-right: 15px;">₿ <b>BTC:</b> R$ {btc:,.0f}</span>
            """

        # 2. Ibovespa via YFinance
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="2d")
        if len(hist) >= 2:
            fechamento_ontem = hist['Close'].iloc[-2]
            preco_agora = hist['Close'].iloc[-1]
            var_ibov = ((preco_agora - fechamento_ontem) / fechamento_ontem) * 100
            cor_ibov = "green" if var_ibov >= 0 else "red"
            seta_ibov = "▲" if var_ibov >= 0 else "▼"
            
            html_painel += f"""
            <span>🇧🇷 <b>IBOV:</b> {int(preco_agora)} pts <span style="color:{cor_ibov}; font-size:12px;">{seta_ibov} {var_ibov:.2f}%</span></span>
            """
            
        return f"""
        <div style="background-color: #f8f9fa; border-bottom: 3px solid #000; padding: 15px; text-align: center; font-family: monospace; font-size: 14px; margin-bottom: 25px;">
            {html_painel}
        </div>
        """
    except Exception as e:
        print(f"⚠️ Erro no painel financeiro: {e}")
        return ""

# --- 4. INTELIGÊNCIA ARTIFICIAL (TEXTOS MELHORES) ---

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None
    # Usando o modelo mais inteligente (2.5) e o 2.0 como backup
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        for tentativa in range(1, 4):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    try:
                        return response.json()['candidates'][0]['content']['parts'][0]['text']
                    except: return None
                elif response.status_code == 429:
                    time.sleep(20 * tentativa)
                    continue
                else:
                    break
            except: break
    return None

def buscar_e_resumir(tema):
    print(f"      ...Processando {tema}...")
    url = RSS_FEEDS.get(tema)
    if not url: return None
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries: return None
        
        top = feed.entries[:6] # Lendo mais notícias para dar contexto
        texto = "\n".join([f"- {e.title}: {e.link}" for e in top])
        
        # PROMPT DE JORNALISTA SÊNIOR
        prompt = f"""
        Você é o Editor-Chefe do 'All News Journal'.
        Escreva uma coluna analítica sobre as notícias abaixo de {tema}.
        
        Estrutura Obrigatória (Use HTML):
        1. Comece com um emoji e uma Manchete de Impacto (em <h3>).
        2. Escreva 3 parágrafos bem desenvolvidos:
           - Parágrafo 1: O Fato Principal (O que aconteceu?).
           - Parágrafo 2: Contexto (Por que isso importa? Bastidores).
           - Parágrafo 3: Impacto Futuro (O que esperar?).
        3. Use <b>negrito</b> para destacar nomes e números importantes.
        4. Finalize com "Fontes:" e uma lista <ul> com os links.
        
        Notícias base:
        {texto}
        """
        
        resumo = chamar_gemini_api(prompt)
        if resumo: return resumo
        else: return f"<p>Erro na IA.</p>"

    except Exception: return "<p>Erro no feed.</p>"

# --- 5. TEMPLATE E ENVIO (BRANDING NOVO) ---

def gerar_template_email(nome, conteudos, painel_mercado):
    html = f"""
    <html><body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding:0; margin:0; background:#eeeeee;">
    <div style="max-width:650px; margin:20px auto; background:white; border-radius:8px; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        
        <div style="background-color: #1a1a1a; color: white; padding: 30px 20px; text-align: center;">
            <h1 style="margin:0; font-family: 'Times New Roman', serif; font-size: 32px; letter-spacing: 1px;">ALL NEWS JOURNAL</h1>
            <p style="margin:10px 0 0; color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Edição Diária • {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>

        {painel_mercado}

        <div style="padding: 20px 40px;">
            <p style="font-size: 16px; color: #555;">Olá, <b>{nome}</b>. Aqui está sua curadoria de hoje:</p>
            <hr style="border:0; border-top:1px solid #eee; margin: 20px 0;">
    """
    
    for tema, texto in conteudos.items():
        # Cores temáticas
        cores = {
            "Mercado": "#27ae60", "Tech": "#2980b9", "Motos": "#e67e22", 
            "Fofoca": "#8e44ad", "Politica": "#c0392b", "Esportes": "#f1c40f",
            "Ciencia": "#16a085", "Mundo": "#34495e"
        }
        cor = cores.get(tema, "#333")
        
        html += f"""
        <div style="margin-bottom: 40px;">
            <div style="border-left: 5px solid {cor}; padding-left: 15px; margin-bottom: 15px;">
                <span style="color: {cor}; font-weight: bold; text-transform: uppercase; font-size: 12px; letter-spacing: 1px;">{tema}</span>
            </div>
            <div style="color: #333; line-height: 1.6; font-size: 15px;">
                {texto}
            </div>
        </div>
        """
    
    html += """
        </div>
        <div style="background-color: #f4f4f4; padding: 20px; text-align: center; color: #999; font-size: 11px;">
            &copy; 2025 All News Journal Group. Gerado por IA.
        </div>
    </div></body></html>
    """
    return html

def enviar_email(destinatario, html):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"📰 All News Journal - {datetime.now().strftime('%d/%m')}"
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
    print("🚀 Iniciando All News Journal (v4.0)...")
    
    sheet = conectar_banco()
    if not sheet: return

    usuarios = sheet.get_all_records()
    print(f"📋 {len(usuarios)} assinantes.")
    
    # Cache global (notícias + mercado)
    painel_financeiro = obter_indicadores()
    cache_temas = {}

    todas_chaves = RSS_FEEDS.keys()

    for usr in usuarios:
        nome, email = usr.get('Nome'), usr.get('Email')
        if not nome or not email: continue
        
        print(f"🔄 Gerando edição para: {nome}...")
        conteudos_usr = {}
        
        for tema in todas_chaves:
            # Verifica se a coluna existe e se está marcada com Sim
            pref = usr.get(tema, '')
            if isinstance(pref, str) and pref.strip().lower() == "sim":
                if tema not in cache_temas:
                    cache_temas[tema] = buscar_e_resumir(tema)
                    print("      💤 Pausa estratégica (12s)...")
                    time.sleep(12)
                conteudos_usr[tema] = cache_temas[tema]

        if conteudos_usr:
            html_final = gerar_template_email(nome, conteudos_usr, painel_financeiro)
            if enviar_email(email, html_final):
                print("   ✅ Jornal despachado.")

if __name__ == "__main__":
    main()
