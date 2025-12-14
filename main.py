import os
import smtplib
import feedparser
import google.generativeai as genai
import yfinance as yf
import time
from datetime import datetime
import pytz # Para garantir o fuso horário do Brasil
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

def obter_data_hoje():
    # Define o fuso horário de São Paulo
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_br)
    
    # Listas para tradução manual (mais seguro que depender do servidor)
    dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    dia_sem = dias[agora.weekday()]
    dia_num = agora.day
    mes_nome = meses[agora.month - 1]
    ano = agora.year
    
    return f"{dia_sem}, {dia_num} de {mes_nome} de {ano}"

def obter_dados_mercado():
    print("📈 Consultando a Bolsa de Valores...")
    try:
        tickers = ['BRL=X', 'EURBRL=X', 'PETR4.SA', 'BTC-USD']
        dados = yf.Tickers(' '.join(tickers))
        
        # Pega o último preço disponível
        dolar = dados.tickers['BRL=X'].history(period='1d')['Close'].iloc[-1]
        euro = dados.tickers['EURBRL=X'].history(period='1d')['Close'].iloc[-1]
        petro = dados.tickers['PETR4.SA'].history(period='1d')['Close'].iloc[-1]
        btc = dados.tickers['BTC-USD'].history(period='1d')['Close'].iloc[-1]
        
        html_mercado = f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 30px; border: 1px solid #e9ecef; box-shadow: inset 0 0 5px rgba(0,0,0,0.02);">
            <h3 style="margin-top: 0; color: #444; text-align: center; font-size: 16px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px;">📊 O Mercado Agora</h3>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; text-align: center; gap: 15px;">
                <div style="min-width: 80px;">
                    <div style="font-size: 12px; color: #888;">DÓLAR</div>
                    <div style="font-size: 18px; font-weight: bold; color: #2ecc71;">R$ {dolar:.2f}</div>
                </div>
                <div style="min-width: 80px;">
                    <div style="font-size: 12px; color: #888;">EURO</div>
                    <div style="font-size: 18px; font-weight: bold; color: #3498db;">R$ {euro:.2f}</div>
                </div>
                <div style="min-width: 80px;">
                    <div style="font-size: 12px; color: #888;">PETROBRAS</div>
                    <div style="font-size: 18px; font-weight: bold; color: #e67e22;">R$ {petro:.2f}</div>
                </div>
                <div style="min-width: 80px;">
                    <div style="font-size: 12px; color: #888;">BITCOIN</div>
                    <div style="font-size: 18px; font-weight: bold; color: #f1c40f;">${btc:,.0f}</div>
                </div>
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
    data_hoje = obter_data_hoje()
    
    html = f"""
    <!DOCTYPE html><html><head><style>
    body{{font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; background-color:#f4f4f4; padding:20px; color:#333;}}
    .container{{max-width:600px; margin:0 auto; background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 15px rgba(0,0,0,0.08);}}
    .header{{background-color:#000; color:#fff; padding:30px 20px; text-align:center;}}
    .header h1{{margin:0; font-size:24px; letter-spacing:1px; text-transform:uppercase;}}
    .header p{{margin:5px 0 0; font-size:14px; opacity:0.8;}}
    .content{{padding:30px;}}
    .category-title{{color:#d35400; border-bottom: 2px solid #fcebe1; padding-bottom:5px; margin-top:30px; font-size:18px; text-transform:uppercase; letter-spacing:0.5px;}}
    ul{{padding-left:0; list-style:none;}}
    li{{margin-bottom:15px; line-height:1.6; font-size:15px;}}
    a{{color:#2980b9; text-decoration:none; font-weight:600; font-size:13px;}}
    a:hover{{text-decoration:underline;}}
    .footer{{background-color:#f9f9f9; text-align:center; padding:20px; font-size:12px; color:#aaa; border-top:1px solid #eee;}}
    </style></head><body>
    
    <div class="container">
        <div class="header">
            <h1>Briefing do Gustavo</h1>
            <p>{data_hoje}</p> </div>
        
        <div class="content">
            {html_mercado}
            """
    
    tem_conteudo = False
    for cat, items in dados.items():
        if not items: continue
        try:
            prompt = f"""
            Resuma estas notícias de {cat} para uma newsletter HTML.
            Conteúdo: {' '.join(items)}
            Regras:
            1. Retorne APENAS o código HTML de uma lista <ul>.
            2. Use emojis no início de cada <li>.
            3. Coloque o link 'Ler mais' dentro de <a href='...'></a> no final.
            4. Sem markdown, só HTML puro.
            """
            resp = model.generate_content(prompt)
            html += f"<h2 class='category-title'>{cat}</h2>{resp.text}"
            tem_conteudo = True
            time.sleep(5) 
        except Exception as e:
            print(f"Erro em {cat}: {e}")

    html += """
        </div>
        <div class="footer">
            Gerado via GitHub Actions • Gemini AI • yFinance
        </div>
    </div>
    </body></html>
    """

    if tem_conteudo:
        msg = MIMEMultipart()
        msg['From'] = MEU_EMAIL
        msg['To'] = DESTINATARIO
        msg['Subject'] = f"☕ Briefing: {data_hoje}" # Assunto com data também!
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MEU_EMAIL, MINHA_SENHA_APP)
        server.send_message(msg)
        server.quit()
        print("✅ E-mail enviado com sucesso!")
    else:
        print("⚠️ Nenhuma notícia encontrada.")

# Execução
painel = obter_dados_mercado()
dados = buscar_noticias()
gerar_html_e_enviar(dados, painel)
