import os
import smtplib
import feedparser
import requests
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time
import re

# --- 1. CONFIGURAÇÕES ---
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()
GCP_JSON = os.environ.get("GCP_JSON")
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/",
    "Politica": "https://g1.globo.com/rss/g1/politica/",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Ciencia": "https://gizmodo.uol.com.br/category/ciencia/feed/",
    "Mundo": "https://g1.globo.com/rss/g1/mundo/"
}

# --- 2. INFRAESTRUTURA ---
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

def obter_indicadores():
    html_items = []
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL", timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            dolar = float(dados['USDBRL']['bid'])
            var_dolar = float(dados['USDBRL']['pctChange'])
            cor_dolar = "green" if var_dolar <= 0 else "red"
            seta_dolar = "▼" if var_dolar <= 0 else "▲"
            html_items.append(f"🇺🇸 <b>USD:</b> {dolar:.2f} <span style='color:{cor_dolar}; font-size:11px;'>{seta_dolar} {var_dolar}%</span>")
            
            btc = float(dados['BTCBRL']['bid'])
            var_btc = float(dados['BTCBRL']['pctChange'])
            cor_btc = "green" if var_btc >= 0 else "red"
            seta_btc = "▲" if var_btc >= 0 else "▼"
            html_items.append(f"₿ <b>BTC:</b> {btc/1000:.1f}k <span style='color:{cor_btc}; font-size:11px;'>{seta_btc} {var_btc}%</span>")
    except: pass

    try:
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="2d")
        if len(hist) >= 2:
            atual = hist['Close'].iloc[-1]
            ant = hist['Close'].iloc[-2]
            var = ((atual - ant) / ant) * 100
            cor = "green" if var >= 0 else "red"
            seta = "▲" if var >= 0 else "▼"
            html_items.append(f"🇧🇷 <b>IBOV:</b> {int(atual)} <span style='color:{cor}; font-size:11px;'>{seta} {var:.2f}%</span>")
    except: pass

    if not html_items: return ""
    return f"""<div style="background-color:#e5e3de; padding:12px; text-align:center; font-family:monospace; font-size:13px; color:#111;">{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(html_items)}</div>"""

# --- 3. EXTRATOR IMAGEM PREMIUM ---
def extrair_imagem_rss(entry, tema):
    image_url = None
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    
    # 1. Tenta Media Content
    if 'media_content' in entry:
        for m in entry.media_content:
            if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                image_url = m['url']; break
    
    # 2. Tenta Links
    if not image_url and 'links' in entry:
        for l in entry.links:
            if l.get('type','').startswith('image/') and any(ext in l.get('href','').lower() for ext in extensoes):
                image_url = l['href']; break
    
    # 3. Regex Ninja no HTML
    if not image_url:
        txt = ""
        if 'content' in entry:
            for c in entry.content: txt += c.value
        if 'summary' in entry: txt += entry.summary
        matches = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', txt)
        for url in matches:
            if any(ext in url.lower() for ext in extensoes) and "pixel" not in url and "doubleclick" not in url:
                image_url = url; break

    # 4. Fallback: Banco de Imagens Unsplash (Substituindo os quadrados antigos)
    if not image_url:
        FALLBACK_IMAGES = {
            "Mercado": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
            "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=300&fit=crop",
            "Motos": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=600&h=300&fit=crop",
            "Fofoca": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=300&fit=crop",
            "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
            "Esportes": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
            "Ciencia": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=300&fit=crop",
            "Mundo": "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=300&fit=crop"
        }
        image_url = FALLBACK_IMAGES.get(tema, "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop")
    
    return image_url

# --- 4. IA (GEMINI) E FILTRO DE NOTÍCIAS ---
def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        for i in range(1, 4):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    return r.json()['candidates'][0]['content']['parts'][0]['text']
                elif r.status_code == 429:
                    time.sleep(20 * i); continue
                else: break
            except: break
    return None

def processar_tema(tema):
    print(f"      ...Gerando Cache de {tema}...")
    url = RSS_FEEDS.get(tema)
    if not url: return None
    try:
        feed = feedparser.parse(url)
        if not feed.entries: return None
        
        # FILTRO INTELIGENTE: Pega apenas notícias válidas
        valid_entries = []
        for e in feed.entries:
            link = e.get('link', '').lower()
            titulo = e.get('title', '').lower()
            
            # Se for Tech, bloqueia qualquer coisa relacionada a apostas de futebol
            if tema == "Tech":
                if "aposta" in link or "palpite" in titulo or "futebol" in titulo:
                    continue # Pula essa notícia e vai pra próxima
            
            valid_entries.append(e)
            if len(valid_entries) >= 4: # Pega as 4 primeiras VÁLIDAS
                break
                
        if not valid_entries: return None
        
        input_txt = ""
        for i, e in enumerate(valid_entries):
            input_txt += f"Notícia {i+1}: {e.title}\nLink: {e.link}\n\n"

        prompt = f"""
        Atue como Editor Sênior. Analise estas manchetes de {tema}.
        Para CADA notícia, escreva um resumo de 50-70 palavras.
        Estrutura: Fato Principal + Contexto.
        Separe com "|||". Sem introduções.
        Input: {input_txt}
        """
        resp = chamar_gemini_api(prompt)
        if not resp: return None
        resumos = [r.strip() for r in resp.split('|||') if r.strip()]
        
        noticias = []
        for i, entry in enumerate(valid_entries):
            resumo = resumos[i] if i < len(resumos) else "Acesse o link abaixo para ler a matéria completa."
            img = extrair_imagem_rss(entry, tema)
            noticias.append({"titulo": entry.title, "link": entry.link, "imagem": img, "resumo": resumo})
        return noticias
    except Exception as e:
        print(f"Erro {tema}: {e}")
        return None

# --- 5. TEMPLATE DO E-MAIL (NOVO VISUAL TURQUESA E CREME) ---
def gerar_html_final(nome, dados, painel):
    cor_turquesa = "0a5c5a"
    cor_creme = "fdfbf7"
    cor_fundo_escuro = "084c4a"
    
    html = f"""
    <html><body style="margin:0; padding:0; background-color:#e5e3de; font-family:'Lora', 'Times New Roman', serif;">
        <div style="max-width:600px; margin:20px auto; background-color:#{cor_creme}; border-radius:8px; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            
            <div style="background-color:transparent; color:#{cor_turquesa}; padding:30px 20px 20px; text-align:center; border-bottom:2px solid #{cor_turquesa};">
                <h1 style="margin:0; font-family:'Playfair Display', Georgia, serif; font-size:32px; text-transform:uppercase; letter-spacing: 2px;">ALL NEWS JOURNAL</h1>
                <p style="margin:10px 0 0; font-size:12px; color:#777; font-style:italic;">Edição Premium • {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>
            
            {painel}
            
            <div style="padding:30px 25px;">
                <p style="color:#2c2c2c; font-size:16px; text-align:center; margin-bottom:40px; font-style:italic;">Bom dia, <b>{nome}</b>. Aqui está a sua curadoria de hoje.</p>
    """
    
    for tema, items in dados.items():
        if not items: continue
        
        # Etiqueta Turquesa
        html += f"""
        <div style="margin:40px 0 25px; border-bottom:2px solid #{cor_turquesa};">
            <span style="background-color:#{cor_turquesa}; color:#ffffff; padding:6px 14px; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; border-radius:4px 4px 0 0; display:inline-block;">{tema}</span>
        </div>"""
        
        for n in items:
            html += f"""
            <div style="margin-bottom:35px; border-bottom:1px solid #e5e3de; padding-bottom:25px;">
                <a href="{n['link']}">
                    <img src="{n['imagem']}" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border-bottom:4px solid #{cor_turquesa}; display:block;">
                </a>
                <div style="padding-top:15px;">
                    <a href="{n['link']}" style="text-decoration:none; color:#111111;">
                        <h3 style="margin:0 0 12px; font-size:22px; font-family:'Playfair Display', Georgia, serif; line-height:1.3;">{n['titulo']}</h3>
                    </a>
                    <p style="margin:0; font-size:15px; color:#444444; line-height:1.6;">{n['resumo']}</p>
                    <div style="margin-top:15px;">
                        <a href="{n['link']}" style="font-size:13px; color:#{cor_turquesa}; font-weight:bold; text-decoration:none; text-transform:uppercase; letter-spacing:0.5px;">Ler matéria completa &rarr;</a>
                    </div>
                </div>
            </div>"""
    
    html += f"""
            </div>
            <div style="text-align:center; padding:30px; background-color:#{cor_fundo_escuro}; color:#{cor_creme}; font-size:12px; font-family:'Lora', 'Times New Roman', serif;">
                <p style="margin:0;">&copy; 2026 All News Journal Group. Conteúdo Premium.</p>
                <p style="margin:10px 0 0; font-size:10px; opacity:0.7;">Você está recebendo este e-mail porque se inscreveu no nosso portal.</p>
            </div>
        </div>
    </body></html>"""
    return html

def enviar_email(dest, html):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"📰 All News Journal - {datetime.now().strftime('%d/%m')}"
        msg['From'] = EMAIL_SENDER
        msg['To']
