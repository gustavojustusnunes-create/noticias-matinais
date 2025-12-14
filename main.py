import os
import smtplib
import feedparser
import google.generativeai as genai
import yfinance as yf
import time
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- CONFIGURAÇÕES E SEGREDOS ---
API_KEY = os.environ["GEMINI_KEY"]
MEU_EMAIL = os.environ["EMAIL_USER"]
MINHA_SENHA_APP = os.environ["EMAIL_PASSWORD"]

# Configura a IA
genai.configure(api_key=API_KEY)

# --- DEFINIÇÃO DOS MODELOS ---
# 1. Principal: O modelo novo e rápido (Limite 20/dia)
MODELO_PRINCIPAL = 'models/gemini-2.5-flash'
# 2. Reserva: Um modelo diferente (Gemma) para tentar salvar o dia
MODELO_RESERVA = 'models/gemma-3-12b-it'

# --- CONEXÃO COM A PLANILHA ---
def conectar_planilha():
    try:
        if "GCP_JSON" not in os.environ:
            return []
        info_json = json.loads(os.environ["GCP_JSON"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(info_json, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("noticias_db").sheet1
        return sheet.get_all_records()
    except Exception as e:
        print(f"❌ Erro ao ler planilha: {e}")
        return []

# --- FONTES DE NOTÍCIAS ---
fontes = {
    '🏍️ Motos & Estradas': ['https://www.motociclismoonline.com.br/feed/', 'https://motor1.uol.com.br/rss/category/motos/'],
    '💰 Mercado & Finanças': ['https://www.infomoney.com.br/feed/', 'https://braziljournal.com/feed/'],
    '📱 Tech & Inovação': ['https://rss.tecmundo.com.br/feed', 'https://olhardigital.com.br/feed/'],
    '✨ Fofoca & Lazer': ['https://vogue.globo.com/rss/vogue/gente', 'https://revistaquem.globo.com/rss/quem/']
}

def obter_data_hoje():
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_br)
    return f"{agora.day}/{agora.month}/{agora.year}"

def obter_dados_mercado():
    print("📈 Consultando Mercado...")
    try:
        tickers = ['BRL=X', 'EURBRL=X', 'PETR4.SA', 'BTC-USD']
        dados = yf.Tickers(' '.join(tickers))
        dolar = dados.tickers['BRL=X'].history(period='1d')['Close'].iloc[-1]
        euro = dados.tickers['EURBRL=X'].history(period='1d')['Close'].iloc[-1]
        btc = dados.tickers['BTC-USD'].history(period='1d')['Close'].iloc[-1]
        
        return f"""
        <div style="background:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:20px; text-align:center;">
            <b>DÓLAR:</b> R$ {dolar:.2f} | <b>EURO:</b> R$ {euro:.2f} | <b>BITCOIN:</b> ${btc:,.0f}
        </div>
        """
    except Exception as e:
        print(f"⚠️ Erro no Mercado: {e}")
        return ""

def gerar_resumo(prompt):
    """Tenta gerar resumo usando Principal -> Reserva -> Falha Graciosa"""
    try:
        # Tenta Modelo Principal
        model = genai.GenerativeModel(MODELO_PRINCIPAL)
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e1:
        print(f"     ⚠️ Principal falhou ({e1}). Tentando reserva...")
        try:
            # Tenta Modelo Reserva (Gemma)
            model_bkp = genai.GenerativeModel(MODELO_RESERVA)
            resp = model_bkp.generate_content(prompt)
            return resp.text
        except Exception as e2:
            print(f"     ❌ Reserva também falhou. Entregando sem resumo.")
            # Se tudo falhar, retorna um texto padrão para não quebrar o email
            return "<i>(O sistema de IA está descansando agora. Confira os links originais acima!)</i>"

def buscar_e_resumir_noticias():
    print("🕵️‍♂️ Buscando e Resumindo Notícias...")
    resumos_prontos = {}
    
    for categoria, urls in fontes.items():
        lista_titulos = []
        html_links = "<ul>" # Prepara uma lista manual de links caso a IA falhe
        
        for url in urls:
            try:
                print(f"   - Lendo: {url}")
                feed = feedparser.parse(url)
                for entry in feed.entries[:4]:
                    lista_titulos.append(f"- {entry.title} ({entry.link})")
                    html_links += f"<li><a href='{entry.link}'>{entry.title}</a></li>"
            except Exception as e:
                print(f"     ❌ Erro ao ler feed {url}: {e}")
        
        html_links += "</ul>"
        
        if lista_titulos:
            print(f"   🤖 Resumindo {categoria}...")
            prompt = f"Resuma para newsletter HTML (lista <ul> com emojis). Foque no essencial: {' '.join(lista_titulos)}"
            
            texto_ia = gerar_resumo(prompt)
            
            # Se a IA devolveu o erro padrão, colocamos a lista de links manuais
            if "O sistema de IA está descansando" in texto_ia:
                resumos_prontos[categoria] = html_links + "<br>" + texto_ia
            else:
                resumos_prontos[categoria] = texto_ia
                
            print(f"     ✅ Categoria {categoria} processada.")
            time.sleep(5) 
            
    return resumos_prontos

def enviar_email(destinatario, nome, html_corpo, assunto):
    msg = MIMEMultipart()
    msg['From'] = MEU_EMAIL
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(html_corpo, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(MEU_EMAIL, MINHA_SENHA_APP)
    server.send_message(msg)
    server.quit()

# --- BLOCO PRINCIPAL ---
usuarios = conectar_planilha()
if not usuarios:
    print("⚠️ Ninguém na lista ou erro na planilha.")
    exit()

html_mercado = obter_dados_mercado()
noticias_do_dia = buscar_e_resumir_noticias() 
data_hoje = obter_data_hoje()

print(f"📧 Iniciando envios para {len(usuarios)} pessoas...")

for pessoa in usuarios:
    nome = pessoa['Nome']
    email = pessoa['Email']
    
    html_final = f"""
    <html><body style="font-family:Arial; color:#333;">
    <div style="max-width:600px; margin:0 auto;">
        <h1 style="background:#2c3e50; color:#fff; padding:20px; text-align:center;">Bom dia, {nome}! ☕</h1>
        <p style="text-align:center; color:#888;">Seu resumo de {data_hoje}</p>
    """
    
    if pessoa.get('Mercado') == 'Sim':
        html_final += html_mercado
        if '💰 Mercado & Finanças' in noticias_do_dia:
            html_final += f"<h3>💰 Giro do Mercado</h3>{noticias_do_dia['💰 Mercado & Finanças']}"

    if pessoa.get('Tech') == 'Sim' and '📱 Tech & Inovação' in noticias_do_dia:
        html_final += f"<h3>📱 Tecnologia</h3>{noticias_do_dia['📱 Tech & Inovação']}"

    if pessoa.get('Motos') == 'Sim' and '🏍️ Motos & Estradas' in noticias_do_dia:
        html_final += f"<h3>🏍️ Duas Rodas</h3>{noticias_do_dia['🏍️ Motos & Estradas']}"

    if pessoa.get('Fofoca') == 'Sim' and '✨ Fofoca & Lazer' in noticias_do_dia:
        html_final += f"<h3>✨ Variedades</h3>{noticias_do_dia['✨ Fofoca & Lazer']}"
        
    html_final += "<br><hr><p style='font-size:12px; text-align:center;'>Enviado por Gustavo AI News</p></div></body></html>"
    
    try:
        enviar_email(email, nome, html_final, f"☕ Briefing do {nome} - {data_hoje}")
        print(f"✅ Enviado para {nome} ({email})")
    except Exception as e:
        print(f"❌ Erro ao enviar para {nome}: {e}")
