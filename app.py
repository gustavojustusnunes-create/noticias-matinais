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
    ORDEM_CADERNOS,
)

# =============================================================================
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
# =============================================================================
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed",  # Garante que a sidebar nasça morta
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None,
    }
)

# =============================================================================
# --- AUTO-EMBED + NUKER DE BRANDING DO STREAMLIT CLOUD ---
# Forçando embed=true via redirect, o wrapper do Streamlit esconde a maior
# parte do chrome. O nuker JS varre o DOM e remove qualquer elemento que
# sobreviva (links streamlit.io, badges, host menus, etc.).
# =============================================================================
st.markdown("""
<script>
(function() {
    try {
        var params = new URLSearchParams(window.location.search);
        if (params.get('embed') !== 'true') {
            params.set('embed', 'true');
            params.set('embed_options', 'show_padding');
            var newUrl = window.location.pathname + '?' + params.toString() + window.location.hash;
            window.location.replace(newUrl);
        }
    } catch (e) { console.warn('embed redirect skipped:', e); }
})();

function nukeStreamlitChrome() {
    try {
        var seletores = [
            'a[href*="streamlit.io"]',
            'a[href*="share.streamlit"]',
            'iframe[src*="streamlit.io"]',
            'iframe[title*="streamlit" i]',
            '[data-testid*="HostMenu"]',
            '[data-testid*="ProfileBadge"]',
            '[data-testid*="HostBadge"]',
            '[data-testid*="ViewerBadge"]',
            '[data-testid*="stToolbarAvatar"]',
            '[data-testid*="stAppDeployButton"]',
            '[data-testid*="stStatusWidget"]',
            '[class*="viewerBadge"]',
            '[class*="ViewerBadge"]',
            '[class*="HostBadge"]',
            '[class*="HostMenu"]',
            '[class*="StreamlitBadge"]'
        ];
        seletores.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
            });
        });
    } catch(e) {}
}
nukeStreamlitChrome();
window.addEventListener('load', nukeStreamlitChrome);
setInterval(nukeStreamlitChrome, 1500);
</script>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. CSS PREMIUM — OCULTA TUDO TÉCNICO DO STREAMLIT ---
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');

    /* ── OCULTAR ABSOLUTAMENTE TUDO DO STREAMLIT ── */
    #MainMenu, footer, header, .stDeployButton,
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], [data-testid="manage-app-button"],
    [data-testid="stToolbarActions"], [class*="viewerBadge"],
    [class*="deployButton"], [data-testid="stBottom"],
    iframe[title="streamlit_analytics"] {
        display: none !important;
    }

    /* Remove a barra lateral totalmente */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* NÃO usar :last-child aqui — Streamlit reorganiza o DOM e o último
       filho pode acabar sendo o conteúdo principal, escondendo tudo.
       A remoção de badges/avatares é feita pelo JS nukeStreamlitChrome
       acima, que cata por seletores específicos. */

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
    h2, h3 { font-family: 'Playfair Display', serif; color: #0a5c5a !important; }

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
    .news-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(10, 92, 90, 0.15); }
    .news-img { width: 100%; height: 180px; object-fit: cover; border-bottom: 3px solid #0a5c5a; }
    .news-content { padding: 20px; }
    .news-tag {
        font-size: 0.70rem; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;
        background-color: #0a5c5a; color: #ffffff !important; padding: 4px 10px;
        border-radius: 4px; margin-bottom: 12px; display: inline-block;
    }
    .news-title {
        font-family: 'Playfair Display', serif; font-size: 1.1rem; font-weight: 700;
        margin-bottom: 12px; display: block; color: #111 !important; text-decoration: none; line-height: 1.35;
    }
    .news-title:hover { color: #0a5c5a !important; }
    .news-source {
        font-size: 0.78rem; color: #0a5c5a; font-weight: bold; text-transform: uppercase;
        letter-spacing: 0.5px; border-top: 1px solid #eee; padding-top: 10px; text-decoration: none; display: block;
    }
    .news-source:hover { opacity: 0.75; }

    /* ── SELECTBOX E BOTÃO PRIMÁRIO ── */
    section[data-testid="stMain"] label[data-testid="stWidgetLabel"] p {
        color: #0a5c5a !important; font-size: 1rem !important; font-weight: bold; font-family: 'Playfair Display', serif;
    }
    section[data-testid="stMain"] button[kind="primary"] {
        background: linear-gradient(135deg, #0a5c5a 0%, #084c4a 100%) !important;
        color: #fdfbf7 !important; border: 2px solid #fdfbf7 !important; border-radius: 10px !important;
        padding: 14px 20px !important; font-family: 'Playfair Display', serif !important; font-size: 1.05rem !important;
        font-weight: bold !important; letter-spacing: 0.5px !important; box-shadow: 0 4px 14px rgba(10, 92, 90, 0.3) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    section[data-testid="stMain"] button[kind="primary"]:hover {
        background: linear-gradient(135deg, #084c4a 0%, #063838 100%) !important;
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(10, 92, 90, 0.45) !important;
    }
    section[data-testid="stMain"] button[kind="primary"] p { color: #fdfbf7 !important; font-weight: bold !important; }

    /* ── BOTÕES SECUNDÁRIOS DO RODAPÉ (estilo link) ── */
    section[data-testid="stMain"] [data-testid="stBaseButton-secondary"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #888 !important;
        font-family: 'Lora', serif !important;
        font-size: 0.78rem !important;
        font-weight: normal !important;
        padding: 4px 8px !important;
        letter-spacing: normal !important;
        text-decoration: underline !important;
    }
    section[data-testid="stMain"] [data-testid="stBaseButton-secondary"]:hover {
        color: #0a5c5a !important;
        background: transparent !important;
        transform: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stMain"] [data-testid="stBaseButton-secondary"] p {
        color: inherit !important;
        font-weight: normal !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 3. DADOS E FEEDS ---
# =============================================================================
RSS_FEEDS       = RSS_FEEDS_MAIN
FILTROS_TEMA    = FILTROS_TEMA_MAIN
FALLBACK_IMAGES = FALLBACK_IMAGES_MAIN
ICONES = {
    "Mundo":    "🌎", "Economia": "📈", "Politica": "🏛️", "IA":       "🤖",
    "Wellness": "🏃", "Ciencia":  "🔬", "Cinema":   "🎬", "Fofoca":   "⭐",
}

# =============================================================================
# --- 4. TRADUÇÃO DE TÍTULOS EM INGLÊS (Claude Haiku) ---
# =============================================================================
def traduzir_titulo_se_ingles(titulo, url_fonte=""):
    if not titulo:
        return titulo

    e_ingles = url_fonte in FEEDS_INGLES if url_fonte else False

    if not e_ingles:
        palavras_ingles = [
            "the ", "how to", "why ", "what ", "best ", "your ", "you ",
            "with ", "this ", "that ", " and ", " for ", " are ", " was ",
            "running", "workout", "training", "fitness", "marathon",
            "i ran", "i didn", "i found", " my ", "review:",
            "celebrity", "award", "season", "episode", "premiere",
        ]
        titulo_lower = titulo.lower()
        e_ingles = sum(1 for p in palavras_ingles if p in titulo_lower) >= 2

    if not e_ingles:
        return titulo

    gemini_key = ""
    try:
        gemini_key = st.secrets.get("GEMINI_API_KEY", "") or st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass
    if not gemini_key:
        import os
        gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not gemini_key:
        return titulo

    try:
        prompt = (
            f"Traduza este título de artigo de inglês para português brasileiro, "
            f"mantendo o tom jornalístico e direto. Retorne APENAS o título traduzido:\n\n{titulo}"
        )
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3}
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            traduzido = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().strip('"\'`')
            if 5 < len(traduzido) < 250:
                return traduzido
    except Exception:
        pass
    return titulo


# =============================================================================
# --- 5. VALIDAÇÕES ---
# =============================================================================
def validar_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email.strip()))

def validar_nome(nome):
    return len(nome.strip()) >= 2

# =============================================================================
# --- 6. GOOGLE SHEETS E REGRAS DE NEGÓCIO ---
# =============================================================================
# IMPORTANTE: cache_resource (não cache_data) — esta função devolve um objeto
# de CONEXÃO (gspread Worksheet). O cache_data serializa o retorno e a conexão
# desserializada perde a sessão autenticada, fazendo toda gravação/leitura
# falhar silenciosamente. cache_resource mantém o objeto vivo.
@st.cache_resource(ttl=300)
def conectar_planilha():
    if "GCP_JSON" not in st.secrets:
        return None
    try:
        creds_dict = json.loads(st.secrets["GCP_JSON"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
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
        return email.strip().lower() in [r.get("Email", "").strip().lower() for r in registros]
    except Exception:
        return False

def salvar_assinante(nome, email, ordem_temas):
    sheet = conectar_planilha()
    if not sheet:
        return False, "Não foi possível conectar. Tente novamente."
    try:
        # Alinha os valores à ORDEM REAL das colunas da planilha (que pode estar
        # embaralhada), em vez de assumir a ordem do RSS_FEEDS. Assim cada caderno
        # cai na coluna certa. Também traduz nomes legados (Mercado/Fitness).
        legado = {"Mercado": "Economia", "Fitness": "Wellness"}
        headers = [h.strip() for h in sheet.row_values(1)]
        if not headers:
            headers = ["Nome", "Email"] + list(RSS_FEEDS.keys())
        linha = []
        for h in headers:
            if h.lower() == "nome":
                linha.append(nome.strip())
            elif h.lower() == "email":
                linha.append(email.strip())
            else:
                chave = legado.get(h, h)
                linha.append(ordem_temas.get(chave, "Não"))
        sheet.append_row(linha)
        return True, "Sucesso"
    except Exception as e:
        # Mostra a causa real para facilitar o diagnóstico (ex.: permissão).
        return False, f"Não consegui registrar: {e}"

def cancelar_assinatura(email):
    sheet = conectar_planilha()
    if not sheet:
        return False, "Não foi possível conectar."
    try:
        email = email.strip().lower()
        todas_linhas = sheet.get_all_values()
        for i, linha in enumerate(todas_linhas):
            if not linha:
                continue
            email_linha = str(linha[1] if len(linha) > 1 else linha[0]).strip().lower()
            if email_linha == email:
                num_cols = len(todas_linhas[0]) if todas_linhas else 10
                for col_idx in range(2, num_cols):
                    sheet.update_cell(i + 1, col_idx + 1, "Não")
                return True, "Sua assinatura foi cancelada com sucesso. Lamentamos vê-lo partir!"
        return False, "E-mail não encontrado em nossa lista."
    except Exception:
        return False, "Erro ao processar o cancelamento. Tente novamente."

# =============================================================================
# --- 7. E-MAIL DE BOAS-VINDAS (Gmail SMTP) ---
# =============================================================================
def enviar_boas_vindas(nome, email_dest, temas_escolhidos):
    try:
        email_sender   = st.secrets.get("EMAIL_USER")
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
# --- 8. BUSCA DE IMAGEM (og:image / twitter:image) ---
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
# --- 9. BUSCA DE NOTÍCIAS RSS ---
# =============================================================================
@st.cache_data(ttl=600)
def buscar_noticias(tema):
    urls = RSS_FEEDS.get(tema, [])
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    TEMAS_MULTI_FONTE = {"Cinema", "Wellness", "Ciencia", "Fofoca"}
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
        og = buscar_og_image(entry.get('link', ''))
        if og:
            img = og
        if not img and 'media_content' in entry:
            for m in entry.media_content:
                if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                    img = m['url']
                    break
        if not img and 'enclosures' in entry:
            for enc in entry.enclosures:
                url_enc = enc.get('url', '')
                if any(ext in url_enc.lower() for ext in extensoes):
                    img = url_enc
                    break
        if not img and 'links' in entry:
            for l in entry.links:
                href = l.get('href', '')
                if l.get('type', '').startswith('image/') and any(ext in href.lower() for ext in extensoes):
                    img = href
                    break
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
        if not img:
            img = FALLBACK_IMAGES.get(
                tema,
                "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
            )

        titulo_final = entry.get('title', '')
        if tema in ("Wellness", "IA", "Cinema", "Fofoca"):
            titulo_final = traduzir_titulo_se_ingles(titulo_final)

        noticias.append({
            "titulo": titulo_final,
            "link":   entry.get('link', ''),
            "img":    img,
        })

    return noticias

# =============================================================================
# --- 10. INDICADORES FINANCEIROS (Capa) ---
# =============================================================================
@st.cache_data(ttl=900)
def obter_indicadores_app():
    try:
        import yfinance as yf
    except ImportError:
        return []

    dados = []

    def _variacao(hist):
        if len(hist) >= 2:
            atual = hist["Close"].iloc[-1]
            ant   = hist["Close"].iloc[-2]
            return atual, (atual - ant) / ant * 100
        return None, None

    for ticker_id, nome, fmt in [
        ("BRL=X", "USD/BRL", lambda v: f"R$ {v:.2f}"),
        ("^BVSP", "IBOV",    lambda v: f"{int(v):,} pts".replace(",", ".")),
    ]:
        try:
            hist = yf.Ticker(ticker_id).history(period="5d")
            atual, var = _variacao(hist)
            if atual is not None:
                dados.append({"nome": nome, "valor": fmt(atual), "var": var})
        except Exception:
            pass

    for ticker_id, moeda in [("BTC-BRL", "BRL"), ("BTC-USD", "USD")]:
        try:
            hist = yf.Ticker(ticker_id).history(period="5d")
            atual, var = _variacao(hist)
            if atual is not None:
                label = f"R$ {atual/1000:.1f}k" if moeda == "BRL" else f"US$ {atual/1000:.1f}k"
                dados.append({"nome": "BTC", "valor": label, "var": var})
                break
        except Exception:
            pass

    return dados

# =============================================================================
# --- 11. MODAIS (Inscrição, Cancelamento, Privacidade) ---
# =============================================================================
@st.dialog("✉️ Assine o All News Journal", width="large")
def modal_inscricao():
    st.markdown(
        "<p style='font-size:0.95rem; color:#555;'>"
        "Receba sua edição personalizada <b>todas as manhãs</b>.</p>",
        unsafe_allow_html=True
    )

    nome_dlg  = st.text_input("Seu Nome", placeholder="Como gostaria de ser chamado")
    email_dlg = st.text_input("Seu melhor E-mail", placeholder="voce@exemplo.com")

    # st.multiselect preserva a ordem dos cliques — é assim que capturamos a
    # preferência de ordenação dos cadernos sem precisar de up/down arrows.
    opcoes_formatadas = [f"{ICONES.get(t, '📰')} {t}" for t in RSS_FEEDS.keys()]

    st.markdown(
        "<p style='font-size:0.9rem; font-weight:bold; margin-top:14px; margin-bottom:0;'>"
        "📋 Escolha seus cadernos (a ordem importa!):</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='font-size:0.75rem; color:#888; margin-top:0;'>"
        "<i>Dica: a ordem em que você selecionar os cadernos será a mesma "
        "em que eles aparecerão no seu e-mail.</i></p>",
        unsafe_allow_html=True
    )

    selecionados_formatados = st.multiselect(
        "Selecione:",
        options=opcoes_formatadas,
        default=opcoes_formatadas,  # todos selecionados por padrão
        label_visibility="collapsed",
    )
    temas_sel_dlg = [s.split(" ", 1)[1] for s in selecionados_formatados]

    st.write("")
    if st.button("ASSINAR AGORA — É GRATUITO 🗞️", type="primary", use_container_width=True):
        erros_dlg = []
        if not validar_nome(nome_dlg):
            erros_dlg.append("Informe um nome válido.")
        if not email_dlg or not validar_email(email_dlg):
            erros_dlg.append("O e-mail informado não é válido.")
        if not temas_sel_dlg:
            erros_dlg.append("Selecione pelo menos um caderno.")

        if erros_dlg:
            for e in erros_dlg:
                st.warning(e)
        else:
            with st.spinner("Processando sua inscrição..."):
                if email_ja_cadastrado(email_dlg):
                    st.info("📬 Este e-mail já está inscrito!")
                else:
                    ordem_banco = {}
                    pos = 1
                    for tema in RSS_FEEDS.keys():
                        if tema in temas_sel_dlg:
                            ordem_banco[tema] = pos
                            pos += 1
                        else:
                            ordem_banco[tema] = "Não"

                    ok_dlg, msg_dlg = salvar_assinante(nome_dlg, email_dlg, ordem_banco)
                    if ok_dlg:
                        enviar_boas_vindas(nome_dlg, email_dlg, temas_sel_dlg)
                        st.success("✅ Inscrição confirmada! Verifique seu e-mail.")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg_dlg}")


@st.dialog("Cancelar assinatura")
def modal_cancelamento():
    st.markdown(
        "<p style='font-size:0.95rem; color:#444; line-height:1.6;'>"
        "Você vai parar de receber a edição diária do All News Journal. Tem certeza?</p>",
        unsafe_allow_html=True
    )

    with st.form("form_cancelamento_dlg", clear_on_submit=False):
        email_cancel = st.text_input("Seu e-mail cadastrado", placeholder="voce@exemplo.com")
        confirmar = st.checkbox("Confirmo que desejo cancelar minha assinatura")
        btn_cancelar = st.form_submit_button("Confirmar cancelamento", type="primary", use_container_width=True)

    if btn_cancelar:
        if not email_cancel:
            st.warning("Por favor, informe seu e-mail.")
        elif not validar_email(email_cancel):
            st.warning("E-mail inválido.")
        elif not confirmar:
            st.warning("Marque a caixa de confirmação.")
        else:
            with st.spinner("Processando..."):
                ok, msg = cancelar_assinatura(email_cancel)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")


@st.dialog("🔒 Política de Privacidade", width="large")
def modal_privacidade():
    st.markdown("""
**All News Journal — Política de Privacidade**

Coletamos apenas o nome e e-mail fornecidos voluntariamente no formulário de inscrição.
Esses dados são utilizados exclusivamente para o envio da edição diária do All News Journal.

- Não compartilhamos suas informações com terceiros.
- Não utilizamos cookies de rastreamento.
- Você pode cancelar a assinatura e ter seus dados removidos a qualquer momento.

Para dúvidas ou solicitações de remoção, entre em contato via
[gustavojustusnunes@gmail.com](mailto:gustavojustusnunes@gmail.com).

*Última atualização: Junho de 2026.*
    """)


# URL ?acao=cancelar → auto-abre modal de cancelamento (link do email)
_params = st.query_params
if _params.get("acao", "") == "cancelar" and not st.session_state.get("_cancel_modal_shown", False):
    st.session_state["_cancel_modal_shown"] = True
    modal_cancelamento()

# =============================================================================
# --- META TAGS SEO ---
# =============================================================================
st.markdown("""
<meta property="og:title" content="All News Journal — Curadoria Premium de Notícias">
<meta property="og:description" content="Receba as notícias que importam, todas as manhãs. Gratuito.">
<meta property="og:type" content="website">
<meta name="description" content="All News Journal — curadoria premium e automatizada das notícias do dia. 8 cadernos temáticos. Gratuito.">
""", unsafe_allow_html=True)

# =============================================================================
# --- CONTEÚDO PRINCIPAL (LANDING PAGE) ---
# =============================================================================
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

aba_inicio, aba_edicao, aba_podcast = st.tabs(["🏠 Página Inicial", "📰 Ler Edição de Hoje", "🎙️ Ouvir no Spotify"])
with aba_inicio:
    st.markdown("""
    <div style='max-width: 720px; margin: 25px auto 35px; padding: 0 20px; text-align: center; color: #2c2c2c; line-height: 1.7; font-size: 1.05rem;'>
      <p style='font-style: italic; color: #0a5c5a; font-size: 1.15rem; margin-bottom: 18px;'>Notícias relevantes, sem ruído, todas as manhãs.</p>
      <p>O <b>All News Journal</b> é um jornal digital independente que entrega na sua caixa de e-mail, <b>todas as manhãs</b>, uma edição <b>personalizada</b> com os cadernos que você escolheu.</p>
      <p>Cada manchete é resumida por nossa redação editorial. Você lê em cinco minutos o que importou no mundo e começa o dia informado, sem rolar timeline, sem clicar em link nenhum.</p>
      <p style='margin-top: 22px; font-size: 0.95rem; color: #555;'>Use o botão abaixo para assinar. É gratuito.</p>
    </div>
    """, unsafe_allow_html=True)

    # Botão CTA centralizado que abre o modal
    col_cta_l, col_cta_c, col_cta_r = st.columns([1, 2, 1])
    with col_cta_c:
        if st.button("✉️ ASSINE GRATUITAMENTE — É RÁPIDO ✨", type="primary", use_container_width=True, key="btn_open_signup"):
            modal_inscricao()

    # Data + Edição
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

    # Contador de assinantes
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

    # Seção "Sobre"
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 Sobre o All News Journal"):
        st.markdown("""
    **Missão:** Curadoria premium e gratuita das notícias que importam — filtradas, resumidas e entregues diretamente no seu e-mail todas as manhãs.

    **Frequência:** Edição diária enviada **toda manhã** (horário de Brasília), de segunda a domingo.

    **Cadernos disponíveis:**

    | Caderno | Foco |
    |---|---|
    | 🌎 Mundo | Geopolítica e eventos internacionais |
    | 📈 Economia | Mercado, investimentos e finanças |
    | 🏛️ Política | Brasil: Congresso, governo e Judiciário |
    | 🤖 IA | Inteligência artificial, modelos e laboratórios |
    | 🏃 Wellness | Performance, treino, corrida, ciclismo, nutrição |
    | 🔬 Ciência | Descobertas científicas e saúde |
    | 🎬 Cinema | Filmes, séries e streaming |
    | ⭐ Fofoca | Celebridades internacionais e cultura pop global |

    **100% automatizado com inteligência artificial** — Google Gemini 1.5 Flash gera resumos jornalísticos de 85 a 105 palavras por notícia, em Português Brasileiro.
        """)

    # =============================================================================
    # --- RODAPÉ PROFISSIONAL ---
    # =============================================================================
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
            <p style='font-size:0.72rem; color:#aaa; margin:6px 0 0;'>
                <a href='mailto:gustavojustusnunes@gmail.com?subject=Contato%20All%20News%20Journal'
                   style='color:#0a5c5a; text-decoration:none;'>Fale conosco</a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_rod_l, col_rod_c1, col_rod_c2, col_rod_r = st.columns([2, 1, 1, 2])
    with col_rod_c1:
        if st.button("Cancelar assinatura", key="footer_btn_cancel", type="secondary", use_container_width=True):
            modal_cancelamento()
    with col_rod_c2:
        if st.button("Política de Privacidade", key="footer_btn_privacy", type="secondary", use_container_width=True):
            modal_privacidade()

with aba_podcast:
    st.markdown("<br><h2 style='text-align: center; color: #0a5c5a; font-family: Playfair Display, serif;'>🎧 Ouça a edição de hoje</h2><br>", unsafe_allow_html=True)
    
    # ── Player Nativo (Fallback/Direto) ──
    import os as _os
    _param  = st.query_params.get("edicao", "")
    _podcast_path = None
    _idx_path = _os.path.join("edicoes", "index.json")
    if _os.path.exists(_idx_path):
        with open(_idx_path, encoding="utf-8") as _f:
            _indice = json.load(_f)
        if _indice:
            _datas = [e["data"] for e in _indice]
            _data_atual = _param if _param in _datas else _datas[0]
            _podcast_path = _os.path.join("edicoes", "podcasts", f"podcast_{_data_atual}.mp3")
    
    if _podcast_path and _os.path.exists(_podcast_path):
        st.markdown("<div style='text-align: center; margin-bottom: 15px; color: #333;'>Reproduzir áudio original (Apresentação: Leo e Ana)</div>", unsafe_allow_html=True)
        st.audio(_podcast_path, format="audio/mpeg")
    else:
        st.markdown("<div style='text-align: center; margin-bottom: 15px; color: #888;'><em>O áudio de hoje ainda está sendo gerado ou não está disponível.</em></div>", unsafe_allow_html=True)

with aba_edicao:
    # =============================================================================
    # --- EDIÇÃO DO DIA (publicada pelo daily — lê edicoes/index.json) ---
    # =============================================================================
    try:
        import os as _os
        import streamlit.components.v1 as _components

        _idx_path = _os.path.join("edicoes", "index.json")
        if _os.path.exists(_idx_path):
            with open(_idx_path, encoding="utf-8") as _f:
                _indice = json.load(_f)
            if _indice:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    "<h3 style='text-align:center; letter-spacing:1px;'>📰 Edição de hoje</h3>",
                    unsafe_allow_html=True,
                )
                _datas   = [e["data"] for e in _indice]
                _rotulos = {
                    e["data"]: f"{e.get('data_extenso', e['data'])} — {e.get('manchete', '')[:60]}"
                    for e in _indice
                }
                _param  = st.query_params.get("edicao", "")
                _padrao = _param if _param in _datas else _datas[0]
                _sel = st.selectbox(
                    "🗞️ Edições anteriores:",
                    _datas,
                    index=_datas.index(_padrao),
                    format_func=lambda d: _rotulos.get(d, d),
                )
                _arq = _os.path.join("edicoes", f"{_sel}.html")
                if _os.path.exists(_arq):
                    # Tenta carregar o podcast do dia, se existir
                    _podcast_path = _os.path.join("edicoes", "podcasts", f"podcast_{_sel}.mp3")
                    if _os.path.exists(_podcast_path):
                        st.markdown("<div style='text-align: center; margin-bottom: 10px; color: #0a5c5a; font-weight: bold;'>🎧 Ouça o Podcast Diário (Apresentação: Leo e Ana)</div>", unsafe_allow_html=True)
                        st.audio(_podcast_path, format="audio/mpeg")
                        
                    with open(_arq, encoding="utf-8") as _f:
                        _components.html(_f.read(), height=2400, scrolling=True)
    except Exception:
        pass  # sem edicoes/, a seção simplesmente não aparece
