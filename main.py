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
    """
    Painel financeiro blindado.
    Tenta pegar Moedas e Bolsa separadamente para garantir que nada falte.
    """
    html_items = []
    
    # 1. TENTATIVA: DÓLAR E BITCOIN (AwesomeAPI)
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL", timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            
            # Dólar
            dolar = float(dados['USDBRL']['bid'])
            var_dolar = float(dados['USDBRL']['pctChange'])
            cor_dolar = "green" if var_dolar <= 0 else "red" # Dólar caindo é bom (geralmente), ou ajuste conforme preferência
            seta_dolar = "▼" if var_dolar <= 0 else "▲"
            html_items.append(f"🇺🇸 <b>USD:</b> {dolar:.2f} <span style='color:{cor_dolar}; font-size:11px;'>{seta_dolar} {var_dolar}%</span>")
            
            # Bitcoin
            btc = float(dados['BTCBRL']['bid'])
            var_btc = float(dados['BTCBRL']['pctChange'])
            cor_btc = "green" if var_btc >= 0 else "red"
            seta_btc = "▲" if var_btc >= 0 else "▼"
            html_items.append(f"₿ <b>BTC:</b> {btc/1000:.1f}k <span style='color:{cor_btc}; font-size:11px;'>{seta_btc} {var_btc}%</span>")
    except Exception as e:
        print(f"⚠️ Erro ao pegar Moedas: {e}")

    # 2. TENTATIVA: IBOVESPA (YFinance)
    try:
        ibov = yf.Ticker("^BVSP")
        hist = ibov.history(period="2d")
        if len(hist) >= 2:
            fechamento_atual = hist['Close'].iloc[-1]
            fechamento_anterior = hist['Close'].iloc[-2]
            var_ibov = ((fechamento_atual - fechamento_anterior) / fechamento_anterior) * 100
            
            cor_ibov = "green" if var_ibov >= 0 else "red"
            seta_ibov = "▲" if var_ibov >= 0 else "▼"
            html_items.append(f"🇧🇷 <b>IBOV:</b> {int(fechamento_atual)} <span style='color:{cor_ibov}; font-size:11px;'>{seta_ibov} {var_ibov:.2f}%</span>")
    except Exception as e:
        print(f"⚠️ Erro ao pegar Ibovespa: {e}")

    # Monta o HTML final com o que conseguiu capturar
    if not html_items:
        return "" # Se tudo falhar, não exibe nada (melhor que erro)

    conteudo_painel = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(html_items)
    
    return f"""
    <div style="background:#f4f4f4; border-bottom:2px solid #ddd; padding:12px; text-align:center; font-family:monospace; font-size:13px; color:#333;">
        {conteudo_painel}
    </div>
    """

# --- 3. EXTRATOR DE IMAGENS (COM VALIDAÇÃO) ---

def extrair_imagem_rss(entry, tema):
    """
    Busca imagens e VALIDA se são arquivos reais (.jpg, .png, etc).
    Se não achar ou for inválida, retorna o Placeholder colorido.
    """
    image_url = None
    
    # Lista de extensões válidas para evitar pixels de rastreamento
    extensoes_validas = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    
    # 1. Tenta 'media_content' (G1, etc.)
    if 'media_content' in entry:
        for media in entry.media_content:
            url = media.get('url', '')
            if url and any(ext in url.lower() for ext in extensoes_validas):
                image_url = url
                break
        
    # 2. Tenta 'links' (enclosures)
    if not image_url and 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/') and any(ext in link.get('href', '').lower() for ext in extensoes_validas):
                image_url = link.get('href')
                break
                
    # 3. Varredura no HTML (Regex)
    if not image_url:
        conteudo_total = ""
        if 'content' in entry:
            for c in entry.content: conteudo_total += c.value
        if 'summary' in entry: conteudo_total += entry.summary
        
        # Procura qualquer tag <img src="...">
        urls_encontradas = re.findall(r'<img[^>]+src="([^">]+)"', conteudo_total)
        for url in urls_encontradas:
            # Filtra lixo comum
            if "doubleclick" not in url and "pixel" not in url and "facebook" not in url:
                image_url = url
                break

    # 4. Fallback OBRIGATÓRIO (Placeholder Colorido)
    if not image_url:
        cor_fundo = "333333"
        if tema == "Mercado": cor_fundo = "27ae60"
        if tema == "Tech": cor_fundo = "2980b9"
        if tema == "Motos": cor_fundo = "e67e22"
        if tema == "Fofoca": cor_fundo = "8e44ad"
        if tema == "Politica": cor_fundo = "c0392b"
        if tema == "Esportes": cor_fundo = "f1c40f"
        if tema == "Ciencia": cor_fundo = "16a085"
        
        # Gera imagem com texto (Placeholder)
        image_url = f"https://placehold.co/600x200/{cor_fundo}/FFF?text={tema}&font=roboto"
        
    return image_url

# --- 4. INTELIGÊNCIA ARTIFICIAL ---

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
        
        entries = feed.entries[:4]
        
        input_text = ""
        for i, entry in enumerate(entries):
            input_text += f"Notícia {i+1}: {entry.title}\nLink: {entry.link}\n\n"

        prompt = f"""
        Atue como Editor Sênior do All News Journal.
        Analise estas {len(entries)} manchetes sobre {tema}.
        
        Escreva resumos informativos.
        Regras:
        1. Para CADA notícia, escreva entre 50 a 70 palavras.
        2. Use 2 frases: Fato Principal + Contexto/Impacto.
        3. Separe cada resumo EXATAMENTE com "|||".
        4. Sem introduções.
        
        Input:
        {input_text}
        """
        
        resposta_ia = chamar_gemini_api(prompt)
        
        if not resposta_ia: return None
        
        resumos = [r.strip() for r in resposta_ia.split('|||') if r.strip()]
        
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

# --- 5. TEMPLATE ---

def gerar_html_final(nome, dados_usuario, painel_mercado):
    html = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#f0f2f5; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff;">
            
            <div style="background:#111; color:#fff; padding:25px; text-align:center;">
                <h1 style="margin:0; font-family:'Times New Roman', serif; letter-spacing:1px; font-size:28px;">ALL NEWS JOURNAL</h1>
                <p style="margin:5px 0 0; font-size:11px; color:#888; text-transform:uppercase;">Briefing Diário • {datetime.now().strftime('%d/%m')}</p>
            </div>
            
            {painel_mercado}
            
            <div style="padding:20px;">
                <p style="color:#555; font-size:14px; text-align:center; margin-bottom:30px;">
                    Bom dia, <b>{nome}</b>. Destaques da edição de hoje:
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
        if tema == "Ciencia": cor_tema = "#16a085"
        if tema == "Mundo": cor_tema = "#34495e"

        html += f"""
        <div style="margin-top:40px; margin-bottom:20px; border-bottom:2px solid {cor_tema}; padding-bottom:5px;">
            <span style="background:{cor_tema}; color:white; padding:5px 10px; font-size:12px; font-weight:bold; text-transform:uppercase;">{tema}</span>
        </div>
        """

        for noti in noticias:
            html += f"""
            <div style="margin-bottom:30px; background:white; border-bottom:1px solid #eee; padding-bottom:20px;">
                <a href="{noti['link']}" style="text-decoration:none;">
                    <img src="{noti['imagem']}" style="width:100%; height:200px; object-fit:cover; border-radius:6px; display:block; background-color:#eee;" alt="Imagem da notícia">
                </a>
                <div style="padding-top:15px;">
                    <a href="{noti['link']}" style="text-decoration:none; color:#111;">
                        <h3 style="margin:0 0 10px 0; font-size:20px; line-height:1.3; font-weight:700;">{noti['titulo']}</h3>
                    </a>
                    <p style="margin:0; font-size:15px; color:#444; line-height:1.6; text-align:justify;">
                        {noti['resumo']}
                    </p>
                    <div style="margin-top:12px;">
                        <a href="{noti['link']}" style="font-size:13px; color:{cor_tema}; font-weight:bold; text-decoration:none; border-bottom:1px solid {cor_tema};">LER MATÉRIA COMPLETA →</a>
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
    print("🚀 Iniciando Motor (v5.2 - Blindado)...")
    
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
