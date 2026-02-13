import streamlit as st
import feedparser
import requests
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS: DESIGN CLÁSSICO (JORNAL DE PAPEL) ---
st.markdown("""
<style>
    /* Importando fontes com serifa (Estilo New York Times) */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Merriweather:wght@300;400;700&display=swap');

    /* Esconder elementos do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Fundo Papel */
    .stApp {
        background-color: #fcfbf9; 
        font-family: 'Merriweather', serif;
        color: #2c2c2c;
    }
    
    /* Título Principal */
    h1 {
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        text-align: center;
        font-size: 3.5rem !important;
        letter-spacing: 2px;
        border-bottom: 3px double #111;
        padding-bottom: 20px;
        margin-bottom: 20px;
        color: #111;
    }
    
    /* Subtítulos */
    h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #111;
    }

    /* Cards de Notícia */
    .news-card {
        background-color: #fff;
        border: 1px solid #ddd;
        padding: 0;
        margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.03);
        transition: transform 0.2s;
    }
    .news-card:hover {
        transform: translateY(-3px);
        box-shadow: 4px 4px 15px rgba(0,0,0,0.1);
    }
    .news-img {
        width: 100%;
        height: 160px;
        object-fit: cover;
        border-bottom: 1px solid #eee;
        filter: sepia(10%); /* Efeito levemente envelhecido */
    }
    .news-content {
        padding: 15px;
    }
    .news-tag {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: bold;
        color: #888;
        margin-bottom: 5px;
    }
    .news-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 10px;
        display: block;
        color: #111;
        text-decoration: none;
        line-height: 1.3;
    }
    .news-title:hover {
        text-decoration: underline;
        color: #b11226; /* Vermelho Jornal */
    }
    .news-date {
        font-size: 0.75rem;
        color: #999;
        margin-top: 10px;
        border-top: 1px solid #eee;
        padding-top: 5px;
    }

    /* Sidebar Customizada */
    section[data-testid="stSidebar"] {
        background-color: #f4f4f4;
        border-right: 1px solid #ddd;
    }
    
    /* Botões */
    .stButton button {
        background-color: #111;
        color: white;
        border-radius: 0;
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #b11226;
        color: white;
        border: 1px solid #b11226;
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
    # Tenta pegar a senha das Secrets
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
    
    # Prepara linha: Nome, Email, Sim/Não para cada tema
    linha = [nome, email]
    chaves = list(RSS_FEEDS.keys())
    
    for chave in chaves:
        if chave in temas: linha.append("Sim")
        else: linha.append("Não")
    
    try:
        sheet.append_row(linha)
        return True
    except: return False

@st.cache_data(ttl=1800) # Cache de 30 minutos
def buscar_noticias(tema):
    url = RSS_FEEDS.get(tema)
    if not url: return []
    try:
        feed = feedparser.parse(url)
        noticias = []
        for entry in feed.entries[:6]:
            # Lógica de Imagem
            img = f"https://placehold.co/600x300/333/FFF?text={tema}"
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
    st.markdown("<h2 style='text-align:center;'>✍️ Assinatura</h2>", unsafe_allow_html=True)
    st.info("Receba o *Briefing Matinal* no seu e-mail gratuitamente.")
    
    with st.form("form_cadastro"):
        nome = st.text_input("Nome Completo")
        email = st.text_input("Seu melhor E-mail")
        st.markdown("---")
        st.write("**Selecione seus Cadernos:**")
        
        # Checkboxes
        escolhas = []
        c1, c2 = st.columns(2)
        for i, tema in enumerate(RSS_FEEDS.keys()):
            col = c1 if i % 2 == 0 else c2
            if col.checkbox(tema, value=True):
                escolhas.append(tema)
        
        st.markdown("---")
        submit = st.form_submit_button("🗞️ Confirmar Inscrição")
        
        if submit:
            if nome and email:
                with st.spinner("Registrando..."):
                    if salvar_assinante(nome, email, escolhas):
                        st.success("Sucesso! Verifique seu e-mail amanhã cedo.")
                        st.balloons()
            else:
                st.warning("Preencha Nome e E-mail.")

# --- 6. CONTEÚDO PRINCIPAL ---

# Título
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

# Data e Local
col_date, col_loc = st.columns(2)
col_date.markdown(f"<div style='text-align:center; border-top:1px solid #333; border-bottom:1px solid #333; padding:5px;'>📅 {datetime.now().strftime('%A, %d %B %Y')}</div>", unsafe_allow_html=True)
col_loc.markdown(f"<div style='text-align:center; border-top:1px solid #333; border-bottom:1px solid #333; padding:5px;'>🌎 Edição Global • Online</div>", unsafe_allow_html=True)

st.write("") # Espaçamento

# Filtro
tema_atual = st.selectbox("📖 Escolha o Caderno para ler agora:", ["Capa (Destaques)"] + list(RSS_FEEDS.keys()))

noticias_display = []

if tema_atual == "Capa (Destaques)":
    # Pega 1 de cada tema
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

# Grid de Notícias
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
                    <div class="news-tag">{n['tema']}</div>
                    <a href="{n['link']}" target="_blank" class="news-title">{n['titulo']}</a>
                    <div class="news-date">Clique para ler na íntegra</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Carregando as manchetes...")

# Rodapé Simples
st.markdown("---")
st.markdown("<div style='text-align:center; color:#888; font-size:0.8rem;'>© 2025 All News Journal Group.</div>", unsafe_allow_html=True)
