import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

import feeds
from claude_api import extrair_contexto_base, chamar_claude_api
from video_builder import criar_video
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_FROM, SMTP_HOST, SMTP_PORT

EMAIL_DESTINO = "gustavojustusnunes@gmail.com"

def enviar_email_com_anexo(dest, html, subject, anexo_path):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"All News Journal <{EMAIL_FROM or EMAIL_SENDER}>"
    msg["To"] = dest
    msg.attach(MIMEText("Acesse a versão HTML para ler a mensagem.", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    if os.path.exists(anexo_path):
        with open(anexo_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(anexo_path)}"')
        msg.attach(part)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_FROM or EMAIL_SENDER, dest, msg.as_string())
    server.quit()
    return True

def main():
    print("🎬 Iniciando geração do Vídeo Diário...")
    try:
        print("   📡 Buscando notícia real do caderno Economia para o vídeo...")
        entries = feeds.coletar_entries_unico("Economia")
        if not entries:
            print("❌ Nenhuma notícia encontrada.")
            return

        entry = entries[0]
        TITULO_BASE = entry.get("title", "Economia Global")
        contexto = extrair_contexto_base(entry, max_chars=1500)
        
        prompt = (
            "Você é o âncora principal de um telejornal/podcast muito respeitado. "
            "Crie um roteiro aprofundado, analítico e de tom sério (aprox. 80-100 palavras) "
            "sobre a notícia abaixo. Vá direto aos fatos, sem saudações. "
            "O texto será lido por um sintetizador de voz (use pontuação para pausas). "
            f"\n\nTítulo Original: {TITULO_BASE}\nContexto: {contexto}"
        )
        resumo_ia = chamar_claude_api(prompt, max_tokens=300)
        
        if resumo_ia and len(resumo_ia.split()) > 20:
            RESUMO = resumo_ia.strip().strip('"')
            TITULO = TITULO_BASE
        else:
            TITULO = TITULO_BASE
            RESUMO = contexto[:400].rsplit('.', 1)[0] + "."
            
        URL_BG = feeds.extrair_imagem_rss(entry, "Economia")
        print(f"   📰 Notícia escolhida: {TITULO[:50]}...")

        video_path = criar_video("Economia", TITULO, RESUMO, URL_BG)

        html = f"""
        <html>
        <body style="font-family: sans-serif; background: #fdfbf7; padding: 20px;">
            <h2 style="color: #0a5c5a;">Seu Vídeo Diário de Notícias Chegou! 🎥</h2>
            <p>Olá Gustavo,</p>
            <p>Em anexo você encontra o vídeo em formato vertical para Reels/TikTok gerado automaticamente.</p>
            <p><b>Tema:</b> Economia<br>
            <b>Título:</b> {TITULO}</p>
            <br>
            <p><i>All News Journal Automation</i></p>
        </body>
        </html>
        """
        
        hoje_str = datetime.now().strftime("%d/%m/%Y")
        subject = f"🎥 Seu Vídeo Diário All News Journal - {hoje_str}"
        
        print(f"   ✉️  Enviando email para {EMAIL_DESTINO} com o anexo...")
        enviar_email_com_anexo(EMAIL_DESTINO, html, subject, str(video_path))
        print("✅ Email e vídeo enviados com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro crítico no envio diário: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
