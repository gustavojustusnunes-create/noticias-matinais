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
    """Painel financeiro blindado (Moedas + Bolsa)."""
    html_items = []
    
    # 1. MOEDAS (AwesomeAPI)
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL", timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            
            # Dólar
            dolar = float(dados['USDBRL']['bid'])
            var_dolar = float(dados['USDBRL']['pctChange'])
            cor_dolar = "green" if var_dolar <= 0 else "red"
            seta_dolar = "▼" if var_dolar <= 0 else "▲"
            html_items.append(f"🇺🇸 <b>USD:</b> {dolar:.2f} <span style='color:{cor_dolar}; font-size:11px;'>{seta_dolar} {var_dolar}%</span>")
            
            # Bitcoin
            btc = float(dados['BTCBRL']['bid'])
            var_btc = float(dados['BTCBRL']['pctChange'])
            cor_btc = "green" if var_btc >= 0 else "red"
            seta_btc = "▲" if var_btc >= 0 else "▼"
            html_items.append(f"₿ <b>BTC:</b> {btc/1000:.1f}k <span style='color:{cor_btc}; font-size:11px;'>{seta_btc} {var_btc}%</span>")
    except Exception as e:
        print(f"⚠️ Erro Moedas: {e}")

    # 2. IBOVESPA (YFinance)
    try:
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="2d")
        if len(hist) >= 2:
            atual = hist['Close'].iloc[-1]
            anterior = hist['Close'].iloc[-2]
            var_ibov = ((atual - anterior) / anterior) * 100
            cor_ibov = "green" if var_ibov >= 0 else "red"
            seta_ibov = "▲" if var_ibov >= 0 else "▼"
            html_items.append(f"🇧🇷 <b>IBOV:</b> {int(atual)} <span style='color:{cor_ibov}; font-size:11px;'>{seta_ibov} {var_ibov:.2f}%</span>")
    except Exception as e:
        print(f"⚠️ Erro Ibovespa: {e}")

    if not html_items: return ""
    return f"""<div style="background:#f4f4f4; border-bottom:2px solid #ddd; padding:12px; text-align:center; font-family:monospace; font-size:13px; color:#333;">{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(html_items)}</div>"""

# --- 3. EXTRATOR DE IMAGENS (V5.3 - REGEX NINJA) ---

def extrair_imagem_rss(entry, tema):
    image_url = None
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    
    # 1. Media Content (Padrão Ouro)
    if 'media_content' in entry:
        for m in entry.media_content:
            if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                image_url = m['url']; break
        
    # 2. Enclosures/Links
    if not image_url and 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/') and any(ext in link.get('href', '').lower() for ext in extensoes):
                image_url = link.get('href'); break
                
    # 3. Varredura HTML (AQUI A MELHORIA: Aceita aspas simples e duplas)
    if not image_url:
        texto = ""
        if 'content' in entry:
            for c in entry.content: texto += c.value
        if 'summary' in entry: texto += entry.summary
        
        # Regex flexível: procura src="link" OU src='link'
        matches = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', texto)
        for url in matches:
            if any(ext in url.lower() for ext in extensoes) and "pixel" not in url and "doubleclick" not in url:
                image_url = url
                break

    # 4. Fallback (Placeholder Temático)
    if not image_url:
        cores = {
            "Mercado": "27ae60", "Tech": "2980b9", "Motos": "e67e22",
            "Fofoca": "8e44ad", "Politica": "c0392b", "Esportes": "f1c40f",
            "Ciencia": "16a085", "Mundo": "34495e"
        }
        cor = cores.get(tema, "333333")
        image_url = f"https://placehold.co/600x200/{cor}/FFF?text={tema}&font=roboto"
        
    return image_url

# --- 4. INTELIGÊNCIA ARTIFICIAL ---

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        for i in range(1, 4):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()['candidates'][0]['content']['parts'][0]['text']
                elif resp.status_code == 429:
                    time.sleep(20 * i); continue
                else: break
            except: break
    return None

def processar_tema(tema):
    print(f"      ...Lendo feed de {tema}...")
    url = RSS_FEEDS.get(tema)
    if not url: return None
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries: return None
        entries = feed.entries[:4]
        
        input_txt = ""
        for i, e in enumerate(entries):
            input_txt += f"Notícia {i+1}: {e.title}\nLink: {e.link}\n\n"

        prompt = f"""
        Atue como Editor Sênior. Analise estas manchetes de {tema}.
        Para CADA notícia, escreva um resumo de 50-70 palavras.
        Estrutura: Fato Principal + Contexto/Impacto.
        Separe EXATAMENTE com "|||".
        Sem introduções.
        Input: {input_txt}
        """
        
        resp_ia = chamar_gemini_api(prompt)
        if not resp_ia: return None
        
        resumos = [r.strip() for r in resp_ia.split('|||') if r.strip()]
        
        noticias = []
        for i, entry in enumerate(entries):
            resumo = resumos[i] if i < len(resumos) else "Leia mais no link."
            img = extrair_imagem_rss(entry, tema)
            noticias.append({"titulo": entry.title, "link": entry.link, "imagem": img, "resumo": resumo})
            
        return noticias
    except Exception as e:
        print(f"Erro {tema}: {e}")
        return None

# --- 5. TEMPLATE ---

def gerar_html_final(nome, dados, painel):
    html = f"""
    <html><body style="margin:0; padding:0; background:#f0f2f5; font-family:Helvetica, Arial;">
        <div style="max-width:600px; margin:0 auto; background:#fff;">
            <div style="background:#111; color:#fff; padding:25px; text-align:center;">
                <h1 style="margin:0; font-family:'Times New Roman'; font-size:28px;">ALL NEWS JOURNAL</h1>
                <p style="margin:5px 0 0; font-size:11px; color:#888; text-transform:uppercase;">Briefing • {datetime.now().strftime('%d/%m')}</p>
            </div>
            {painel}
            <div style="padding:20px;">
                <p style="color:#555; font-size:14px; text-align:center; margin-bottom:30px;">Bom dia, <b>{nome}</b>.</p>
    """
    
    for tema, items in dados.items():
        cor = "333"
        if tema == "Mercado": cor = "27ae60"
        elif tema == "Tech": cor = "2980b9"
        elif tema == "Motos": cor = "e67e22"
        elif tema == "Fofoca": cor = "8e44ad"
        elif tema == "Politica": cor = "c0392b"
        elif tema == "Esportes": cor = "f1c40f"
        elif tema == "Ciencia": cor = "16a085"
        elif tema == "Mundo": cor = "34495e"
        
        html += f"""<div style="margin:40px 0 20px; border-bottom:2px solid #{cor};"><span style="background:#{cor}; color:#fff; padding:5px 10px; font-size:12px; font-weight:bold;">{tema.upper()}</span></div>"""
        
        for n in items:
            html += f"""
            <div style="margin-bottom:30px; border-bottom:1px solid #eee; padding-bottom:20px;">
                <a href="{n['link']}"><img src="{n['imagem']}" style="width:100%; height:200px; object-fit:cover; border-radius:6px; background:#eee;"></a>
                <div style="padding-top:15px;">
                    <a href="{n['link']}" style="text-decoration:none; color:#111;"><h3 style="margin:0 0 10px; font-size:18px;">{n['titulo']}</h3></a>
                    <p style="margin:0; font-size:14px; color:#444; line-height:1.5;">{n['resumo']}</p>
                    <div style="margin-top:10px;"><a href="{n['link']}" style="font-size:12px; color:#{cor}; font-weight:bold; text-decoration:none;">LER MAIS →</a></div>
                </div>
            </div>"""

    html += """<div style="text-align:center; padding:30px; background:#fafafa; color:#aaa; font-size:11px;">&copy; 2025 All News Journal.</div></div></body></html>"""
    return html

def enviar_email(dest, html):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"📰 All News Journal - {datetime.now().strftime('%d/%m')}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = dest
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, dest, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Erro SMTP: {e}")
        return False

# --- MAIN ---
def main():
    print("🚀 Iniciando Motor (v5.3 - Regex Ninja)...")
    sheet = conectar_banco()
    if not sheet: return
    usuarios = sheet.get_all_records()
    painel = obter_indicadores()
    cache = {}
    for usr in usuarios:
        if not usr.get('Nome') or not usr.get('Email'): continue
        print(f"🔄 Gerando para: {usr.get('Nome')}...")
        conteudo = {}
        for tema in RSS_FEEDS.keys():
            if usr.get(tema, '').strip().lower() == "sim":
                if tema not in cache:
                    cache[tema] = processar_tema(tema)
                    time.sleep(10)
                conteudo[tema] = cache[tema]
        if conteudo:
            if enviar_email(usr.get('Email'), gerar_html_final(usr.get('Nome'), conteudo, painel)):
                print("   ✅ Enviado.")

if __name__ == "__main__":
    main()
