import streamlit as st
import feedparser
import requests
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS: DESIGN PREMIUM (TURQUESA E CREME) ---
st.markdown("""
<style>
    /* Importando fontes premium */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');

    /* Esconder menu superior direito do Streamlit, mas manter o botão da sidebar à esquerda */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    .stDeployButton {display:none;}
    
    /* Fundo Principal (Creme) e Fonte Geral */
    .stApp {
        background-color: #fdfbf7; 
        font-family: 'Lora', serif;
        color: #2c2c2c;
    }
    
    /* Título Principal */
    h1 {
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        text-align: center;
        font-size: 3.5rem !important;
        letter-spacing: 2px;
        color: #0a5c5a !important; /* Azul Turquesa Escuro */
        border-top: 2px solid #0a5c5a;
        border-bottom: 2px solid #0a5c5a;
        padding: 15px 0;
        margin-bottom: 20px;
    }
    
    h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #0a5c5a !important;
    }

    /* Cards de Notícia (Estilo Revista) */
    .news-card {
        background-color: #ffffff;
        border: 1px solid #e5e3de;
        border-radius: 8px; /* Cantos arredondados modernos */
        overflow: hidden;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .news-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(10, 92, 90, 0.15); /* Sombra turquesa ao passar o mouse */
    }
    .news-img {
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-bottom: 3px solid #0a5c5a;
    }
    .news-content {
        padding: 20px;
    }
    
    /* ===== CORREÇÃO DA TAG "DESTAQUE" ===== */
    .news-tag {
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: bold;
        background-color: #0a5c5a; /* Fundo Turquesa */
        color: #ffffff !important; /* Letra Branca */
        padding: 4px 10px;
        border-radius: 4px;
        margin-bottom: 12px;
        display: inline-block;
    }
    /* ====================================== */

    .news-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 12px;
        display: block;
        color: #111 !important;
        text-decoration: none;
        line-height: 1.3;
    }
    .news-title:hover {
        color: #0a5c5a !important;
    }
    .news-date {
        font-size: 0.8rem;
        color: #777;
        font-style: italic;
        border-top: 1px solid #eee;
        padding-top: 10px;
    }

    /* SUPER DESTAQUE NA SIDEBAR (ÁREA DE INSCRIÇÃO) */
    section[data-testid="stSidebar"] {
        background-color: #084c4a !important; /* Turquesa muito escuro */
        border-right: none;
    }
    /* Força os textos da sidebar a ficarem em Creme */
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #fdfbf7 !important;
    }
    
    /* Campos de digitar texto (Fundo creme, letra preta) */
    section[data-testid="stSidebar"] input {
        background-color: #fdfbf7 !important;
        color: #111 !important;
        border-radius: 5px !important;
        border: none !important;
    }
    
    /* Botão de Inscrição em Super Destaque */
    section[data-testid="stSidebar"] .stButton button {
        background-color: #fdfbf7 !important;
        color: #084c4a !important;
        font-weight: 900 !important;
        border-radius: 5px !important;
        border: 2px solid #fdfbf7 !important;
        width: 100%;
        transition: all 0.3s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: #e5e3de !important;
        transform: scale(1.02);
    }
    
    /* Caixa do formulário */
    [data-testid="stForm"] {
        border: 1px solid rgba(253, 251, 247, 0.2);
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DADOS E FEEDS ---
RSS_FEEDS = {
    "Mercado": "https://www.infomoney.com.br/feed/",
    "Tech": "https://rss.tecmundo.com.br/feed",
    "Motos": "https://www.motociclismoonline.com.br/feed/", 
    "Fofoca": "https://revistaquem.globo.com/rss/quem/",
    "Politica": "https://g1.globo.com/rss/g1/politica/",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Ciencia": "https://gizmodo.uol.com.br/category/ciencia/feed/",
    "Mundo": "https://g1.globo.com/rss/g1/mundo/"
}

# --- 4. FUNÇÕES DO GOOGLE SHEETS ---
def conectar_planilha():
    if "GCP_JSON" not in st.secrets:
        st.error("⚠️ Configuração pendente: Adicione GCP_JSON nas Secrets do Streamlit.")
        return None
    try:
        creds_dict = json.loads(st.secrets["GCP_JSON"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("noticias_db").sheet1
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

def salvar_assinante(nome, email, temas):
    sheet = conectar_planilha()
    if not sheet: return False
    linha = [nome, email]
    chaves = list(RSS_FEEDS.keys())
    for chave in chaves:
        if chave in temas: linha.append("Sim")
        else: linha.append("Não")
    try:
        sheet.append_row(linha)
        return True
    except: return False

@st.cache_data(ttl=1800)
def buscar_noticias(tema):
    url = RSS_FEEDS.get(tema)
    if not url: return []
    try:
        feed = feedparser.parse(url)
        noticias = []
        for entry in feed.entries[:6]:
            img = f"https://placehold.co/600x300/0a5c5a/FFF?text={tema}"
            if 'media_content' in entry:
                for m in entry.media_content:
                    if 'url' in m: img = m['url']; break
            elif 'links' in entry:
                for l in entry.links:
                    if l.get('type','').startswith('image/'): img = l['href']; break
            
            noticias.append({
                "titulo": entry.title,
                "link": entry.link,
                "img": img,
                "data": entry.get('published', '')[:16]
            })
        return noticias
    except: return []

# --- 5. SIDEBAR: ÁREA DE ASSINATURA ---
with st.sidebar:
    st.markdown("<h2 style='text-align:center; font-family: Playfair Display;'>✍️ Junte-se ao Clube</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size: 0.9rem;'>Receba nossa curadoria premium de notícias todas as manhãs, gratuitamente.</p>", unsafe_allow_html=True)
    st.write("")
    
    with st.form("form_cadastro"):
        nome = st.text_input("Seu Nome")
        email = st.text_input("Seu melhor E-mail")
        st.markdown("<hr style='border-color: rgba(253, 251, 247, 0.2);'>", unsafe_allow_html=True)
        st.write("**Personalize sua Edição:**")
        
        escolhas = []
        c1, c2 = st.columns(2)
        for i, tema in enumerate(RSS_FEEDS.keys()):
            col = c1 if i % 2 == 0 else c2
            if col.checkbox(tema, value=True):
                escolhas.append(tema)
        
        st.write("")
        submit = st.form_submit_button("ASSINAR AGORA 🗞️")
        
        if submit:
            if nome and email:
                with st.spinner("Preparando sua edição..."):
                    if salvar_assinante(nome, email, escolhas):
                        st.success("Tudo certo! Verifique seu e-mail amanhã cedo.")
                        st.balloons()
            else:
                st.warning("Por favor, preencha Nome e E-mail.")

# --- 6. CONTEÚDO PRINCIPAL ---

st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

col_date, col_loc = st.columns(2)
col_date.markdown(f"<div style='text-align:center; color: #0a5c5a; font-weight: bold; padding:5px;'>📅 {datetime.now().strftime('%A, %d de %B de %Y')}</div>", unsafe_allow_html=True)
col_loc.markdown(f"<div style='text-align:center; color: #0a5c5a; font-weight: bold; padding:5px;'>🌎 Edição Global • Online</div>", unsafe_allow_html=True)

st.write("")

tema_atual = st.selectbox("📖 Navegue pelos Cadernos:", ["Capa (Destaques)"] + list(RSS_FEEDS.keys()))
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
                <a href="{n['link']}" target="_blank">
                    <img src="{n['img']}" class="news-img">
                </a>
                <div class="news-content">
                    <span class="news-tag">{n['tema']}</span>
                    <a href="{n['link']}" target="_blank" class="news-title">{n['titulo']}</a>
                    <div class="news-date">Acesse a matéria original completa</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Buscando as manchetes mais recentes...")

st.markdown("<hr style='border-color: #0a5c5a; opacity: 0.2; margin-top: 50px;'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; color:#0a5c5a; font-family: Playfair Display; font-size:0.9rem;'>© 2026 All News Journal Group. Conteúdo Premium.</div>", unsafe_allow_html=True)
