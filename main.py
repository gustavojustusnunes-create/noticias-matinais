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
    """Painel financeiro compacto."""
    html_painel = ""
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL")
        if resp.status_code == 200:
            dados = resp.json()
            dolar = float(dados['USDBRL']['bid'])
            var_dolar = float(dados['USDBRL']['pctChange'])
            cor_dolar = "green" if var_dolar >= 0 else "red"
            
            html_painel += f"""
            <span style="margin: 0 10px;">🇺🇸 <b>USD:</b> {dolar:.2f} <span style="color:{cor_dolar}; font-size:11px;">{var_dolar}%</span></span>
            """
            
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="2d")
        if len(hist) >= 2:
            fechamento = hist['Close'].iloc[-1]
            var_ibov = ((fechamento - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            cor_ibov = "green" if var_ibov >= 0 else "red"
            html_painel += f"""
            <span style="margin: 0 10px;">🇧🇷 <b>IBOV:</b> {int(fechamento)} <span style="color:{cor_ibov}; font-size:11px;">{var_ibov:.2f}%</span></span>
            """
            
        return f"""
        <div style="background:#f4f4f4; border-bottom:2px solid #ddd; padding:10px; text-align:center; font-family:monospace; font-size:13px; color:#333;">
            {html_painel}
        </div>
        """
    except: return ""

# --- 3. EXTRATOR DE IMAGENS (A NOVA MÁGICA) ---

def extrair_imagem_rss(entry, tema):
    """Tenta achar imagem no RSS. Se não achar, cria um Placeholder."""
    image_url = None
    
    # 1. Tenta 'media_content' (Padrão RSS moderno)
    if 'media_content' in entry:
        media = entry.media_content[0]
        if 'url' in media: image_url = media['url']
        
    # 2. Tenta 'links' (enclosures)
    if not image_url and 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                image_url = link.get('href')
                break
                
    # 3. Tenta achar tag <img src="..."> dentro da descrição HTML
    if not image_url and 'summary' in entry:
        img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if img_match: image_url = img_match.group(1)

    # 4. Fallback: Se não achou nada, usa imagem gerada com o nome do TEMA
    if not image_url:
        # Usa placehold.co para gerar uma imagem elegante com o nome do tema
        cor_fundo = "333333"
        if tema == "Mercado": cor_fundo = "27ae60"
        if tema == "Tech": cor_fundo = "2980b9"
        if tema == "Fofoca": cor_fundo = "8e44ad"
        image_url = f"https://placehold.co/600x200/{cor_fundo}/FFF?text={tema}&font=roboto"
        
    return image_url

# --- 4. INTELIGÊNCIA ARTIFICIAL (DIVISÃO POR BLOCOS) ---

def chamar_gemini_api(prompt):
    if not GEMINI_KEY: return None
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        for tentativa in range(1, 4):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 429:
                    time.sleep(20 * tentativa)
                    continue
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
        
        # Pega as top 4 notícias
        entries = feed.entries[:4]
        
        # Prepara dados para a IA
        input_text = ""
        for i, entry in enumerate(entries):
            input_text += f"Notícia {i+1}: {entry.title}\nLink: {entry.link}\n\n"

        # Prompt focado em SPLIT (Separação)
        prompt = f"""
        Atue como Editor Sênior do All News Journal.
        Você recebeu {len(entries)} manchetes sobre {tema}.
        
        Sua missão: Escrever um resumo curto e impactante para CADA notícia separadamente.
        
        Regras de Formatação (Rigoroso):
        - Separe cada resumo com a string "|||" (três barras verticais).
        - NÃO coloque títulos, nem links, nem introduções. Apenas o texto do resumo.
        - Cada resumo deve ter no máximo 40 palavras.
        - Use um tom profissional mas envolvente.
        
        Input:
        {input_text}
        """
        
        resposta_ia = chamar_gemini_api(prompt)
        
        if not resposta_ia: return None
        
        # Divide a resposta da IA pelos separadores "|||"
        resumos = [r.strip() for r in resposta_ia.split('|||') if r.strip()]
        
        # Monta a lista final de objetos (Foto + Título + Resumo + Link)
        noticias_finais = []
        for i, entry in enumerate(entries):
            resumo_texto = resumos[i] if i < len(resumos) else "Clique para ler a matéria completa."
            imagem = extrair_imagem_rss(entry, tema)
            
            noticias_finais.append({
                "titulo": entry.title,
                "link": entry.link,
                "imagem": imagem,
                "resumo": resumo_texto
            })
            
        return noticias_finais

    except Exception as e:
        print(f"Erro em {tema}: {e}")
        return None

# --- 5. TEMPLATE (VISUAL DE CARDS) ---

def gerar_html_final(nome, dados_usuario, painel_mercado):
    html = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#f0f2f5; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff;">
            
            <div style="background:#111; color:#fff; padding:25px; text-align:center;">
                <h1 style="margin:0; font-family:'Times New Roman', serif; letter-spacing:1px; font-size:28px;">ALL NEWS JOURNAL</h1>
                <p style="margin:5px 0 0; font-size:11px; color:#888; text-transform:uppercase;">Briefing Visual • {datetime.now().strftime('%d/%m')}</p>
            </div>
            
            {painel_mercado}
            
            <div style="padding:20px;">
                <p style="color:#555; font-size:14px; text-align:center; margin-bottom:30px;">
                    Bom dia, <b>{nome}</b>. Destaques visuais de hoje:
                </p>
    """

    for tema, noticias in dados_usuario.items():
        cor_tema = "#333"
        if tema == "Mercado": cor_tema = "#27ae60"
        if tema == "Tech": cor_tema = "#2980b9"
        if tema == "Motos": cor_tema = "#e67e22"
        if tema == "Fofoca": cor_tema = "#8e44ad"
        if tema == "Politica": cor_tema = "#c0392b"
        if tema == "Esportes": cor_tema = "#f1c40f"

        # Cabeçalho do Tema
        html += f"""
        <div style="margin-top:40px; margin-bottom:20px; border-bottom:2px solid {cor_tema}; padding-bottom:5px;">
            <span style="background:{cor_tema}; color:white; padding:5px 10px; font-size:12px; font-weight:bold; text-transform:uppercase;">{tema}</span>
        </div>
        """

        # Loop das Notícias (Cards)
        for noti in noticias:
            html += f"""
            <div style="margin-bottom:25px; background:white; border-bottom:1px solid #eee; padding-bottom:15px;">
                <a href="{noti['link']}" style="text-decoration:none;">
                    <img src="{noti['imagem']}" style="width:100%; height:180px; object-fit:cover; border-radius:6px; display:block;" alt="Imagem da notícia">
                </a>
                
                <div style="padding-top:12px;">
                    <a href="{noti['link']}" style="text-decoration:none; color:#111;">
                        <h3 style="margin:0 0 8px 0; font-size:18px; line-height:1.3;">{noti['titulo']}</h3>
                    </a>
                    <p style="margin:0; font-size:14px; color:#666; line-height:1.5;">
                        {noti['resumo']}
                    </p>
                    <div style="margin-top:10px;">
                        <a href="{noti['link']}" style="font-size:12px; color:{cor_tema}; font-weight:bold; text-decoration:none;">LER MATÉRIA COMPLETA →</a>
                    </div>
                </div>
            </div>
            """

    html += """
            <div style="text-align:center; padding:30px; background:#fafafa; color:#aaa; font-size:11px;">
                &copy; 2025 All News Journal.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def enviar_email(destinatario, html):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"📸 All News Visual - {datetime.now().strftime('%d/%m')}"
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
    print("🚀 Iniciando Motor Visual (v5.0)...")
    
    sheet = conectar_banco()
    if not sheet: return

    usuarios = sheet.get_all_records()
    painel = obter_indicadores()
    cache = {}
    todas_chaves = RSS_FEEDS.keys()

    for usr in usuarios:
        nome, email = usr.get('Nome'), usr.get('Email')
        if not nome or not email: continue
        
        print(f"🔄 Montando jornal para: {nome}...")
        conteudos = {}
        
        for tema in todas_chaves:
            if usr.get(tema, '').strip().lower() == "sim":
                if tema not in cache:
                    cache[tema] = processar_tema(tema)
                    print("      💤 Pausa (10s)...")
                    time.sleep(10)
                conteudos[tema] = cache[tema]

        if conteudos:
            html = gerar_html_final(nome, conteudos, painel)
            if enviar_email(email, html):
                print("   ✅ Despachado.")

if __name__ == "__main__":
    main()
