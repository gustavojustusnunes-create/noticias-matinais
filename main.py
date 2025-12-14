import os
import smtplib
import feedparser
import google.generativeai as genai
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- PEGA AS SENHAS DO COFRE DO GITHUB ---
API_KEY = os.environ["GEMINI_KEY"]
MEU_EMAIL = os.environ["EMAIL_USER"]
MINHA_SENHA_APP = os.environ["EMAIL_PASSWORD"]
DESTINATARIO = MEU_EMAIL 

# Configura a IA
genai.configure(api_key=API_KEY)

# --- AQUI ESTAVA O ERRO, AGORA ESTÁ CORRIGIDO ---
# Sua chave só aceita este modelo específico:
model = genai.GenerativeModel('gemini-flash-latest') 

fontes = {
    '💰 Mercado & Finanças': ['https://www.infomoney.com.br/feed/', 'https://braziljournal.com/feed/'],
    '📱 Tech & Inovação': ['https://rss.tecmundo.com.br/feed', 'https://olhardigital.com.br/feed/'],
    '✨ Fofoca & Fama': ['https://revistaquem.globo.com/rss/quem/', 'https://www.metropoles.com/colunas/leo-dias/feed'],
    '🌍 Notícias Gerais': ['https://g1.globo.com/rss/g1/']
}

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

def gerar_html_e_enviar(dados):
    html = """
    <!DOCTYPE html><html><head><style>
    body{font-family:Helvetica,sans-serif;background:#f4f4f4;padding:20px}
    .box{max-width:600px;margin:0 auto;background:#fff;padding:30px;border-radius:10px;box-shadow:0 0 10px rgba(0,0,0,0.1)}
    h1{text-align:center;color:#333;border-bottom:2px solid #333;padding-bottom:10px}
    h2{color:#d32f2f;margin-top:20px;text-transform:uppercase;font-size:18px}
    li{margin-bottom:10px;line-height:1.5;color:#555}
    a{color:#007bff;text-decoration:none;font-weight:bold}
    .footer{text-align:center;font-size:12px;color:#999;margin-top:30px}
    </style></head><body><div class="box">
    <h1>📰 BRIEFING DO GUSTAVO</h1>
    <p style="text-align:center;color:#666">Seu resumo diário automático.</p>
    """
    
    tem_conteudo = False
    for cat, items in dados.items():
        if not items: continue
        try:
            # Prompt para a IA
            prompt = f"""
            Você é um editor web. Resuma estas notícias de {cat} para HTML:
            {' '.join(items)}
            
            Regras:
            1. Use tags <ul> e <li>.
            2. Coloque emojis no início de cada <li>.
            3. Escolha o melhor link e coloque em uma tag <a href="...">Leia mais</a> no final do item.
            4. NÃO use ```html ou markdown, retorne apenas o código HTML puro.
            """
            
            resp = model.generate_content(prompt)
            html += f"<h2>{cat}</h2>{resp.text}"
            tem_conteudo = True
            time.sleep(10) # Pausa de segurança
        except Exception as e:
            print(f"Erro em {cat}: {e}")

    html += '<div class="footer">Gerado via GitHub Actions • Gemini AI</div></div></body></html>'

    if tem_conteudo:
        msg = MIMEMultipart()
        msg['From'] = MEU_EMAIL
        msg['To'] = DESTINATARIO
        msg['Subject'] = "☕ Seu Briefing Diário Chegou!"
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MEU_EMAIL, MINHA_SENHA_APP)
        server.send_message(msg)
        server.quit()
        print("✅ E-mail enviado com sucesso!")
    else:
        print("⚠️ Nenhuma notícia encontrada para enviar.")

# Execução
dados = buscar_noticias()
gerar_html_e_enviar(dados)
