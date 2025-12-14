import os
import smtplib
import feedparser
import google.generativeai as genai
import yfinance as yf # Nova biblioteca financeira
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- CONFIGURAÇÕES ---
API_KEY = os.environ["GEMINI_KEY"]
MEU_EMAIL = os.environ["EMAIL_USER"]
MINHA_SENHA_APP = os.environ["EMAIL_PASSWORD"]
DESTINATARIO = MEU_EMAIL 

# Configura a IA
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

fontes = {
    '💰 Mercado & Finanças': ['https://www.infomoney.com.br/feed/', 'https://braziljournal.com/feed/'],
    '📱 Tech & Inovação': ['https://rss.tecmundo.com.br/feed', 'https://olhardigital.com.br/feed/'],
    '✨ Fofoca & Fama': ['https://revistaquem.globo.com/rss/quem/', 'https://www.metropoles.com/colunas/leo-dias/feed'],
    '🌍 Notícias Gerais': ['https://g1.globo.com/rss/g1/']
}

def obter_dados_mercado():
    print("📈 Consultando a Bolsa de Valores...")
    try:
        # Tickers: Dólar, Euro, Petrobras, Bitcoin
        tickers = ['BRL=X', 'EURBRL=X', 'PETR4.SA', 'BTC-USD']
        dados = yf.Tickers(' '.join(tickers))
        
        # Pega o preço atual (ou último fechamento)
        dolar = dados.tickers['BRL=X'].history(period='1d')['Close'].iloc[-1]
        euro = dados.tickers['EURBRL=X'].history(period='1d')['Close'].iloc[-1]
        petro = dados.tickers['PETR4.SA'].history(period='1d')['Close'].iloc[-1]
        btc = dados.tickers['BTC-USD'].history(period='1d')['Close'].iloc[-1]
        
        # Formata o HTML bonitinho
        html_mercado = f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <h3 style="margin-top: 0; color: #2c3e50; text-align: center;">📊 Painel de Mercado</h3>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; text-align: center;">
                <div style="margin: 5px;">🇺🇸 <b>Dólar:</b> R$ {dolar:.2f}</div>
                <div style="margin: 5px;">🇪🇺 <b>Euro:</b> R$ {euro:.2f}</div>
                <div style="margin: 5px;">🛢️ <b>Petrobras:</b> R$ {petro:.2f}</div>
                <div style="margin: 5px;">₿ <b>Bitcoin:</b> US$ {btc:,.0f}</div>
            </div>
        </div>
        """
        return html_mercado
    except Exception as e:
        print(f"Erro no mercado: {e}")
        return ""

def buscar_noticias():
    print("🕵️‍♂️ Buscando notícias...")
    noticias_agrupadas = {}
    for categoria, urls in fontes.items():
        lista = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    lista.append(f"- {entry.title} (Link: {entry.link})")
            except: pass
        noticias_agrupadas[categoria] = lista
    return noticias_agrupadas

def gerar_html_e_enviar(dados, html_mercado):
    # Cabeçalho do HTML
    html = f"""
    <!DOCTYPE html><html><head><style>
    body{{font-family:'Segoe UI', Helvetica, sans-serif; background:#f4f4f4; padding:20px}}
    .box{{max-width:600px; margin:0 auto; background:#fff; padding:30px; border-radius:10px; box-shadow:0 0 15px rgba(0,0,0,0.1)}}
    h1{{text-align:center; color:#333; border-bottom:3px solid #007bff; padding-bottom:15px; margin-bottom:25px}}
    h2{{color:#2c3e50; margin-top:25px; border-left: 5px solid #007bff; padding-left: 10px; text-transform:uppercase; font-size:18px}}
    li{{margin-bottom:12px; line-height:1.6; color:#555}}
    a{{color:#007bff; text-decoration:none; font-weight:bold}}
    a:hover{{text-decoration:underline}}
    .footer{{text-align:center; font-size:12px; color:#999; margin-top:40px; border-top: 1px solid #eee; padding-top: 20px}}
    </style></head><body><div class="box">
    
    <h1>☕ BRIEFING MATINAL</h1>
    
    {html_mercado} <p style="text-align:center; color:#666; font-style:italic;">Aqui está o resumo do que importa hoje.</p>
    """
    
    tem_conteudo = False
    for cat, items in dados.items():
        if not items: continue
        try:
            # Prompt para a IA
            prompt = f"""
            Você é um editor experiente. Resuma estas notícias de {cat} para HTML.
            Conteúdo: {' '.join(items)}
            
            Regras de formatação:
            1. Use tags <ul> para a lista e <li> para cada item.
            2. Comece cada <li> com um emoji adequado ao tema da notícia.
            3. Seja direto e objetivo (bullet points curtos).
            4. No final de cada item, coloque o link original dentro de uma tag <a href="...">[Ler mais]</a>.
            5. Retorne APENAS o HTML da lista.
            """
            
            resp = model.generate_content(prompt)
            html += f"<h2>{cat}</h2>{resp.text}"
            tem_conteudo = True
            time.sleep(5) 
        except Exception as e:
            print(f"Erro em {cat}: {e}")

    html += '<div class="footer">Gerado automaticamente por Gustavo AI • Powered by Gemini & Yahoo Finance</div></div></body></html>'

    if tem_conteudo:
        msg = MIMEMultipart()
        msg['From'] = MEU_EMAIL
        msg['To'] = DESTINATARIO
        msg['Subject'] = "☕ Seu Briefing: Mercado, Tech e Notícias"
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MEU_EMAIL, MINHA_SENHA_APP)
        server.send_message(msg)
        server.quit()
        print("✅ E-mail enviado com sucesso!")
    else:
        print("⚠️ Nenhuma notícia encontrada para enviar.")

# Execução Principal
painel_financeiro = obter_dados_mercado()
dados_noticias = buscar_noticias()
gerar_html_e_enviar(dados_noticias, painel_financeiro)
