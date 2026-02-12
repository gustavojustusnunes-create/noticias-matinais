import streamlit as st
import feedparser
import requests
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA E DESIGN CLÁSSICO ---
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS: Design Jornalístico (Times New Roman / Serifas) + Esconder GitHub
st.markdown("""
<style>
    /* Importando fontes clássicas */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Merriweather:wght@300;400;700&display=swap');

    /* Esconder Elementos do Streamlit (GitHub, Menu, Rodapé) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Fundo e Tipografia Geral */
    .stApp {
        background-color: #fdfbf7; /* Cor de papel envelhecido leve */
        font-family: 'Merriweather', serif;
    }
    
    /* Títulos */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #1a1a1a;
    }
    
    h1 { 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        border-bottom: 3px double #1a1a1a;
        padding-bottom: 10px;
        text-align: center;
        font-size: 3rem !important;
    }

    /* Cartões de Notícia (Estilo Jornal) */
    .news-card {
        background-color: white;
        padding: 0;
        border: 1px solid #ddd;
        margin-bottom: 25px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .news-text {
        padding: 15px;
    }
    .news-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #000;
        text-decoration: none;
    }
    .news-meta {
        font-size: 0.8rem;
        color: #666;
        text-transform: uppercase;
        border-top: 1px solid #eee;
        padding-top: 5px;
        margin-top: 10px;
    }
    
    /* Botões */
    .stButton>button {
        background-color: #1a1a1a;
        color: white;
        border-radius: 0;
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        background-color: #333;
        color: white;
        border: 1px solid #000;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES E DADOS ---
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

# --- 3. FUNÇÕES DE BACKEND ---

def conectar_planilha():
    """Conecta ao Google Sheets usando as Secrets do Streamlit"""
    if "GCP_JSON" not in st.secrets:
        st.error("Erro de Configuração: GCP_JSON não encontrado nas Secrets.")
        return None
    try:
        creds_dict = json.loads(st.secrets["GCP_JSON"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("noticias_db").sheet1
    except Exception as e:
        st.error(f"Erro ao conectar no banco de dados: {e}")
        return None

def salvar_assinante(nome, email, temas_selecionados):
    sheet = conectar_planilha()
    if not sheet: return False
    
    # Prepara a linha de dados (Sim/Não para cada tema)
    nova_linha = [nome, email]
    todos_temas = list(RSS_FEEDS.keys())
    
    for tema in todos_temas:
        if tema in temas_selecionados:
            nova_linha.append("Sim")
        else:
            nova_linha.append("Não")
            
    # Adiciona data de inscrição (opcional, se tiver coluna)
    # nova_linha.append(datetime.now().strftime("%Y-%m-%d"))

    try:
        sheet.append_row(nova_linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

@st.cache_data(ttl=1800)
def buscar_noticias(tema):
    url = RSS_FEEDS.get(tema)
    if not url: return []
    try:
        feed = feedparser.parse(url)
        noticias = []
        for entry in feed.entries[:6]:
            img = "https://placehold.co/600x300/EEE/31343C?text=News"
            # Lógica de Imagem Simplificada
            if 'media_content' in entry: img = entry.media_content[0]['url']
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

# --- 4. ÁREA DE ASSINATURA (SIDEBAR) ---
with st.sidebar:
    st.markdown("### ✍️ Assine o Jornal")
    st.write("Receba nossa curadoria diária de notícias diretamente no seu e-mail. Gratuito.")
    
    with st.form("form_assinatura"):
        nome_user = st.text_input("Seu Nome Completo")
        email_user = st.text_input("Seu E-mail")
        
        st.markdown("---")
        st.write("**Quais cadernos você quer receber?**")
        
        # Checkboxes para os temas
        temas_escolhidos = []
        col_cb1, col_cb2 = st.columns(2)
        
        for i, tema in enumerate(RSS_FEEDS.keys()):
            coluna = col_cb1 if i % 2 == 0 else col_cb2
            if coluna.checkbox(tema, value=True):
                temas_escolhidos.append(tema)
                
        st.markdown("---")
        submitted = st.form_submit_button("🗞️ Confirmar Assinatura")
        
        if submitted:
            if nome_user and email_user:
                with st.spinner("Registrando sua assinatura..."):
                    sucesso = salvar_assinante(nome_user, email_user, temas_escolhidos)
                    if sucesso:
                        st.success(f"Bem-vindo(a), {nome_user}! Sua edição chega amanhã às 07:15.")
                        st.balloons()
            else:
                st.warning("Por favor, preencha nome e e-mail.")

# --- 5. JORNAL DO DIA (CORPO PRINCIPAL) ---

# Título Clássico
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)
col_date, col_temp = st.columns([1,1])
col_date.markdown(f"<p style='text-align:center; border-top:1px solid black; border-bottom:1px solid black; padding:5px;'>📅 {datetime.now().strftime('%d de %B de %Y')}</p>", unsafe_allow_html=True)
col_temp.markdown(f"<p style='text-align:center; border-top:1px solid black; border-bottom:1px solid black; padding:5px;'>📍 Edição Global • Online</p>", unsafe_allow_html=True)

st.write("") # Espaço

# Filtro de Visualização
opcoes_temas = ["Capa (Todos)"] + list(RSS_FEEDS.keys())
tema_visualizacao = st.selectbox("Escolha o Caderno para ler agora:", opcoes_temas)

noticias_exibir = []

if tema_visualizacao == "Capa (Todos)":
    # Na capa, pegamos 1 de cada para não ficar gigante
    for t in RSS_FEEDS.keys():
        n = buscar_noticias(t)
        if n: noticias_exibir.append({"tema": t, "data": n[0]})
else:
    raw_news = buscar_noticias(tema_visualizacao)
    for n in raw_news:
        noticias_exibir.append({"tema": tema_visualizacao, "data": n})

# Grid de Notícias Clássico
if noticias_exibir:
    # Cria colunas (Layout tipo Jornal)
    cols = st.columns(3)
    
    for i, item in enumerate(noticias_exibir):
        coluna = cols[i % 3]
        noticia = item['data']
        tema_label = item['tema']
        
        with coluna:
            st.markdown(f"""
            <div class="news-card">
                <img src="{noticia['img']}" style="width:100%; height:150px; object-fit:cover; filter: grayscale(20%); transition: filter 0.3s;">
                <div class="news-text">
                    <div style="font-size:10px; font-weight:bold; letter-spacing:1px; margin-bottom:5px;">{tema_label.upper()}</div>
                    <a href="{noticia['link']}" target="_blank" class="news-title">{noticia['titulo']}</a>
                    <div class="news-meta">Clique para ler na íntegra</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Carregando as manchetes...")

st.markdown("---")
st.markdown("<p style='text-align:center; font-family:Times New Roman;'>© 2025 All News Journal Group. Todos os direitos reservados.</p>", unsafe_allow_html=True)
