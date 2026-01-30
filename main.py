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
import sys

# --- 1. CONFIGURAÇÕES E CONSTANTES ---
# Carregando variáveis de ambiente
GEMINI_KEY = os.environ.get("GEMINI_KEY")
GCP_JSON = os.environ.get("GCP_JSON")
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Configuração de Fontes
RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/"
}

# --- 2. SERVIÇOS DE INFRAESTRUTURA ---

def configurar_ia():
    """Inicializa o cliente do Gemini com tratamento de erro."""
    if not GEMINI_KEY:
        print("❌ ERRO CRÍTICO: GEMINI_KEY não encontrada.")
        sys.exit(1)
    
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Usamos 'gemini-1.5-flash' pois é o alias estável
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        print(f"❌ Erro ao configurar IA: {e}")
        sys.exit(1)

def conectar_banco():
    """Conecta ao Google Sheets via Service Account."""
    if not GCP_JSON:
        print("❌ ERRO CRÍTICO: GCP_JSON não encontrado.")
        sys.exit(1)

    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        # Abre a primeira planilha encontrada ou pelo nome específico
        return client.open("noticias_db").sheet1
    except Exception as e:
        print(f"❌ Erro ao conectar no Banco de Dados: {e}")
        return None

# --- 3. LÓGICA DE NEGÓCIO (CORE) ---

def buscar_e_resumir(model, tema):
    """Lê RSS, processa e envia para a IA resumir."""
    print(f"      ...Lendo notícias de {tema}...")
    url = RSS_FEEDS.get(tema)
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return "<p>Nenhuma notícia relevante encontrada hoje.</p>"
        
        # Pega as top 5 notícias
        top_noticias = feed.entries[:5]
        texto_cru = "\n".join([f"- {entry.title}: {entry.link}" for entry in top_noticias])

        prompt = f"""
        Atue como um editor sênior de newsletter.
        Tema: {tema}
        Notícias:
        {texto_cru}

        Instruções:
        1. Crie um resumo consolidado de 2 parágrafos.
        2. Tom de voz: Profissional, mas conversacional (Smart Brevity).
        3. Destaque termos chave em <b>negrito</b>.
        4. Comece com um emoji relevante ao tema.
        5. Ao final, liste os links originais em uma tag <ul> HTML simples.
        
        Saída: Apenas o HTML (sem markdown ```html).
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"⚠️ Erro na geração de conteúdo para {tema}: {e}")
        # Fallback: Retorna apenas os links se a IA falhar
        lista_links = "".join([f"<li><a href='{n.link}'>{n.title}</a></li>" for n in feed.entries[:3]])
        return f"<p>Erro momentâneo na IA. Seguem as manchetes:</p><ul>{lista_links}</ul>"

def gerar_template_email(nome, conteudos_html):
    """Monta o HTML final do e-mail com design responsivo básico."""
    blocos = ""
    for tema, html_tema in conteudos_html.items():
        cor_header = "#007bff" # Azul padrão
        if tema == "Mercado": cor_header = "#28a745"
        if tema == "Fofoca": cor_header = "#e83e8c"
        
        blocos += f"""
        <div style="margin-bottom: 25px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: {cor_header}; color: white; padding: 10px 15px; font-weight: bold; font-family: sans-serif;">
                {tema}
            </div>
            <div style="padding: 15px; background-color: #fff; color: #333; line-height: 1.5; font-family: sans-serif;">
                {html_tema}
            </div>
        </div>
        """

    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    return f"""
    <html>
    <body style="background-color: #f4f4f9; padding: 20px; font-family: sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px;">
            <h2 style="text-align: center; color: #333;">☕ Seu Briefing Diário • {data_hoje}</h2>
            <p>Bom dia, <b>{nome}</b>! Aqui está sua curadoria exclusiva.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            {blocos}
            <p style="text-align: center; color: #888; font-size: 12px; margin-top: 30px;">
                Gerado automaticamente por IA System v2.1
            </p>
        </div>
    </body>
    </html>
    """

def enviar_email(destinatario, nome, html_content):
    """Dispara o e-mail via SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Briefing IA <{EMAIL_SENDER}>"
        msg['To'] = destinatario
        msg['Subject'] = f"☕ Resumo: {datetime.now().strftime('%d/%m')}"
        
        # --- A CORREÇÃO ESTÁ AQUI: Dois parênteses no final ---
        msg.attach(MIMEText(html_content, 'html')) 

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Erro de SMTP para {destinatario}: {e}")
        return False

# --- 4. EXECUTOR PRINCIPAL ---

def main():
    print("🚀 Iniciando Motor de Newsletter (v2.3 Fix)...")
    
    # Inicializações
    model = configurar_ia()
    sheet = conectar_banco()
    
    if not sheet:
        print("Encerrando por falha no banco.")
        return

    usuarios = sheet.get_all_records()
    print(f"📋 {len(usuarios)} usuários na base.")

    # Cache para não gastar tokens gerando o mesmo resumo para pessoas diferentes
    cache_resumos = {}

    for usuario in usuarios:
        nome = usuario.get('Nome')
        email = usuario.get('Email')
        
        if not nome or not email:
            continue

        print(f"🔄 Processando: {nome}...")
        
        conteudos_usuario = {}
        # Mapeamento: Nome da Coluna no Sheets -> Chave no RSS_FEEDS
        mapa_temas = ["Mercado", "Tech", "Motos", "Fofoca"]

        for tema in mapa_temas:
            # Verifica se o usuário marcou "Sim" na coluna
            if usuario.get(tema, '').strip().lower() == "sim":
                
                # Verifica Cache
                if tema not in cache_resumos:
                    print(f"   🤖 Gerando resumo inédito: {tema}")
                    cache_resumos[tema] = buscar_e_resumir(model, tema)
                    time.sleep(2) # Respeitar Rate Limit da API
                
                conteudos_usuario[tema] = cache_resumos[tema]

        if conteudos_usuario:
            html_final = gerar_template_email(nome, conteudos_usuario)
            if enviar_email(email, nome, html_final):
                print(f"   ✅ Enviado para {email}")
            else:
                print(f"   ❌ Falha no envio para {email}")
        else:
            print(f"   ℹ️ {nome} não possui interesses ativos.")

    print("🏁 Processo finalizado.")

if __name__ == "__main__":
    main()
