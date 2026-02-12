import streamlit as st
import feedparser
import requests
import pandas as pd
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Personalizado (Para ficar igual ao E-mail)
st.markdown("""
<style>
    .card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #333;
    }
    .card h3 { margin-top: 0; color: #111; }
    .card a { text-decoration: none; color: #007bff; font-weight: bold; }
    .card a:hover { text-decoration: underline; }
    .metric-container { background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. DADOS E FEEDS ---
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

# --- 3. FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=3600) # Cache de 1 hora para não ficar lento
def buscar_noticias(tema):
    url = RSS_FEEDS.get(tema)
    if not url: return []
    
    try:
        feed = feedparser.parse(url)
        noticias = []
        for entry in feed.entries[:5]: # Top 5 notícias
            # Tenta extrair imagem
            img = "https://placehold.co/600x200/EEE/31343C?text=News&font=roboto"
            if 'media_content' in entry:
                img = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if link.get('type', '').startswith('image/'):
                        img = link.get('href'); break
            
            noticias.append({
                "titulo": entry.title,
                "link": entry.link,
                "img": img,
                "data": entry.get('published', '')[:16]
            })
        return noticias
    except:
        return []

def pegar_cotacao():
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL")
        return resp.json()
    except: return None

# --- 4. INTERFACE PRINCIPAL ---

# Cabeçalho
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📰 All News Journal")
    st.caption(f"Edição ao Vivo • {datetime.now().strftime('%d/%m/%Y')}")

# Painel Financeiro (Sidebar ou Topo)
cotacoes = pegar_cotacao()
if cotacoes:
    usd = float(cotacoes['USDBRL']['bid'])
    usd_var = float(cotacoes['USDBRL']['pctChange'])
    btc = float(cotacoes['BTCBRL']['bid'])
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Dólar (USD)", f"R$ {usd:.2f}", f"{usd_var}%")
    col_b.metric("Bitcoin (BTC)", f"R$ {btc/1000:.1f}k", f"{float(cotacoes['BTCBRL']['pctChange'])}%")

st.divider()

# Sidebar de Navegação
st.sidebar.header("Filtros")
tema_selecionado = st.sidebar.radio("Escolha o Caderno:", list(RSS_FEEDS.keys()))

# Botão de Atualizar Manual
if st.sidebar.button("🔄 Atualizar Feed"):
    st.cache_data.clear()

# --- 5. EXIBIÇÃO DAS NOTÍCIAS ---
st.subheader(f"Destaques de {tema_selecionado}")

news = buscar_noticias(tema_selecionado)

if news:
    for n in news:
        # Layout de Cartão
        with st.container():
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(n['img'], use_column_width=True)
            with c2:
                st.markdown(f"### [{n['titulo']}]({n['link']})")
                st.caption(f"Publicado em: {n['data']}")
                st.write("Clique no título para ler a matéria completa na fonte original.")
            st.divider()
else:
    st.warning("Não foi possível carregar as notícias deste tema no momento.")

# Rodapé
st.markdown("---")
st.markdown("© 2025 All News Journal • Tecnologia Streamlit & Python")
