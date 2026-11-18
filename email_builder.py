"""
email_builder.py — Geração do HTML e envio de email do All News Journal
Inclui: painel financeiro, preheader, sumário, editorial, tempo de leitura (2-3 min),
        renderização visual das pílulas dos 4 Blocos Universais (Gancho, O Fato,
        Caixa '💰 Como isso afeta você' e Pergunta do Dia), subject dinâmico e retry com backoff.
"""
import base64
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import yfinance as yf
except ImportError:
    yf = None

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
    if yf is None:
        return ""
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
# --- RENDERIZADOR DOS 4 BLOCOS UNIVERSAIS (MANUAL EDITORIAL JOVEM) ---
# =============================================================================
def extrair_4_blocos_de_item(n: dict) -> dict:
    """
    Extrai ou converte uma notícia em estrutura de 4 blocos universais:
    - bloco_1_gancho
    - bloco_2_fato
    - bloco_3_e_dai
    - bloco_4_fechamento
    """
    blocos_src = n.get("draft_blocks") if isinstance(n.get("draft_blocks"), dict) else n
    g = (blocos_src.get("bloco_1_gancho") or "").strip()
    f = (blocos_src.get("bloco_2_fato") or "").strip()
    e = (blocos_src.get("bloco_3_e_dai") or "").strip()
    c = (blocos_src.get("bloco_4_fechamento") or "").strip()

    if g and f and e and c:
        return {
            "bloco_1_gancho": g,
            "bloco_2_fato": f,
            "bloco_3_e_dai": e,
            "bloco_4_fechamento": c,
        }

    resumo_raw = (n.get("resumo") or "").strip()
    partes = [p.strip() for p in resumo_raw.replace("\n", " ").split(". ") if p.strip()]
    gancho_fb = (partes[0] + ".") if partes else n.get("titulo", "Destaque do dia.")
    fato_fb = ". ".join(partes[1:3]) + "." if len(partes) > 1 else resumo_raw
    edai_fb = (
        partes[3] + "."
        if len(partes) > 3
        else "Isso impacta diretamente os custos, investimentos e decisões práticas do seu dia a dia."
    )
    fechamento_fb = "Como você enxerga esse movimento na sua rotina e no seu bolso?"
    return {
        "bloco_1_gancho": g or gancho_fb,
        "bloco_2_fato": f or fato_fb,
        "bloco_3_e_dai": e or edai_fb,
        "bloco_4_fechamento": c or fechamento_fb,
    }


def renderizar_blocos_noticia_html(n: dict, cor: str = "0a5c5a") -> str:
    """
    Renderiza visualmente as pílulas dos 4 Blocos Universais no HTML do e-mail:
    1. Gancho em destaque
    2. O Fato
    3. Caixa '💰 Como isso afeta você'
    4. Pergunta do Dia
    """
    blocos = extrair_4_blocos_de_item(n)
    return f"""
        <!-- BLOCO 1: GANCHO EM DESTAQUE -->
        <div style="margin:0 0 12px;padding:10px 14px;background-color:#{cor}12;border-left:4px solid #{cor};border-radius:0 6px 6px 0;">
          <span style="display:inline-block;font-size:10px;font-weight:bold;text-transform:uppercase;letter-spacing:1.2px;color:#{cor};font-family:sans-serif;margin-bottom:3px;">
            ⚡ Gancho em Destaque
          </span>
          <p style="margin:0;font-size:15px;font-weight:bold;color:#111;line-height:1.45;font-family:'Lora','Times New Roman',serif;">
            {blocos['bloco_1_gancho']}
          </p>
        </div>

        <!-- BLOCO 2: O FATO -->
        <div style="margin:0 0 14px;">
          <span style="display:inline-block;background-color:#e5e3de;color:#333;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-family:sans-serif;margin-bottom:6px;">
            📊 O Fato
          </span>
          <p style="margin:0;font-size:15px;color:#2c2c2c;line-height:1.7;font-family:'Lora','Times New Roman',serif;">
            {blocos['bloco_2_fato']}
          </p>
        </div>

        <!-- BLOCO 3: CAIXA '💰 COMO ISSO AFETA VOCÊ' -->
        <div style="margin:0 0 14px;padding:14px 16px;background-color:#f0f7f6;border:1px solid #{cor}44;border-radius:8px;">
          <p style="margin:0 0 5px;font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#0a5c5a;font-family:sans-serif;">
            💰 Como isso afeta você
          </p>
          <p style="margin:0;font-size:14px;color:#1f2937;line-height:1.6;font-family:'Lora','Times New Roman',serif;">
            {blocos['bloco_3_e_dai']}
          </p>
        </div>

        <!-- BLOCO 4: PERGUNTA DO DIA -->
        <div style="margin:0 0 16px;padding:10px 14px;background-color:#faf6eb;border:1px dashed #c9a84c;border-radius:8px;">
          <span style="font-size:11px;font-weight:bold;color:#926c15;text-transform:uppercase;letter-spacing:1px;font-family:sans-serif;">
            💬 Pergunta do Dia:
          </span>
          <span style="font-size:14px;color:#333;font-style:italic;font-family:'Lora','Times New Roman',serif;">
            {blocos['bloco_4_fechamento']}
          </span>
        </div>
    """


def formatar_newsletter_4_blocos(story: dict, draft_blocks: dict) -> dict:
    """
    Subagente formatador de E-mail HTML para o node_multichannel_fanout.
    Constrói o item enriquecido com os 4 blocos e retorna o HTML completo da newsletter
    com tempo de leitura de 2-3 minutos.
    """
    tema = story.get("caderno") or story.get("tema") or "Economia"
    item_enriquecido = {
        "titulo": draft_blocks.get("titulo_jovem") or story.get("titulo", "Destaque do Dia"),
        "link": story.get("link", "https://noticias-matinais.vercel.app"),
        "imagem": story.get("imagem") or story.get("url_imagem") or "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=1200",
        "resumo": " ".join([
            draft_blocks.get("bloco_1_gancho", ""),
            draft_blocks.get("bloco_2_fato", ""),
            draft_blocks.get("bloco_3_e_dai", ""),
            draft_blocks.get("bloco_4_fechamento", ""),
        ]).strip(),
        "draft_blocks": draft_blocks,
        "bloco_1_gancho": draft_blocks.get("bloco_1_gancho", ""),
        "bloco_2_fato": draft_blocks.get("bloco_2_fato", ""),
        "bloco_3_e_dai": draft_blocks.get("bloco_3_e_dai", ""),
        "bloco_4_fechamento": draft_blocks.get("bloco_4_fechamento", ""),
    }
    dados_edicao = {tema: [item_enriquecido]}
    html_completo = gerar_html_final("Leitor(a)", dados_edicao, painel="")
    card_html = renderizar_blocos_noticia_html(item_enriquecido)
    return {
        "channel": "email_newsletter",
        "reading_time_minutes": 2,
        "subject": montar_subject(dados_edicao),
        "card_4_blocks_html": card_html,
        "full_html": html_completo,
    }


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
    - Pílulas visuais dos 4 Blocos Universais (Gancho, O Fato, 💰 Como isso afeta você, Pergunta do Dia)
    - Tempo de leitura estimado (2-3 min)
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

    # ── Tempo de leitura (calibrado para 2-3 min conforme JTBD) ──────────────
    total_palavras = sum(
        len(n.get("resumo", "").split())
        for items in dados.values() if items
        for n in items
    )
    if coluna_autor:
        total_palavras += len(coluna_autor.get("texto", "").split())
    tempo_leitura = min(3, max(2, round(total_palavras / 200))) if total_palavras > 0 else 2

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
        f"{manchete_principal} — Sua curadoria matinal em até 3 minutos no All News Journal"
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
      Edição Digital Matinal • 18–30 Anos
    </p>
    <img src="cid:{LOGO_CID}" alt="All News Journal"
         width="90" height="90"
         style="display:block;margin:0 auto 14px;width:90px;height:90px;border-radius:50%;">
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:36px;
               text-transform:uppercase;letter-spacing:3px;color:#{TURQUESA};">
      ALL NEWS JOURNAL
    </h1>
    <p style="margin:10px 0 4px;font-size:12px;color:#777;font-style:italic;">{data_ptbr}</p>
    <p style="margin:0;font-size:11px;color:#999;">⏱️ Leitura rápida: {tempo_leitura} min (sem ansiedade)</p>
  </div>

  <!-- PAINEL FINANCEIRO -->
  {painel}

  <!-- SAUDAÇÃO + EDITORIAL -->
  <div style="padding:30px 30px 10px;">
    <p style="color:#555;font-size:15px;text-align:center;margin-bottom:{'20px' if editorial else '35px'};
              font-style:italic;border-bottom:{'none' if editorial else '1px solid #e5e3de'};padding-bottom:{'10px' if editorial else '25px'};">
      Bom dia, <b style="color:#{TURQUESA};">{nome}</b>. O que realmente importa para o seu bolso, carreira e rotina hoje.
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
        O All News Journal também está em formato de áudio. Ana e Leo comentam as principais notícias do dia.
      </p>
      <a href="https://allnewsjournal.streamlit.app/?edicao={datetime.now().strftime('%Y-%m-%d')}"
         style="display:inline-block;background-color:#ffffff;color:#0a5c5a;padding:12px 28px;
                border-radius:24px;text-decoration:none;font-weight:bold;font-size:15px;box-shadow:0 2px 5px rgba(0,0,0,0.15);">
        🎧 Ouvir Podcast no Site &rarr;
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

    # ── Cadernos (com Pílulas Visuais dos 4 Blocos) ──────────────────────────
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
            onerror_script = (
                f"this.onerror=null;"
                f"this.style.background='linear-gradient(135deg, #{cor}22, #{cor}55)';"
                f"this.style.height='120px';"
                f"this.src='data:image/svg+xml;base64,"
                f"PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MCA2MCI+"
                f"PHRleHQgeT0iLjllbSIgZm9udC1zaXplPSI1MCI+e2ljb25lX2I2NH08L3RleHQ+PC9zdmc+"
                f"';"
            )
            blocos_html = renderizar_blocos_noticia_html(n, cor=cor)

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
        {blocos_html}
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
            if isinstance(resp, dict) and resp.get("id"):
                return True
            raise RuntimeError(f"resposta inesperada do Resend: {resp!r}")

        except Exception as e:
            msg_err = str(e).lower()
            if "attachments" in payload and any(
                t in msg_err for t in ("attachment", "content_id", "validation_error")
            ):
                print("      ⚠️ Anexo da logo recusado — reenviando sem a logo.")
                payload.pop("attachments", None)
                continue

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
            return False
        except smtplib.SMTPRecipientsRefused:
            print(f"      ❌ Destinatário recusado: {dest}")
            return False
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
