"""
email_builder.py — Geração do HTML e envio de email do All News Journal
Inclui: painel financeiro, preheader, sumário, editorial, tempo de leitura,
        subject dinâmico e retry com backoff.
"""
import base64
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yfinance as yf

from config import (
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_FROM,
    SMTP_HOST, SMTP_PORT, URL_CANCELAMENTO,
    ICONES_TEMA, CORES_TEMA,
    RESEND_API_KEY, RESEND_FROM,
    LOGO_URL, LOGO_PATH, LOGO_CID,
)


# =============================================================================
# --- PAINEL FINANCEIRO ---
# =============================================================================
def formatar_indicador(nome, valor, variacao, prefixo=""):
    cor   = "green" if variacao >= 0 else "red"
    seta  = "▲" if variacao >= 0 else "▼"
    sinal = "+" if variacao > 0 else ""
    return (
        f"{prefixo} <b>{nome}:</b> {valor} "
        f"<span style='color:{cor}; font-size:11px;'>{seta} {sinal}{variacao:.2f}%</span>"
    )


def obter_indicadores():
    """Busca USD/BRL, IBOV e BTC via yfinance e retorna HTML do painel."""
    html_items = []

    def buscar_btc():
        for ticker_id, moeda in [("BTC-BRL", "BRL"), ("BTC-USD", "USD")]:
            try:
                hist = yf.Ticker(ticker_id).history(period="5d")
                if len(hist) >= 2:
                    atual = hist["Close"].iloc[-1]
                    ant   = hist["Close"].iloc[-2]
                    var   = (atual - ant) / ant * 100
                    label = f"R$ {atual/1000:.1f}k" if moeda == "BRL" else f"US$ {atual/1000:.1f}k"
                    return formatar_indicador("BTC", label, var, "₿")
            except Exception as e:
                print(f"⚠️ BTC/{moeda}: {e}")
        return None

    for ticker_id, nome, fmt, pfx in [
        ("BRL=X",  "USD",  lambda v: f"R$ {v:.2f}", "🇺🇸"),
        ("^BVSP",  "IBOV", lambda v: f"{int(v)} pts", "🇧🇷"),
    ]:
        try:
            hist = yf.Ticker(ticker_id).history(period="5d")
            if len(hist) >= 2:
                atual = hist["Close"].iloc[-1]
                ant   = hist["Close"].iloc[-2]
                var   = (atual - ant) / ant * 100
                html_items.append(formatar_indicador(nome, fmt(atual), var, pfx))
        except Exception as e:
            print(f"⚠️ {nome}: {e}")

    btc = buscar_btc()
    if btc:
        html_items.insert(1, btc)

    if not html_items:
        return ""
    return (
        "<div style='background-color:#e5e3de; padding:12px; text-align:center; "
        "font-family:monospace; font-size:13px; color:#111;'>"
        + " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(html_items)
        + "</div>"
    )


# =============================================================================
# --- GERAÇÃO DO HTML DO EMAIL ---
# =============================================================================
def gerar_html_final(nome, dados, painel, editorial="", coluna_autor=None):
    """
    Gera o HTML completo do email com:
    - Preheader invisível para preview no Gmail
    - Editorial do dia (se fornecido)
    - Coluna do Autor (se fornecido)
    - Sumário/índice clicável
    - Tempo de leitura estimado
    - Fallback de imagem com gradiente colorido
    """
    TURQUESA = "0a5c5a"
    CREME    = "fdfbf7"
    ESCURO   = "084c4a"

    hoje = datetime.now()
    MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    DIAS  = ["Segunda-feira","Terça-feira","Quarta-feira",
             "Quinta-feira","Sexta-feira","Sábado","Domingo"]
    data_ptbr = f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}"

    # ── Manchete principal (para preheader) ──────────────────────────────────
    manchete_principal = ""
    for tema, items in dados.items():
        if items:
            manchete_principal = items[0].get("titulo", "")
            break

    # ── Tempo de leitura ────────────────────────────────────────────────────
    total_palavras = sum(
        len(n.get("resumo", "").split())
        for items in dados.values() if items
        for n in items
    )
    if coluna_autor:
        total_palavras += len(coluna_autor.get("texto", "").split())
    tempo_leitura = max(1, round(total_palavras / 200))

    # ── Sumário ──────────────────────────────────────────────────────────────
    linhas_sumario = ""
    for tema, items in dados.items():
        if not items:
            continue
        icone = ICONES_TEMA.get(tema, "📰")
        cor   = CORES_TEMA.get(tema, TURQUESA)
        titulo_curto = items[0].get("titulo", "")[:50]
        if len(items[0].get("titulo", "")) > 50:
            titulo_curto += "…"
        linhas_sumario += (
            f"<a href='#caderno-{tema}' style='display:block;color:#{cor};font-size:14px;"
            f"text-decoration:none;padding:4px 0;font-weight:600;'>"
            f"{icone} {tema} — {titulo_curto}</a>"
        )

    # ── Preheader ────────────────────────────────────────────────────────────
    preheader = (
        f"<div style='display:none;max-height:0;overflow:hidden;mso-hide:all;'>"
        f"{manchete_principal} — Sua curadoria premium do All News Journal"
        f"</div>"
    )

    html = f"""
<html><body style="margin:0;padding:0;background-color:#e5e3de;font-family:'Lora','Times New Roman',serif;">
{preheader}
<div style="max-width:620px;margin:20px auto;background-color:#{CREME};border-radius:8px;
            overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.07);">

  <!-- CABEÇALHO -->
  <div style="padding:30px 20px 20px;text-align:center;border-bottom:3px solid #{TURQUESA};">
    <p style="margin:0 0 12px;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#999;">
      Edição Premium Digital
    </p>
    <img src="cid:{LOGO_CID}" alt="All News Journal"
         width="90" height="90"
         style="display:block;margin:0 auto 14px;width:90px;height:90px;border-radius:50%;">
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:36px;
               text-transform:uppercase;letter-spacing:3px;color:#{TURQUESA};">
      ALL NEWS JOURNAL
    </h1>
    <p style="margin:10px 0 4px;font-size:12px;color:#777;font-style:italic;">{data_ptbr}</p>
    <p style="margin:0;font-size:11px;color:#999;">⏱️ Leitura estimada: {tempo_leitura} min</p>
  </div>

  <!-- PAINEL FINANCEIRO -->
  {painel}

  <!-- SAUDAÇÃO + EDITORIAL -->
  <div style="padding:30px 30px 10px;">
    <p style="color:#555;font-size:15px;text-align:center;margin-bottom:{'20px' if editorial else '35px'};
              font-style:italic;border-bottom:{'none' if editorial else '1px solid #e5e3de'};padding-bottom:{'10px' if editorial else '25px'};">
      Bom dia, <b style="color:#{TURQUESA};">{nome}</b>. A sua curadoria premium de hoje está pronta.
    </p>
"""

    # ── Abertura ────────────────────────────────────────────────────────────
    if editorial:
        html += f"""
    <p style="font-size:15px;color:#444;font-style:italic;text-align:center;
              border-bottom:1px solid #e5e3de;padding-bottom:25px;margin-bottom:25px;
              line-height:1.7;">
      "{editorial}"
    </p>
"""

    # ── Coluna do Autor (Editorial Escrito) ──────────────────────────────────
    if coluna_autor:
        html += f"""
    <div style="margin-bottom:40px;padding-bottom:30px;border-bottom:2px solid #333;">
      <span style="background-color:#333;color:#fff;padding:7px 16px;
                   font-size:11px;font-weight:bold;text-transform:uppercase;
                   letter-spacing:1.5px;border-radius:4px 4px 0 0;display:inline-block;">
        🖋️ EDITORIAL
      </span>
      <img src="{coluna_autor['imagem']}"
           alt="Editorial"
           style="width:100%;height:230px;object-fit:cover;border-radius:0 6px 6px 6px;
                  border-bottom:4px solid #333;display:block;margin-top:0;">
      <div style="padding-top:18px;">
        <h3 style="margin:0 0 14px;font-size:21px;
                   font-family:'Playfair Display',Georgia,serif;
                   line-height:1.35;color:#111;">
          {coluna_autor['titulo']}
        </h3>
        <p style="margin:0 0 16px;font-size:15px;color:#3a3a3a;line-height:1.75;
                  font-family:'Lora','Times New Roman',serif;white-space:pre-wrap;">{coluna_autor['texto']}</p>
      </div>
    </div>
"""

    # ── Podcast Promocional ──────────────────────────────────────────────────
    html += f"""
    <div style="background-color:#0a5c5a;padding:25px 20px;border-radius:8px;margin-bottom:30px;text-align:center;">
      <h3 style="color:#ffffff;margin:0 0 10px;font-family:'Playfair Display',Georgia,serif;font-size:20px;">
        🎧 Escute a Edição de Hoje!
      </h3>
      <p style="color:#e0ecec;font-size:14px;margin:0 0 18px;line-height:1.5;">
        O All News Journal agora também é podcast. Ana e Leo comentam as principais notícias do dia.
      </p>
      <a href="https://all-news-journal-ikgdbajp9nobmquagzvx3v.streamlit.app?edicao={datetime.now().strftime('%Y-%m-%d')}"
         style="display:inline-block;background-color:#ffffff;color:#0a5c5a;padding:10px 24px;
                border-radius:20px;text-decoration:none;font-weight:bold;font-size:14px;margin-right:10px;">
        ▶️ Play no Site
      </a>
      <a href="https://open.spotify.com/show/033FwFJeZTyXrigyvfXpt3"
         style="display:inline-block;background-color:#1db954;color:#ffffff;padding:10px 24px;
                border-radius:20px;text-decoration:none;font-weight:bold;font-size:14px;">
        🎧 Ouvir no Spotify
      </a>
    </div>
"""

    # ── Sumário ──────────────────────────────────────────────────────────────
    if linhas_sumario:
        html += f"""
    <div style="background:#f5f3ef;padding:18px 24px;border-radius:8px;margin-bottom:30px;">
      <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#999;margin:0 0 10px;">
        📋 Nesta edição
      </p>
      {linhas_sumario}
    </div>
"""

    # ── Cadernos ─────────────────────────────────────────────────────────────
    for tema, items in dados.items():
        if not items:
            continue
        icone = ICONES_TEMA.get(tema, "📰")
        cor   = CORES_TEMA.get(tema, TURQUESA)
        html += f"""
    <!-- CADERNO: {tema.upper()} -->
    <div id="caderno-{tema}" style="margin:35px 0 20px;border-bottom:2px solid #{cor};">
      <span style="background-color:#{cor};color:#fff;padding:7px 16px;
                   font-size:11px;font-weight:bold;text-transform:uppercase;
                   letter-spacing:1.5px;border-radius:4px 4px 0 0;display:inline-block;">
        {icone} {tema}
      </span>
    </div>"""

        for n in items:
            titulo_safe = n["titulo"].replace('"', '&quot;').replace("'", "&#39;")
            # Fallback de imagem com gradiente colorido do caderno
            onerror_script = (
                f"this.onerror=null;"
                f"this.style.background='linear-gradient(135deg, #{cor}22, #{cor}55)';"
                f"this.style.height='120px';"
                f"this.src='data:image/svg+xml;base64,"
                f"PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MCA2MCI+"
                f"PHRleHQgeT0iLjllbSIgZm9udC1zaXplPSI1MCI+e2ljb25lX2I2NH08L3RleHQ+PC9zdmc+"
                f"';"
            )
            html += f"""
    <div style="margin-bottom:40px;padding-bottom:30px;border-bottom:1px solid #ede9e3;">
      <a href="{n['link']}" target="_blank" style="display:block;text-decoration:none;">
        <img src="{n['imagem']}"
             alt="{titulo_safe}"
             style="width:100%;height:230px;object-fit:cover;border-radius:6px;
                    border-bottom:4px solid #{cor};display:block;"
             onerror="{onerror_script}">
      </a>
      <div style="padding-top:18px;">
        <a href="{n['link']}" target="_blank" style="text-decoration:none;color:#111;">
          <h3 style="margin:0 0 14px;font-size:21px;
                     font-family:'Playfair Display',Georgia,serif;
                     line-height:1.35;color:#111;">
            {n['titulo']}
          </h3>
        </a>
        <p style="margin:0 0 16px;font-size:15px;color:#3a3a3a;line-height:1.75;
                  font-family:'Lora','Times New Roman',serif;">
          {n['resumo']}
        </p>
        <a href="{n['link']}" target="_blank"
           style="font-size:12px;color:#{cor};font-weight:bold;text-decoration:none;
                  text-transform:uppercase;letter-spacing:1px;
                  border-bottom:2px solid #{cor};padding-bottom:2px;">
          Ler matéria completa &rarr;
        </a>
      </div>
    </div>"""

    html += f"""
  </div><!-- /conteúdo -->

  <!-- RODAPÉ -->
  <div style="text-align:center;padding:25px 30px;background-color:#{ESCURO};
              color:#{CREME};font-family:'Lora','Times New Roman',serif;">
    <p style="margin:0 0 10px;font-size:10px;color:rgba(253,251,247,0.6);line-height:1.6;">
      Você recebe este email porque é assinante do All News Journal.<br/>
      Para cancelar sua assinatura,
      <a href="{URL_CANCELAMENTO}" style="color:#c9a84c;text-decoration:underline;">clique aqui</a>.
    </p>
    <p style="margin:0;font-size:14px;letter-spacing:1px;font-weight:bold;">
      ALL NEWS JOURNAL
    </p>
    <p style="margin:8px 0 0;opacity:0.7;font-size:11px;">
      © {hoje.year} All News Journal Group &nbsp;·&nbsp; Conteúdo Premium Digital
    </p>
    <p style="margin:6px 0 0;font-size:10px;opacity:0.5;">
      Recebeu esta edição porque é assinante do nosso serviço.
    </p>
  </div>

</div><!-- /wrapper -->
</body></html>"""
    return html


# =============================================================================
# --- MONTAGEM DO SUBJECT DINÂMICO ---
# =============================================================================
def montar_subject(dados):
    """
    Monta assunto do email com títulos das primeiras notícias de até 3 cadernos.
    Formato: 📰 Título1 | Título2 | Título3 (máx 90 chars)
    """
    trechos = []
    for tema, items in dados.items():
        if items and len(trechos) < 3:
            titulo = items[0].get("titulo", "")[:35]
            if len(items[0].get("titulo", "")) > 35:
                titulo += "…"
            trechos.append(titulo)

    if not trechos:
        hoje  = datetime.now()
        MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
        return f"📰 All News Journal — {hoje.day} de {MESES[hoje.month - 1]}. de {hoje.year}"

    subject = "📰 " + " | ".join(trechos)
    if len(subject) > 90:
        subject = subject[:87] + "…"
    return subject


# =============================================================================
# --- ENVIO DE EMAIL — SUBJECT DEFAULT ---
# =============================================================================
def _subject_default():
    hoje  = datetime.now()
    MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    return f"📰 All News Journal — {hoje.day} de {MESES[hoje.month - 1]}. de {hoje.year}"


# =============================================================================
# --- ENVIO VIA RESEND (provedor primário) ---
# =============================================================================
def enviar_email_resend(dest, html, subject=None):
    """
    Envia email via API do Resend (resend.com).
    3 tentativas com backoff de 15s. Retorna True/False.
    """
    if subject is None:
        subject = _subject_default()

    try:
        import resend
    except ImportError:
        print("      ❌ Pacote 'resend' não instalado — rode: pip install resend")
        return False

    resend.api_key = RESEND_API_KEY

    # Embute a logo inline (Content-ID) — referenciada como cid:LOGO_CID no HTML.
    # Funciona mesmo com o repositório privado (a raw URL daria 404 no Gmail).
    attachments = []
    try:
        with open(LOGO_PATH, "rb") as fh:
            attachments.append({
                "filename":     "anj-logo.png",
                "content":      base64.b64encode(fh.read()).decode(),
                "content_type": "image/png",
                "content_id":   LOGO_CID,
            })
    except Exception as e:
        print(f"      ⚠️ Logo não embutida ({e}). Email segue sem a imagem.")

    payload = {
        "from":    RESEND_FROM,
        "to":      [dest],
        "subject": subject,
        "html":    html,
        "text":    "Acesse a versão HTML para ler a edição completa.",
        "headers": {"X-Mailer": "All News Journal Mailer"},
    }
    if attachments:
        payload["attachments"] = attachments

    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            resp = resend.Emails.send(payload)
            # SDK retorna dict com 'id' em sucesso
            if isinstance(resp, dict) and resp.get("id"):
                return True
            # Resposta inesperada — trata como falha desta tentativa
            raise RuntimeError(f"resposta inesperada do Resend: {resp!r}")

        except Exception as e:
            msg_err = str(e).lower()
            # Rede de segurança: se o anexo (logo inline) for o problema, reenvia
            # SEM o anexo. A edição sair sem logo é melhor do que não sair.
            if "attachments" in payload and any(
                t in msg_err for t in ("attachment", "content_id", "validation_error")
            ):
                print("      ⚠️ Anexo da logo recusado — reenviando sem a logo.")
                payload.pop("attachments", None)
                continue

            # Erros permanentes: não vale a pena retentar
            if any(t in msg_err for t in ("invalid api key", "unauthorized", "validation_error", "invalid_to")):
                print(f"      ❌ Resend rejeitou definitivamente ({dest}): {e}")
                return False

            if tentativa < max_tentativas:
                espera = 15 * tentativa
                print(f"      ⚠️ Resend tentativa {tentativa} falhou ({e}). Aguardando {espera}s…")
                time.sleep(espera)
            else:
                print(f"      ❌ Falha definitiva (Resend) ao enviar para {dest}: {e}")
                return False

    return False


# =============================================================================
# --- ENVIO VIA SMTP GMAIL (legado / fallback) ---
# =============================================================================
def enviar_email_smtp(dest, html, subject=None):
    """
    Envia o email via SMTP do Gmail (caminho legado).
    3 tentativas com backoff de 15s. Retorna True/False.
    """
    if subject is None:
        subject = _subject_default()

    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"All News Journal <{EMAIL_FROM or EMAIL_SENDER}>"
            msg["To"]      = dest
            msg["X-Mailer"] = "All News Journal Mailer"
            msg.attach(MIMEText("Acesse a versão HTML para ler a edição completa.", "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM or EMAIL_SENDER, dest, msg.as_string())
            server.quit()
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"      ❌ Falha de autenticação SMTP — verifique EMAIL_USER/EMAIL_PASSWORD")
            return False  # Não adianta tentar novamente
        except smtplib.SMTPRecipientsRefused:
            print(f"      ❌ Destinatário recusado: {dest}")
            return False  # Não adianta tentar novamente
        except Exception as e:
            if tentativa < max_tentativas:
                espera = 15 * tentativa
                print(f"      ⚠️ Tentativa {tentativa} falhou ({e}). Aguardando {espera}s…")
                time.sleep(espera)
            else:
                print(f"      ❌ Falha definitiva ao enviar para {dest}: {e}")
                return False

    return False


# =============================================================================
# --- DISPATCHER ---
# =============================================================================
def enviar_email(dest, html, subject=None):
    """
    Roteia para Resend (se RESEND_API_KEY estiver configurado) ou SMTP do Gmail.
    Mantém a assinatura/retorno original (True/False).
    """
    if RESEND_API_KEY:
        return enviar_email_resend(dest, html, subject=subject)
    return enviar_email_smtp(dest, html, subject=subject)
