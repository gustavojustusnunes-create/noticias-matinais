import streamlit as st
import feedparser
import requests
import gspread
from google.oauth2.service_account import Credentials
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Importa constantes centralizadas do config.py
from config import (
    RSS_FEEDS as RSS_FEEDS_MAIN,
    FILTROS_TEMA as FILTROS_TEMA_MAIN,
    FALLBACK_IMAGES as FALLBACK_IMAGES_MAIN,
    SPORT_ROTATIONS as SPORT_ROTATIONS_MAIN,
    SPORT_KEYWORDS as SPORT_KEYWORDS_MAIN,
    FALLBACK_ESPORTES_GENERIC as FALLBACK_ESPORTES_GENERIC_MAIN,
    FEEDS_INGLES,
    ICONES_TEMA,
)

# =============================================================================
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
# =============================================================================
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None,
    }
)

# =============================================================================
# --- 2. CSS PREMIUM — OCULTA TUDO TÉCNICO DO STREAMLIT ---
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');

    /* ── OCULTAR ABSOLUTAMENTE TUDO DO STREAMLIT ── */
    #MainMenu                                  { display: none !important; }
    footer                                     { display: none !important; }
    header                                     { background: transparent !important; }
    .stDeployButton                            { display: none !important; }
    [data-testid="stToolbar"]                  { display: none !important; }
    [data-testid="stDecoration"]               { display: none !important; }
    [data-testid="stStatusWidget"]             { display: none !important; }
    [data-testid="manage-app-button"]          { display: none !important; }
    [data-testid="stToolbarActions"]           { display: none !important; }
    .viewerBadge_container__1QSob             { display: none !important; }
    .styles_viewerBadge__1yB5_                { display: none !important; }
    #stDecoration                              { display: none !important; }
    [class*="viewerBadge"]                    { display: none !important; }
    [class*="deployButton"]                   { display: none !important; }
    [class*="StatusWidget"]                   { display: none !important; }
    [class*="toolbar"]                        { display: none !important; }
    iframe[title="streamlit_analytics"]       { display: none !important; }
    .st-emotion-cache-zq5wmm                  { display: none !important; }
    .st-emotion-cache-1dp5vir                 { display: none !important; }
    .st-emotion-cache-18ni7ap                 { display: none !important; }
    /* Oculta todo rodapé de terceiros */
    [data-testid="stBottom"]                  { display: none !important; }
    .st-emotion-cache-uf99v8                  { display: none !important; }

    /* ── DESIGN PREMIUM ── */
    .stApp {
        background-color: #fdfbf7;
        font-family: 'Lora', serif;
        color: #2c2c2c;
    }

    h1 {
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        text-align: center;
        font-size: 3.5rem !important;
        letter-spacing: 2px;
        color: #0a5c5a !important;
        border-top: 2px solid #0a5c5a;
        border-bottom: 2px solid #0a5c5a;
        padding: 15px 0;
        margin-bottom: 20px;
    }
    h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #0a5c5a !important;
    }

    /* ── CARDS DE NOTÍCIA ── */
    .news-card {
        background-color: #ffffff;
        border: 1px solid #e5e3de;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .news-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(10, 92, 90, 0.15);
    }
    .news-img {
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-bottom: 3px solid #0a5c5a;
    }
    .news-content { padding: 20px; }
    .news-tag {
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: bold;
        background-color: #0a5c5a;
        color: #ffffff !important;
        padding: 4px 10px;
        border-radius: 4px;
        margin-bottom: 12px;
        display: inline-block;
    }
    .news-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 12px;
        display: block;
        color: #111 !important;
        text-decoration: none;
        line-height: 1.35;
    }
    .news-title:hover { color: #0a5c5a !important; }
    .news-source {
        font-size: 0.78rem;
        color: #0a5c5a;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-top: 1px solid #eee;
        padding-top: 10px;
        text-decoration: none;
        display: block;
    }
    .news-source:hover { opacity: 0.75; }

    /* ── ALERTAS ── */
    .alerta-erro {
        background-color: #fff0f0;
        border-left: 4px solid #cc0000;
        padding: 12px 16px;
        border-radius: 4px;
        color: #cc0000;
        font-size: 0.9rem;
        margin: 8px 0;
    }
    .alerta-sucesso {
        background-color: #f0fff4;
        border-left: 4px solid #0a5c5a;
        padding: 12px 16px;
        border-radius: 4px;
        color: #0a5c5a;
        font-size: 0.9rem;
        margin: 8px 0;
    }

    /* ── BOTÃO HAMBURGUER DO HEADER ── */
    header[data-testid="stHeader"] button {
        background-color: #0a5c5a !important;
        border-radius: 8px !important;
        border: 2px solid #0a5c5a !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        opacity: 1 !important;
        visibility: visible !important;
        margin-top: 10px !important;
        margin-left: 10px !important;
    }
    header[data-testid="stHeader"] button svg {
        fill: #ffffff !important;
        color: #ffffff !important;
        stroke: #ffffff !important;
        width: 20px !important;
        height: 20px !important;
    }
    header[data-testid="stHeader"] button:hover {
        background-color: #084c4a !important;
    }
    [data-testid="stSidebarHeader"] button {
        background-color: #fdfbf7 !important;
        border-radius: 8px !important;
        border: 2px solid #084c4a !important;
    }
    [data-testid="stSidebarHeader"] button svg {
        fill: #084c4a !important;
        color: #084c4a !important;
        stroke: #084c4a !important;
    }

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {
        background-color: #084c4a !important;
        border-right: none;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #fdfbf7 !important;
    }
    section[data-testid="stSidebar"] input {
        background-color: #fdfbf7 !important;
        color: #111 !important;
        border-radius: 5px !important;
        border: none !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #0a5c5a !important;
        font-size: 1.1rem !important;
        font-weight: bold;
        font-family: 'Playfair Display', serif;
    }
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #111111 !important;
        border: 2px solid #0a5c5a !important;
        border-radius: 5px;
    }
    div[data-baseweb="select"] span { color: #111111 !important; font-weight: bold; }

    /* Botões da sidebar */
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background-color: #0a5c5a !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button span,
    section[data-testid="stSidebar"] .stButton > button p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] button:hover,
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #084c4a !important;
        border-color: #ffffff !important;
        transform: scale(1.04);
    }
    /* Botão primário (Subscrever) */
    section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #fdfbf7 !important;
        color: #084c4a !important;
        border: 2px solid #fdfbf7 !important;
        font-size: 0.92rem !important;
        font-weight: 900 !important;
        margin-top: 6px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
    section[data-testid="stSidebar"] button[kind="primary"] p {
        color: #084c4a !important;
        font-weight: 900 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
        background-color: #e5e3de !important;
        border-color: #e5e3de !important;
    }

    [data-testid="stForm"] {
        border: 1px solid rgba(253, 251, 247, 0.2);
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        padding: 20px;
    }

    /* ── SELECTBOX PRINCIPAL ── */
    section[data-testid="stMain"] label[data-testid="stWidgetLabel"] p {
        color: #0a5c5a !important;
        font-size: 1rem !important;
        font-weight: bold;
        font-family: 'Playfair Display', serif;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 3. DADOS E FEEDS (constantes importadas de config.py) ---
# =============================================================================
RSS_FEEDS            = RSS_FEEDS_MAIN
FILTROS_TEMA         = FILTROS_TEMA_MAIN
FALLBACK_IMAGES      = FALLBACK_IMAGES_MAIN
SPORT_ROTATIONS      = SPORT_ROTATIONS_MAIN
SPORT_KEYWORDS       = SPORT_KEYWORDS_MAIN
FALLBACK_ESPORTES_GENERIC = FALLBACK_ESPORTES_GENERIC_MAIN


def traduzir_titulo_se_ingles(titulo, url_fonte=""):
    """
    Detecta se o título veio de feed em inglês e traduz via Claude Haiku.
    Usa FEEDS_INGLES de config.py para detecção precisa por URL de origem.
    Se a tradução falhar, retorna o título original sem prefixo.
    """
    if not titulo:
        return titulo

    # Detecção por URL de origem (precisa)
    e_ingles = url_fonte in FEEDS_INGLES if url_fonte else False

    # Detecção por vocabulário (fallback para o app onde não temos a URL)
    if not e_ingles:
        palavras_ingles = [
            "the ", "how to", "why ", "what ", "best ", "your ", "you ",
            "with ", "this ", "that ", " and ", " for ", " are ", " was ",
            "running", "workout", "training", "fitness", "marathon",
            "i ran", "i didn", "i found", " my ", "review:",
            "things no", "could benefit", "summer", "winter", "spring",
            "tried ", "defense", "softer", "faster", "better",
            "scared", "shorts", "pillow", "sleeper",
            "celebrity", "award", "season", "episode", "premiere",
        ]
        titulo_lower = titulo.lower()
        palavras_encontradas = sum(1 for p in palavras_ingles if p in titulo_lower)
        e_ingles = palavras_encontradas >= 2

    if not e_ingles:
        return titulo

    # Obtém chave Claude
    claude_key = ""
    try:
        claude_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.secrets.get("CLAUDE_KEY", "")
    except Exception:
        pass
    if not claude_key:
        import os
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("CLAUDE_KEY", "")

    if not claude_key:
        return titulo  # sem prefixo "🌐" — retorna original limpo

    try:
        prompt = (
            f"Traduza este título de artigo de inglês para português brasileiro, "
            f"mantendo o tom jornalístico e direto. "
            f"Retorne APENAS o título traduzido, sem aspas, sem explicação:\n\n{titulo}"
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         claude_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=10
        )
        if r.status_code == 200:
            traduzido = r.json()["content"][0]["text"].strip().strip('"\'`')
            if 5 < len(traduzido) < 250:
                return traduzido
    except Exception:
        pass
    return titulo  # fallback: original sem modificação

# =============================================================================
# --- 4. VALIDAÇÕES ---
# =============================================================================
def validar_email(email):
    padrao = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(padrao, email.strip()))

def validar_nome(nome):
    return len(nome.strip()) >= 2

# =============================================================================
# --- 5. GOOGLE SHEETS ---
# =============================================================================
@st.cache_data(ttl=300)
def conectar_planilha():
    if "GCP_JSON" not in st.secrets:
        return None
    try:
        creds_dict = json.loads(st.secrets["GCP_JSON"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        # Abre pelo ID (se disponível) ou pelo nome
        sheet_id = st.secrets.get("GOOGLE_SHEETS_ID", "")
        if sheet_id:
            return client.open_by_key(sheet_id).sheet1
        return client.open("noticias_db").sheet1
    except Exception:
        return None

def email_ja_cadastrado(email):
    sheet = conectar_planilha()
    if not sheet:
        return False
    try:
        registros = sheet.get_all_records()
        emails_existentes = [r.get("Email", "").strip().lower() for r in registros]
        return email.strip().lower() in emails_existentes
    except Exception:
        return False

def salvar_assinante(nome, email, ordem_temas):
    sheet = conectar_planilha()
    if not sheet:
        return False, "Não foi possível conectar. Por favor, tente novamente em alguns instantes."
    try:
        linha = [nome.strip(), email.strip()]
        for chave in RSS_FEEDS.keys():
            linha.append(ordem_temas.get(chave, "Não"))
        sheet.append_row(linha)
        return True, "Sucesso"
    except Exception as e:
        return False, "Ocorreu um problema ao registar a sua inscrição. Por favor, tente novamente."

def cancelar_assinatura(email):
    """Marca o assinante como inativo na planilha (coluna 'ativo' ou remove)."""
    sheet = conectar_planilha()
    if not sheet:
        return False, "Não foi possível conectar. Tente novamente em alguns instantes."
    try:
        email = email.strip().lower()
        registros = sheet.get_all_records()
        todas_linhas = sheet.get_all_values()

        # Localiza o email na planilha (coluna "Email" = índice 1, base 0)
        for i, linha in enumerate(todas_linhas):
            if not linha:
                continue
            email_linha = str(linha[1] if len(linha) > 1 else linha[0]).strip().lower()
            if email_linha == email:
                # Sobrescreve todos os temas com "Não" (desativa todos os cadernos)
                num_cols = len(todas_linhas[0]) if todas_linhas else 10
                for col_idx in range(2, num_cols):
                    sheet.update_cell(i + 1, col_idx + 1, "Não")
                return True, "A sua assinatura foi cancelada com sucesso. Lamentamos vê-lo partir!"

        return False, "E-mail não encontrado na nossa lista de assinantes."
    except Exception as e:
        return False, "Ocorreu um erro ao processar o cancelamento. Tente novamente."

# =============================================================================
# --- 6. E-MAIL DE BOAS-VINDAS ---
# =============================================================================
def enviar_boas_vindas(nome, email_dest, temas_escolhidos):
    try:
        email_sender   = st.secrets.get("EMAIL_USER")
        # Suporta EMAIL_PASS (novo) e EMAIL_PASSWORD (legado)
        email_password = st.secrets.get("EMAIL_PASS") or st.secrets.get("EMAIL_PASSWORD")
        if not email_sender or not email_password:
            return

        temas_html = "".join(
            f"<li style='padding:4px 0; color:#2c2c2c;'>✅ {t}</li>"
            for t in temas_escolhidos
        )

        html = f"""
        <html><body style="margin:0; padding:0; background-color:#e5e3de; font-family:'Lora','Times New Roman',serif;">
          <div style="max-width:560px; margin:30px auto; background:#fdfbf7; border-radius:8px; overflow:hidden; box-shadow:0 4px 15px rgba(0,0,0,0.07);">
            <div style="padding:30px 20px; text-align:center; border-bottom:2px solid #0a5c5a;">
              <p style="margin:0 0 6px; font-size:10px; letter-spacing:3px; text-transform:uppercase; color:#999;">Edição Premium Digital</p>
              <h1 style="margin:0; font-family:'Playfair Display',Georgia,serif; font-size:28px; text-transform:uppercase; letter-spacing:2px; color:#0a5c5a;">ALL NEWS JOURNAL</h1>
              <p style="margin:8px 0 0; font-size:12px; color:#777; font-style:italic;">Inscrição confirmada com sucesso</p>
            </div>
            <div style="padding:30px 25px;">
              <p style="font-size:17px; color:#2c2c2c;">Olá, <b>{nome}</b>! 👋</p>
              <p style="font-size:15px; color:#444; line-height:1.7;">
                A sua inscrição no <b>All News Journal</b> foi confirmada com sucesso.<br>
                A partir de amanhã cedo, receberá a sua edição personalizada com os seguintes cadernos:
              </p>
              <ul style="font-size:15px; padding-left:20px; line-height:1.8;">
                {temas_html}
              </ul>
            </div>
            <div style="text-align:center; padding:20px; background-color:#084c4a; color:#fdfbf7; font-size:12px;">
              <p style="margin:0; font-weight:bold; font-size:13px; letter-spacing:1px;">ALL NEWS JOURNAL</p>
              <p style="margin:8px 0 0; font-size:10px; opacity:0.7;">© {datetime.now().year} All News Journal Group. Conteúdo Premium.</p>
            </div>
          </div>
        </body></html>
        """

        msg = MIMEMultipart()
        msg['Subject'] = "📰 Bem-vindo ao All News Journal!"
        msg['From']    = f"All News Journal <{email_sender}>"
        msg['To']      = email_dest
        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        server.sendmail(email_sender, email_dest, msg.as_string())
        server.quit()
    except Exception:
        pass

# =============================================================================
# --- 7. BUSCA DE IMAGEM ---
# =============================================================================
def buscar_og_image(url_artigo, timeout=8):
    if not url_artigo:
        return None
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        r = requests.get(url_artigo, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        html = r.text
        padroes = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        ]
        for padrao in padroes:
            match = re.search(padrao, html, re.IGNORECASE)
            if match:
                img_url = match.group(1).strip().replace('&amp;', '&')
                if img_url.startswith('http') and len(img_url) > 15:
                    return img_url
    except Exception:
        pass
    return None

# =============================================================================
# --- 8. BUSCA DE NOTÍCIAS ---
# =============================================================================
@st.cache_data(ttl=600)
def buscar_noticias(tema):
    urls = RSS_FEEDS.get(tema, [])
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    TEMAS_MULTI_FONTE = {"Cinema", "Fitness", "Ciencia", "Esportes", "Motos"}
    filtros = FILTROS_TEMA.get(tema, [])

    entries = []
    vistos = set()

    if tema in TEMAS_MULTI_FONTE:
        for url in urls:
            try:
                f = feedparser.parse(url)
                for e in f.entries:
                    link = e.get('link', '')
                    if link not in vistos:
                        vistos.add(link)
                        entries.append(e)
            except Exception:
                continue
    else:
        for url in urls:
            try:
                f = feedparser.parse(url)
                if f.entries:
                    entries = list(f.entries)
                    break
            except Exception:
                continue

    if not entries:
        return []

    # Aplica filtros
    entries_filtradas = []
    for entry in entries:
        titulo = entry.get('title', '').lower()
        link   = entry.get('link', '').lower()
        if filtros and any(p in titulo or p in link for p in filtros):
            continue
        entries_filtradas.append(entry)
        if len(entries_filtradas) >= 6:
            break

    if not entries_filtradas:
        return []

    noticias = []
    for entry in entries_filtradas:
        img = None

        # Tenta og:image primeiro (para todos os temas)
        og = buscar_og_image(entry.get('link', ''))
        if og:
            img = og

        # media_content
        if not img and 'media_content' in entry:
            for m in entry.media_content:
                if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                    img = m['url']
                    break

        # enclosures
        if not img and 'enclosures' in entry:
            for enc in entry.enclosures:
                url_enc = enc.get('url', '')
                if any(ext in url_enc.lower() for ext in extensoes):
                    img = url_enc
                    break

        # links com type image
        if not img and 'links' in entry:
            for l in entry.links:
                href = l.get('href', '')
                if l.get('type', '').startswith('image/') and any(ext in href.lower() for ext in extensoes):
                    img = href
                    break

        # scraping de <img> no summary/content
        if not img:
            txt = ""
            if 'content' in entry:
                for c in entry.content:
                    txt += c.value
            if 'summary' in entry:
                txt += entry.summary
            matches = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', txt)
            for u in matches:
                if any(ext in u.lower() for ext in extensoes) and "pixel" not in u and "doubleclick" not in u:
                    img = u
                    break

        # Fallback por tema
        if not img:
            if tema == "Esportes":
                titulo_lower = entry.get('title', '').lower()
                categoria = None
                for cat, kws in SPORT_KEYWORDS.items():
                    if any(kw in titulo_lower for kw in kws):
                        categoria = cat
                        break
                if categoria and categoria in SPORT_ROTATIONS:
                    idx = ord(titulo_lower[0]) % len(SPORT_ROTATIONS[categoria])
                    img = SPORT_ROTATIONS[categoria][idx]
                else:
                    img = FALLBACK_ESPORTES_GENERIC[len(noticias) % len(FALLBACK_ESPORTES_GENERIC)]
            else:
                img = FALLBACK_IMAGES.get(
                    tema,
                    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
                )

        titulo_final = entry.get('title', '')
        if tema == "Fitness":
            titulo_final = traduzir_titulo_se_ingles(titulo_final)

        noticias.append({
            "titulo": titulo_final,
            "link":   entry.get('link', ''),
            "img":    img,
        })

    return noticias

# =============================================================================
# --- 9. SIDEBAR: FORMULÁRIO ---
# =============================================================================
ICONES = {
    "Mundo":    "🌎", "Mercado":  "📈", "Politica": "🏛️",
    "Tech":     "💻", "Esportes": "🏎️", "Cinema":   "🎬",
    "Fitness":  "🏃", "Ciencia":  "🔬", "Motos":    "🏍️",
    "Fofoca":   "⭐",
}

if "ordem_lista" not in st.session_state:
    st.session_state.ordem_lista = list(RSS_FEEDS.keys())
if "ativos" not in st.session_state:
    st.session_state.ativos = {t: True for t in RSS_FEEDS.keys()}

with st.sidebar:
    st.markdown(
        "<h2 style='text-align:center; font-family: Playfair Display; margin-bottom:4px;'>✍️ Junte-se ao Clube</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center; font-size: 0.88rem; opacity:0.9;'>Receba a nossa curadoria premium "
        "de notícias todas as manhãs, gratuitamente.</p>",
        unsafe_allow_html=True
    )
    st.write("")

    nome  = st.text_input("O seu Nome",          key="inp_nome")
    email = st.text_input("O seu melhor E-mail", key="inp_email")

    st.markdown("<hr style='border-color: rgba(253, 251, 247, 0.2);'>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:0.82rem; font-weight:bold; margin-bottom:2px;'>"
        "📋 Escolha e ordene os seus cadernos:</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='font-size:0.75rem; opacity:0.75; margin-top:0; margin-bottom:10px;'>"
        "Use ↑↓ para ordenar. Desmarque os que não quer receber.</p>",
        unsafe_allow_html=True
    )

    lista = st.session_state.ordem_lista

    for i, tema in enumerate(lista):
        icone = ICONES.get(tema, "📰")
        col_chk, col_up, col_dn = st.columns([5, 1, 1])

        ativo = col_chk.checkbox(
            f"{icone} {tema}",
            value=st.session_state.ativos.get(tema, True),
            key=f"chk_{tema}"
        )
        st.session_state.ativos[tema] = ativo

        if i > 0:
            if col_up.button("↑", key=f"up_{tema}", use_container_width=True):
                lista[i], lista[i - 1] = lista[i - 1], lista[i]
                st.rerun()
        else:
            col_up.write("")

        if i < len(lista) - 1:
            if col_dn.button("↓", key=f"dn_{tema}", use_container_width=True):
                lista[i], lista[i + 1] = lista[i + 1], lista[i]
                st.rerun()
        else:
            col_dn.write("")

    temas_ativos_preview = [
        t for t in st.session_state.ordem_lista
        if st.session_state.ativos.get(t, True)
    ]
    if temas_ativos_preview:
        preview_txt = " → ".join(f"{ICONES.get(t,'📰')}{t}" for t in temas_ativos_preview)
        st.markdown(
            f"<p style='font-size:0.70rem; opacity:0.65; text-align:center; "
            f"font-style:italic; margin-top:8px;'>📧 Ordem no e-mail:<br>{preview_txt}</p>",
            unsafe_allow_html=True
        )

    st.write("")

    ordem_temas = {}
    pos = 1
    for tema in st.session_state.ordem_lista:
        if st.session_state.ativos.get(tema, True):
            ordem_temas[tema] = pos
            pos += 1
        else:
            ordem_temas[tema] = "Não"

    if st.button("ASSINAR AGORA — É GRATUITO 🗞️", use_container_width=True, key="btn_subscribe", type="primary"):
        erros = []

        if not validar_nome(nome):
            erros.append("Por favor, informe um nome válido (mínimo 2 caracteres).")
        if not email:
            erros.append("Por favor, informe o seu e-mail.")
        elif not validar_email(email):
            erros.append("O e-mail informado não é válido. Verifique e tente novamente.")

        temas_selecionados = [t for t, v in ordem_temas.items() if v != "Não"]
        if not temas_selecionados:
            erros.append("Selecione pelo menos um caderno para receber.")

        if erros:
            for erro in erros:
                st.warning(erro)
        else:
            with st.spinner("A verificar o seu cadastro..."):
                if email_ja_cadastrado(email):
                    st.info("📬 Este e-mail já está inscrito! Já faz parte do clube.")
                else:
                    with st.spinner("A registar a sua inscrição..."):
                        ok, mensagem = salvar_assinante(nome, email, ordem_temas)
                        if ok:
                            temas_ordenados = sorted(
                                temas_selecionados,
                                key=lambda t: ordem_temas[t]
                            )
                            enviar_boas_vindas(nome, email, temas_ordenados)
                            st.success("✅ Inscrição confirmada! Verifique o seu e-mail — enviamos uma mensagem de boas-vindas.")
                            st.balloons()
                            st.session_state.ordem_lista = list(RSS_FEEDS.keys())
                            st.session_state.ativos = {t: True for t in RSS_FEEDS.keys()}
                        else:
                            st.error(f"❌ {mensagem}")

    # ── Seção de cancelamento ──────────────────────────────────────────────
    st.markdown("<hr style='border-color:rgba(253,251,247,0.15);margin:20px 0 12px;'>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:0.78rem;opacity:0.7;text-align:center;margin-bottom:8px;'>"
        "Deseja cancelar sua assinatura?</p>",
        unsafe_allow_html=True
    )

    # Detecta parâmetro ?acao=cancelar na URL
    params = st.query_params
    mostrar_cancelamento = params.get("acao", "") == "cancelar"

    if "mostrar_cancelamento" not in st.session_state:
        st.session_state.mostrar_cancelamento = mostrar_cancelamento

    if st.button("Cancelar minha assinatura", key="btn_cancelar_toggle", use_container_width=True):
        st.session_state.mostrar_cancelamento = not st.session_state.get("mostrar_cancelamento", False)
        st.rerun()

    if st.session_state.get("mostrar_cancelamento", False):
        with st.form("form_cancelamento", clear_on_submit=True):
            email_cancel = st.text_input("Seu e-mail cadastrado", key="inp_email_cancel",
                                          placeholder="seuemail@exemplo.com")
            confirmar = st.checkbox("Confirmo que desejo cancelar minha assinatura")
            btn_cancelar = st.form_submit_button("Confirmar cancelamento")

        if btn_cancelar:
            if not email_cancel:
                st.warning("Por favor, informe o seu e-mail.")
            elif not validar_email(email_cancel):
                st.warning("E-mail inválido. Verifique e tente novamente.")
            elif not confirmar:
                st.warning("Marque a caixa de confirmação para continuar.")
            else:
                with st.spinner("Processando..."):
                    ok, msg_cancel = cancelar_assinatura(email_cancel)
                    if ok:
                        st.success(f"✅ {msg_cancel}")
                    else:
                        st.error(f"❌ {msg_cancel}")

# =============================================================================
# --- 10. META TAGS SEO ---
# =============================================================================
st.markdown("""
<meta property="og:title" content="All News Journal — Curadoria Premium de Notícias">
<meta property="og:description" content="Receba as notícias que importam, todas as manhãs. Gratuito.">
<meta property="og:type" content="website">
<meta name="description" content="All News Journal — curadoria premium e automatizada das notícias do dia. 10 cadernos temáticos. Gratuito.">
""", unsafe_allow_html=True)

# =============================================================================
# --- 11. CONTEÚDO PRINCIPAL ---
# =============================================================================
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

hoje = datetime.now()
meses       = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
dias_semana = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]
data_ptbr = f"{dias_semana[hoje.weekday()]}, {hoje.day} de {meses[hoje.month-1]} de {hoje.year}"

col_date, col_loc = st.columns(2)
col_date.markdown(
    f"<div style='text-align:center; color:#0a5c5a; font-weight:bold; padding:5px;'>📅 {data_ptbr}</div>",
    unsafe_allow_html=True
)
col_loc.markdown(
    "<div style='text-align:center; color:#0a5c5a; font-weight:bold; padding:5px;'>🌎 Edição Global · Digital</div>",
    unsafe_allow_html=True
)

# ── Contador de assinantes ────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def obter_total_assinantes():
    sheet = conectar_planilha()
    if not sheet:
        return 0
    try:
        registros = sheet.get_all_records()
        return sum(
            1 for r in registros
            if any(str(r.get(t, "")).strip().isdigit() for t in RSS_FEEDS)
        )
    except Exception:
        return 0

total_assinantes = obter_total_assinantes()
if total_assinantes > 0:
    st.markdown(
        f"<div style='text-align:center;padding:8px;color:#0a5c5a;font-size:0.88rem;'>"
        f"📊 <b>{total_assinantes}</b> leitores já recebem nossa curadoria</div>",
        unsafe_allow_html=True
    )

st.write("")

tema_atual = st.selectbox("📖 Selecione o Caderno:", ["Capa (Destaques)"] + list(RSS_FEEDS.keys()))
st.markdown("<br>", unsafe_allow_html=True)

noticias_display = []

if tema_atual == "Capa (Destaques)":
    for t in RSS_FEEDS.keys():
        res = buscar_noticias(t)
        if res:
            item = res[0]
            item['tema'] = t
            noticias_display.append(item)
else:
    res = buscar_noticias(tema_atual)
    if not res:
        st.warning(f"⚠️ As notícias de **{tema_atual}** estão temporariamente indisponíveis. Por favor, tente novamente em alguns minutos.")
    for item in res:
        item['tema'] = tema_atual
        noticias_display.append(item)

if noticias_display:
    cols = st.columns(3)
    for i, n in enumerate(noticias_display):
        col = cols[i % 3]
        with col:
            st.markdown(f"""
            <div class="news-card">
                <a href="{n['link']}" target="_blank" rel="noopener noreferrer">
                    <img src="{n['img']}" class="news-img"
                         onerror="this.src='{FALLBACK_IMAGES.get(n['tema'], 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop')}'">
                </a>
                <div class="news-content">
                    <span class="news-tag">{n['tema']}</span>
                    <a href="{n['link']}" target="_blank" rel="noopener noreferrer" class="news-title">{n['titulo']}</a>
                    <a href="{n['link']}" target="_blank" rel="noopener noreferrer" class="news-source">Ler na fonte original →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
elif not noticias_display and tema_atual == "Capa (Destaques)":
    st.info("A carregar as manchetes mais recentes...")

# ── Seção "Sobre" ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 Sobre o All News Journal"):
    st.markdown("""
**Missão:** Curadoria premium e gratuita das notícias que importam — filtradas, resumidas e entregues diretamente no seu e-mail todas as manhãs.

**Frequência:** Edição diária enviada às **6h da manhã** (horário de Brasília), de segunda a domingo.

**Cadernos disponíveis:**

| Caderno | Foco |
|---|---|
| 🌎 Mundo | Geopolítica e eventos internacionais |
| 📈 Mercado | Economia, investimentos e finanças |
| 🏛️ Política | Brasil: Congresso, governo e Judiciário |
| 💻 Tech | Tecnologia, IA e inovação |
| 🏎️ Esportes | F1, NBA, MMA, Tênis (sem futebol) |
| 🎬 Cinema | Filmes, séries e streaming |
| 🏃 Fitness | Treino, corrida, nutrição e performance |
| 🔬 Ciência | Descobertas científicas e saúde |
| 🏍️ Motos | Motociclismo e novidades do segmento |
| ⭐ Fofoca | Celebridades internacionais e Hollywood |

**100% automatizado com inteligência artificial** — Claude AI (Anthropic) gera resumos jornalísticos de 85 a 105 palavras por notícia, em Português Brasileiro.
    """)

# Rodapé profissional
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='
        border-top: 2px solid #0a5c5a;
        padding: 25px 0 10px;
        text-align: center;
        color: #0a5c5a;
        font-family: Playfair Display, serif;
    '>
        <p style='font-size:1.1rem; font-weight:bold; letter-spacing:2px; margin:0;'>ALL NEWS JOURNAL</p>
        <p style='font-size:0.75rem; color:#888; margin:8px 0 0;'>
            © """ + str(datetime.now().year) + """ All News Journal Group &nbsp;·&nbsp; Conteúdo Premium Digital &nbsp;·&nbsp; Edição Global
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
