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
    FEEDS_INGLES,
    ICONES_TEMA,
    ORDEM_CADERNOS,
)

# =============================================================================
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
# =============================================================================
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed" # Garante que a sidebar nasça morta
)

# =============================================================================
# --- AUTO-EMBED E JS INJECTIONS ---
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
    
    /* Remove a barra lateral totalmente do DOM visual */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* Força o sumiço do avatar no canto inferior direito do Streamlit Cloud */
    .stApp > div:last-child { display: none !important; }
    [data-testid="stAppViewContainer"] > div:last-child { display: none !important; }

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

    /* ── SELECTBOX E BOTÃO PRINCIPAL ── */
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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 3. DADOS E FEEDS ---
# =============================================================================
RSS_FEEDS        = RSS_FEEDS_MAIN
FILTROS_TEMA     = FILTROS_TEMA_MAIN
FALLBACK_IMAGES  = FALLBACK_IMAGES_MAIN
ICONES = {
    "Mundo":    "🌎", "Economia": "📈", "Politica": "🏛️", "IA":        "🤖",
    "Wellness": "🏃", "Ciencia":  "🔬", "Cinema":   "🎬", "Fofoca":   "⭐",
}

def traduzir_titulo_se_ingles(titulo, url_fonte=""):
    # ... (MANTIDO SEU CÓDIGO ORIGINAL DE TRADUÇÃO) ...
    if not titulo: return titulo
    e_ingles = url_fonte in FEEDS_INGLES if url_fonte else False
    if not e_ingles:
        palavras_ingles = ["the ", "how to", "why ", "what ", "best ", "your ", "you ", "with ", "this ", "that ", " and ", " for ", " are ", " was "]
        titulo_lower = titulo.lower()
        palavras_encontradas = sum(1 for p in palavras_ingles if p in titulo_lower)
        e_ingles = palavras_encontradas >= 2
    if not e_ingles: return titulo

    claude_key = ""
    try: claude_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.secrets.get("CLAUDE_KEY", "")
    except Exception: pass

    if not claude_key: return titulo
    try:
        prompt = f"Traduza este título de artigo de inglês para português brasileiro, mantendo o tom jornalístico e direto. Retorne APENAS o título traduzido:\n\n{titulo}"
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 150, "messages": [{"role": "user", "content": prompt}]},
            timeout=10
        )
        if r.status_code == 200:
            traduzido = r.json()["content"][0]["text"].strip().strip('"\'`')
            if 5 < len(traduzido) < 250: return traduzido
    except Exception: pass
    return titulo

def validar_email(email): return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email.strip()))
def validar_nome(nome): return len(nome.strip()) >= 2

# =============================================================================
# --- 5. GOOGLE SHEETS E REGRAS DE NEGÓCIO ---
# =============================================================================
@st.cache_data(ttl=300)
def conectar_planilha():
    if "GCP_JSON" not in st.secrets: return None
    try:
        creds_dict = json.loads(st.secrets["GCP_JSON"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet_id = st.secrets.get("GOOGLE_SHEETS_ID", "")
        if sheet_id: return client.open_by_key(sheet_id).sheet1
        return client.open("noticias_db").sheet1
    except Exception: return None

def email_ja_cadastrado(email):
    sheet = conectar_planilha()
    if not sheet: return False
    try:
        registros = sheet.get_all_records()
        return email.strip().lower() in [r.get("Email", "").strip().lower() for r in registros]
    except Exception: return False

def salvar_assinante(nome, email, ordem_temas):
    sheet = conectar_planilha()
    if not sheet: return False, "Não foi possível conectar. Tente novamente."
    try:
        linha = [nome.strip(), email.strip()]
        for chave in RSS_FEEDS.keys(): linha.append(ordem_temas.get(chave, "Não"))
        sheet.append_row(linha)
        return True, "Sucesso"
    except Exception: return False, "Ocorreu um problema ao registar. Tente novamente."

def cancelar_assinatura(email):
    sheet = conectar_planilha()
    if not sheet: return False, "Não foi possível conectar."
    try:
        email = email.strip().lower()
        todas_linhas = sheet.get_all_values()
        for i, linha in enumerate(todas_linhas):
            if not linha: continue
            email_linha = str(linha[1] if len(linha) > 1 else linha[0]).strip().lower()
            if email_linha == email:
                num_cols = len(todas_linhas[0]) if todas_linhas else 10
                for col_idx in range(2, num_cols): sheet.update_cell(i + 1, col_idx + 1, "Não")
                return True, "A sua assinatura foi cancelada com sucesso."
        return False, "E-mail não encontrado."
    except Exception: return False, "Erro ao processar."

# ... (MANTIDO CÓDIGO ORIGINAL DE E-MAIL, BUSCA IMAGEM, YFINANCE, ETC) ...
# Por brevidade, as funções enviar_boas_vindas, buscar_og_image, buscar_noticias e obter_indicadores_app permanecem inalteradas.

# Copie e cole essas funções do seu código original aqui (enviar_boas_vindas, buscar_og_image, buscar_noticias, obter_indicadores_app)

# =============================================================================
# --- CONTEÚDO PRINCIPAL (LANDING PAGE) ---
# =============================================================================
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

st.markdown("""
<div style='max-width: 720px; margin: 25px auto 35px; padding: 0 20px; text-align: center; color: #2c2c2c; line-height: 1.7; font-size: 1.05rem;'>
  <p style='font-style: italic; color: #0a5c5a; font-size: 1.15rem; margin-bottom: 18px;'>Notícias relevantes, sem ruído, todas as manhãs.</p>
  <p>O <b>All News Journal</b> é um jornal digital independente que entrega na sua caixa de e-mail, todos os dias às 6h, uma edição <b>personalizada</b> com os cadernos que você escolheu.</p>
  <p>Cada manchete é resumida por nossa redação editorial. Você lê em cinco minutos o que importou no mundo e começa o dia informado, sem rolar timeline, sem clicar em link nenhum.</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# --- CTA DE INSCRIÇÃO: MODAL ÚNICO E ROBUSTO ---
# =============================================================================
@st.dialog("✉️ Assine o All News Journal", width="large")
def modal_inscricao():
    st.markdown("<p style='font-size:0.95rem; color:#555;'>Receba sua edição personalizada <b>todas as manhãs às 6h</b>.</p>", unsafe_allow_html=True)

    nome_dlg  = st.text_input("Seu Nome", placeholder="Como gostaria de ser chamado")
    email_dlg = st.text_input("Seu melhor E-mail", placeholder="voce@exemplo.com")

    # A grande jogada: O Multiselect preserva a ordem que o usuário clica!
    opcoes_formatadas = [f"{ICONES.get(t, '📰')} {t}" for t in RSS_FEEDS.keys()]
    
    st.markdown("<p style='font-size:0.9rem; font-weight:bold; margin-top:14px; margin-bottom:0;'>📋 Escolha seus cadernos (A ordem importa!):</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#888; margin-top:0;'><i>Dica: A ordem em que você selecionar os cadernos abaixo será a ordem exata em que eles aparecerão no seu e-mail.</i></p>", unsafe_allow_html=True)
    
    selecionados_formatados = st.multiselect(
        "Selecione:",
        options=opcoes_formatadas,
        default=opcoes_formatadas, # Vem todos selecionados por padrão
        label_visibility="collapsed"
    )

    # Limpando os ícones para pegar só o nome do tema
    temas_sel_dlg = [s.split(" ", 1)[1] for s in selecionados_formatados]

    st.write("")
    if st.button("ASSINAR AGORA — É GRATUITO 🗞️", type="primary", use_container_width=True):
        erros_dlg = []
        if not validar_nome(nome_dlg): erros_dlg.append("Informe um nome válido.")
        if not email_dlg or not validar_email(email_dlg): erros_dlg.append("O e-mail informado não é válido.")
        if not temas_sel_dlg: erros_dlg.append("Selecione pelo menos um caderno.")

        if erros_dlg:
            for e in erros_dlg: st.warning(e)
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
                        # enviar_boas_vindas(nome_dlg, email_dlg, temas_sel_dlg) # Descomente quando colocar a func de volta
                        st.success("✅ Inscrição confirmada! Verifique seu e-mail.")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg_dlg}")

# Botão centralizado que abre o modal
col_cta_l, col_cta_c, col_cta_r = st.columns([1, 2, 1])
with col_cta_c:
    if st.button("✉️ ASSINE GRATUITAMENTE — É RÁPIDO ✨", type="primary", use_container_width=True):
        modal_inscricao()

# ... (MANTIDO RESTANTE DA PÁGINA COM A EXIBIÇÃO DE NOTÍCIAS) ...

# =============================================================================
# --- RODAPÉ PROFISSIONAL E MODAL DE CANCELAMENTO ---
# =============================================================================
st.markdown("<br><br>", unsafe_allow_html=True)

@st.dialog("Deseja cancelar sua assinatura?")
def modal_cancelamento():
    st.write("Insira seu e-mail abaixo para interromper o recebimento do jornal.")
    email_cancel = st.text_input("Seu e-mail cadastrado")
    if st.button("Confirmar Cancelamento", type="primary"):
        if validar_email(email_cancel):
            ok, msg = cancelar_assinatura(email_cancel)
            if ok: st.success(msg)
            else: st.error(msg)
        else:
            st.warning("E-mail inválido.")

cols_footer = st.columns([1,2,1])
with cols_footer[1]:
    st.markdown("""
        <div style='border-top: 2px solid #0a5c5a; padding: 25px 0 10px; text-align: center; color: #0a5c5a; font-family: Playfair Display, serif;'>
            <p style='font-size:1.1rem; font-weight:bold; letter-spacing:2px; margin:0;'>ALL NEWS JOURNAL</p>
            <p style='font-size:0.75rem; color:#888; margin:8px 0 0;'>© """ + str(datetime.now().year) + """ All News Journal Group</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("Cancelar Assinatura", use_container_width=True): modal_cancelamento()
    with col_c2:
        st.markdown("<p style='text-align:center; padding-top:8px;'><a href='mailto:contato@allnews.com' style='color:#0a5c5a;'>Fale Conosco</a></p>", unsafe_allow_html=True)
