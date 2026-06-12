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
        # Rotação semanal
        temas_semana = {
            0: "Economia",  # Segunda-feira
            1: "IA",        # Terça-feira
            2: "Mundo",     # Quarta-feira
            3: "Politica",  # Quinta-feira
            4: "Ciencia",   # Sexta-feira
            5: "Cinema",    # Sábado
            6: "Wellness"   # Domingo
        }
        dia_semana = datetime.now().weekday()
        tema_hoje = temas_semana.get(dia_semana, "Mundo")
        
        print(f"   📡 Buscando notícia real do caderno {tema_hoje} para o vídeo...")
        entries = feeds.coletar_entries_unico(tema_hoje)
        if not entries:
            print(f"❌ Nenhuma notícia encontrada para {tema_hoje}.")
            return

        entry = entries[0]
        TITULO_BASE = entry.get("title", f"Destaques de {tema_hoje}")
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
            
        URL_BG = feeds.extrair_imagem_rss(entry, tema_hoje)
        print(f"   📰 Notícia escolhida: {TITULO[:50]}...")

        video_path = criar_video(tema_hoje, TITULO, RESUMO, URL_BG)
        
        # Gerar legenda sugerida para o Reel
        prompt_legenda = (
            "Crie uma legenda curta e engajadora para o Instagram/TikTok para um vídeo sobre a seguinte notícia: "
            f"\n\nTítulo: {TITULO}\nResumo: {RESUMO}\n\n"
            "Regras: "
            "1. Escreva 1 parágrafo chamativo.\n"
            "2. Adicione um CTA para ler mais no link da bio.\n"
            "3. Inclua 4-6 hashtags relevantes ao tema e a hashtag #AllNewsJournal.\n"
            "4. A última linha deve obrigatoriamente marcar '@all.news.journal'.\n"
            "Responda apenas com o texto da legenda, sem introduções."
        )
        legenda_ia = chamar_claude_api(prompt_legenda, max_tokens=150)
        
        if not legenda_ia:
            legenda_ia = (
                f"{TITULO}\n\n"
                f"{RESUMO}\n\n"
                "Acesse o link na bio para ler sem ruídos! 📰✨\n\n"
                f"#{tema_hoje} #Noticias #AllNewsJournal\n"
                "@all.news.journal"
            )
            
        legenda_html = legenda_ia.strip().replace("\n", "<br>")

        html = f"""
        <html>
        <body style="font-family: sans-serif; background: #fdfbf7; padding: 20px;">
            <h2 style="color: #0a5c5a;">Seu Vídeo Diário de Notícias Chegou! 🎥</h2>
            <p>Olá Gustavo,</p>
            <p>Em anexo você encontra o vídeo em formato vertical para Reels/TikTok gerado automaticamente.</p>
            <p><b>Tema:</b> {tema_hoje}<br>
            <b>Título:</b> {TITULO}</p>
            <br>
            <div style="background: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                <h3 style="color: #0a5c5a; margin-top: 0;">Sugestão de Legenda (Copie e Cole):</h3>
                <p style="font-family: monospace; font-size: 14px; color: #333;">{legenda_html}</p>
            </div>
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
