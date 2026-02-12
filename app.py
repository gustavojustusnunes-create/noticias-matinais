import streamlit as st
import feedparser
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS (Modo Escuro/Claro automático)
st.markdown("""
<style>
    .stApp { margin-top: -30px; }
    .card-container {
        background-color: #262730; /* Fundo escuro padrão Streamlit */
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #444;
    }
    a { text-decoration: none; font-weight: bold; color: #4da6ff !important; }
    a:hover { text-decoration: underline; }
    h3 { margin-top: 0 !important; padding-top: 0 !important; }
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

# --- 3. FUNÇÕES ROBUSTAS ---

@st.cache_data(ttl=900) # Cache de 15 min para não travar
def pegar_cotacao():
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,BTC-BRL", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

@st.cache_data(ttl=1800) # Cache de 30 min para notícias
def buscar_noticias(tema):
    url = RSS_FEEDS.get(tema)
    if not url: return []
    
    noticias = []
    try:
        feed = feedparser.parse(url)
        if not feed.entries: return []
        
        for entry in feed.entries[:6]: # Top 6 notícias
            try:
                # Lógica de Imagem (A mesma do robô de e-mail)
                img = None
                
                # Tenta media_content
                if 'media_content' in entry:
                    for m in entry.media_content:
                        if 'image' in m.get('type', '') or 'jpg' in m.get('url', ''):
                            img = m['url']; break
                
                # Tenta links
                if not img and 'links' in entry:
                    for link in entry.links:
                        if link.get('type', '').startswith('image/'):
                            img = link.get('href'); break
                
                # Placeholder se não achar nada
                if not img:
                    cor = "333"
                    if tema == "Mercado": cor = "27ae60"
                    if tema == "Tech": cor = "2980b9"
                    img = f"https://placehold.co/600x300/{cor}/FFF?text={tema}&font=roboto"

                noticias.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "img": img,
                    "resumo": entry.get('summary', 'Clique para ler mais.')[:150] + "..."
                })
            except Exception as e:
                continue # Se uma notícia der erro, pula para a próxima (não quebra o site)
                
    except Exception as e:
        st.error(f"Erro ao ler feed: {e}")
        return []
        
    return noticias

# --- 4. INTERFACE ---

# Topo: Cotações
cotacoes = pegar_cotacao()
col_metrics = st.columns(4)

if cotacoes:
    usd = float(cotacoes['USDBRL']['bid'])
    var_usd = float(cotacoes['USDBRL']['pctChange'])
    btc = float(cotacoes['BTCBRL']['bid'])
    var_btc = float(cotacoes['BTCBRL']['pctChange'])
    
    col_metrics[0].metric("🇺🇸 Dólar", f"R$ {usd:.2f}", f"{var_usd}%")
    col_metrics[1].metric("₿ Bitcoin", f"R$ {btc/1000:.1f}k", f"{var_btc}%")

# Título
st.title("📰 All News Journal")
st.markdown(f"**Edição em Tempo Real** • {datetime.now().strftime('%d/%m/%Y')}")
st.divider()

# Sidebar
with st.sidebar:
    st.header("Explorar")
    tema_selecionado = st.radio("Selecione o Caderno:", list(RSS_FEEDS.keys()))
    st.markdown("---")
    if st.button("🔄 Atualizar Tudo"):
        st.cache_data.clear()

# Área de Notícias
st.subheader(f"Destaques: {tema_selecionado}")

news = buscar_noticias(tema_selecionado)

if news:
    # Grid de Notícias (2 colunas)
    row1 = st.columns(2)
    row2 = st.columns(2)
    row3 = st.columns(2)
    grid_slots = row1 + row2 + row3 # Lista de 6 slots
    
    for i, n in enumerate(news):
        if i < len(grid_slots):
            with grid_slots[i]:
                # Cartão Visual
                st.image(n['img'], use_column_width=True)
                st.markdown(f"#### [{n['titulo']}]({n['link']})")
                st.caption(n['resumo'])
                st.markdown("---")
else:
    st.info("Nenhuma notícia carregada. Tente atualizar a página.")
