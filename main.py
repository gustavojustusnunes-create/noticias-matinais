import os
import smtplib
import feedparser
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time

# --- 1. CONFIGURAÇÕES DE AMBIENTE ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
GCP_JSON = os.environ.get("GCP_JSON") 
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 

# Validação de Segurança
if not GEMINI_KEY:
    print("ERRO CRÍTICO: Chave GEMINI_KEY não encontrada.")
    exit(1)

# Configura a IA
genai.configure(api_key=GEMINI_KEY)
# ALTERADO PARA GEMINI-PRO (Mais compatível)
model = genai.GenerativeModel('gemini-pro')

# Fontes de Notícias
RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/"
}

# --- 2. INTELIGÊNCIA ARTIFICIAL ---

def buscar_e_resumir(tema):
    print(f"      ...Lendo notícias de {tema}...")
    url = RSS_FEEDS.get(tema)
    if not url:
        return "<p>Fonte não configurada.</p>"

    feed = feedparser.parse(url)
    if not feed.entries:
        return "<p>Nenhuma notícia encontrada hoje.</p>"

    top_noticias = feed.entries[:5]
    
    texto_cru = ""
    for entry in top_noticias:
        texto_cru += f"- {entry.title}: {entry.link}\n"

    prompt = f"""
    Você é um editor de newsletter matinal.
    Analise estas manchetes sobre {tema}:
    {texto_cru}

    Sua missão:
    1. Escreva um resumo único de 2 parágrafos curtos.
    2. Use um tom leve, direto e inteligente.
    3. Use <b>negrito</b> para destaques importantes.
    4. Adicione 1 emoji no início.
    5. Termine com uma lista <ul> simples dos links originais.
    
    Responda apenas com o HTML do conteúdo.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Erro na IA para {tema}: {e}")
        lista_html = "<ul>" + "".join([f"<li><a href='{n.link}'>{n.title}</a></li>" for n in top_noticias]) + "</ul>"
        return f"<p>Resumo indisponível. Manchetes do dia:</p>{lista_html}"

# --- 3. MONTAGEM DO EMAIL ---

def gerar_html_final(nome, conteudos):
    blocos_html = ""
    for tema, texto in conteudos.items():
        if texto:
            blocos_html += f"""
            <div style="margin-bottom: 30px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="background-color: #007bff; color: white; padding: 8px 15px; font-weight: bold; text-transform: uppercase; font-size: 14px;">
                    {tema}
                </div>
                <div style="padding: 20px; color: #444; line-height: 1.6;">
                    {texto}
                </div>
            </div>
            """

    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #2c3e50; padding: 30px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">☕ Briefing Matinal</h1>
                <p style="color: #bdc3c7; margin-top: 10px; font-size: 14px;">{data_hoje}</p>
            </div>
            <div style="padding: 30px 20px 10px 20px; text-align: center;">
                <p style="font-size: 18px; color: #333;">Bom dia, <b>{nome}</b>!</p>
                <p style="color: #666; font-size: 14px;">Aqui está o resumo do que rola no mundo.</p>
            </div>
            <div style="padding: 20px;">
                {blocos_html}
            </div>
            <div style="background-color: #eee; padding: 20px; text-align: center; font-size: 12px; color: #888;">
                <p>Gerado por IA • {data_hoje}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# --- 4. ENVIO E CONEXÃO ---

def conectar_banco():
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("noticias_db").sheet1
    except Exception as e:
        print(f"Erro crítico no banco de dados: {e}")
        return None

def enviar_email(destinatario, nome, html_content):
    msg = MIMEMultipart()
    msg['From'] = f"Briefing IA <{EMAIL_SENDER}>"
    msg['To'] = destinatario
    msg['Subject'] = f"☕ Seu Briefing Matinal - {datetime.now().strftime('%d/%m')}"

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro de SMTP ao enviar para {destinatario}: {e}")
        return False

# --- 5. EXECUÇÃO PRINCIPAL ---

def main():
    print("🚀 Iniciando motor de notícias...")
    
    sheet = conectar_banco()
    if not sheet:
        return

    usuarios = sheet.get_all_records()
    print(f"📋 {len(usuarios)} usuários encontrados.")

    cache_resumos = {} 

    for usuario in usuarios:
        nome = usuario['Nome']
        email = usuario['Email']
        
        # Pula linhas vazias
        if not email or not nome:
            continue

        print(f"🔄 Processando para: {nome}...")
        
        conteudos_usuario = {}
        
        # Mapeamento conforme sua planilha (image_336f8c.png)
        mapa = {
            "Mercado": "Mercado",
            "Tech": "Tech",
            "Motos": "Motos",
            "Fofoca": "Fofoca"
        }

        tem_conteudo = False
        for coluna_planilha, chave_rss in mapa.items():
            if usuario.get(coluna_planilha) == "Sim":
                tem_conteudo = True
                
                if chave_rss not in cache_resumos:
                    print(f"   🤖 Gerando resumo IA inédito para: {chave_rss}")
                    cache_resumos[chave_rss] = buscar_e_resumir(chave_rss)
                    time.sleep(1) 
                
                conteudos_usuario[chave_rss] = cache_resumos[chave_rss]

        if tem_conteudo:
            html = gerar_html_final(nome, conteudos_usuario)
            sucesso = enviar_email(email, nome, html)
            if sucesso:
                print(f"   ✅ Email enviado com sucesso!")
        else:
            print(f"   ⚠️ {nome} não tem temas marcados como 'Sim'.")

if __name__ == "__main__":
    main()
