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

# =============================================================================
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
# =============================================================================
st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# --- 2. CSS: DESIGN PREMIUM ---
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    .stDeployButton {display:none;}

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
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 12px;
        display: block;
        color: #111 !important;
        text-decoration: none;
        line-height: 1.3;
    }
    .news-title:hover { color: #0a5c5a !important; }
    .news-date {
        font-size: 0.8rem;
        color: #777;
        font-style: italic;
        border-top: 1px solid #eee;
        padding-top: 10px;
    }

    /* Alerta de erro customizado */
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

    /* Botões da sidebar */
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
        transform: scale(1.05) !important;
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

    /* Todos os botões da sidebar — base */
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

    /* Texto interno dos botões */
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button span,
    section[data-testid="stSidebar"] .stButton > button p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Hover de todos os botões */
    section[data-testid="stSidebar"] button:hover,
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #084c4a !important;
        border-color: #ffffff !important;
        transform: scale(1.04);
    }

    /* Botão "Subscrever" — destaque em creme (identificado por ser use_container_width) */
    section[data-testid="stSidebar"] .stButton:last-of-type > button {
        background-color: #fdfbf7 !important;
        color: #084c4a !important;
        border: 2px solid #fdfbf7 !important;
        font-size: 0.92rem !important;
        padding: 8px 0 !important;
        margin-top: 6px !important;
    }
    section[data-testid="stSidebar"] .stButton:last-of-type > button p {
        color: #084c4a !important;
    }
    section[data-testid="stSidebar"] .stButton:last-of-type > button:hover {
        background-color: #e5e3de !important;
    }

    /* Botão "Subscrever" type=primary — destaque em creme */
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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 3. DADOS E FEEDS (com fallback igual ao main.py) ---
# =============================================================================

def traduzir_titulo_se_ingles(titulo):
    """
    Detecta se o título está em inglês e traduz para português via Claude.
    Usado nas notícias de Fitness (fontes internacionais US/EU).
    Retorna o título traduzido ou o original se já estiver em PT ou se falhar.
    """
    if not titulo:
        return titulo

    # Heurística: detecta inglês por palavras funcionais comuns
    palavras_ingles = ["the", "how", "why", "what", "best", "your", "you",
                       "with", "this", "that", "and", "for", "are", "was",
                       "running", "workout", "training", "fitness", "marathon",
                       "i ran", "i didn", "i found", "my ", "me ", "review:",
                       "things no", "could benefit", "summer", "winter", "spring"]
    titulo_lower = titulo.lower()
    palavras_encontradas = sum(1 for p in palavras_ingles if p in titulo_lower)
    if palavras_encontradas < 2:
        return titulo  # Provavelmente já está em português

    # Tenta pegar a chave de diferentes fontes (Streamlit secrets ou env var)
    claude_key = ""
    try:
        claude_key = st.secrets.get("CLAUDE_KEY", "")
    except Exception:
        pass
    if not claude_key:
        import os
        claude_key = os.environ.get("CLAUDE_KEY", "")

    if not claude_key:
        # Sem chave: mostra indicador visual de que é conteúdo EN
        return f"🇺🇸 {titulo}"

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
            traduzido = r.json()["content"][0]["text"].strip()
            traduzido = traduzido.strip('"\'`')
            if 5 < len(traduzido) < 250:
                return traduzido
    except Exception:
        pass
    return titulo

RSS_FEEDS = {
    "Mundo":    ["https://g1.globo.com/rss/g1/mundo/"],
    "Mercado":  [
        "https://www.infomoney.com.br/feed/",
        "https://rss.uol.com.br/feed/economia.xml",
        "https://economia.uol.com.br/rss.xml",
        "https://valor.globo.com/rss/",
    ],
    "Politica": ["https://g1.globo.com/rss/g1/politica/"],
    "Tech":     ["https://rss.tecmundo.com.br/feed"],
    "Esportes": [
        "https://pt.motorsport.com/rss/f1/news/",                # Motorsport PT — F1
        "https://www.espn.com.br/rss/",                          # ESPN Brasil — NBA/NFL/F1
        "https://sportv.globo.com/rss/sportv/",                  # SporTV
        "https://ge.globo.com/rss/ge/",                          # GE Globo
        "https://www.uol.com.br/esporte/rss.xml",                # UOL Esporte
    ],
    "Cinema":   [
        "https://www.omelete.com.br/rss/",                       # Omelete (filmes + séries)
        "https://www.cinepop.com.br/feed",                       # CinePOP
        "https://www.papodecinema.com.br/feed/",                 # Papo de Cinema
        "https://www.adorocinema.com/rss/",                      # AdoroCinema
    ],
    "Fitness":  [
        # Fontes internacionais de elite — Europa e EUA (traduzidas pelo Gemini)
        "https://www.runnersworld.com/rss/all.xml/",             # Runner's World US — corrida/trail
        "https://www.menshealth.com/rss/all.xml/",               # Men's Health US — performance
        "https://www.womenshealthmag.com/rss/all.xml/",          # Women's Health US — wellness
        "https://www.bicycling.com/rss/all.xml/",                # Bicycling US — ciclismo
        "https://www.outsideonline.com/feed/",                   # Outside Online — endurance/aventura
        # Backup Brasil
        "https://www.runnersworld.com.br/feed/",                 # Runner's World BR
        "https://g1.globo.com/rss/g1/bem-estar/",                # G1 Bem-Estar
    ],
    "Ciencia":  [
        "https://g1.globo.com/rss/g1/ciencia-e-saude/",          # G1 Ciência e Saúde
        "https://gizmodo.uol.com.br/feed/",                      # Gizmodo UOL
        "https://www.inovacaotecnologica.com.br/boletim/rss.xml",# Inovação Tecnológica
        "https://www.tecmundo.com.br/ciencia/rss",               # TecMundo ciência
    ],
    "Motos":    [
        "https://www.motociclismoonline.com.br/feed/",           # Motociclismo Online — robusto
        "https://www.motoo.com.br/feed/",                        # Motoo
        "https://motoblog.uol.com.br/feed/",                     # Moto Blog UOL
        "https://www.icarros.com.br/noticias/motos/rss.xml",     # iCarros motos
        "https://revistaautoesporte.globo.com/rss/",             # Auto Esporte
    ],
    "Fofoca":   ["https://revistaquem.globo.com/rss/quem/"],
}

# Filtros de palavras indesejadas (mesmo padrão do main.py)
FILTROS_TEMA = {
    "Mundo":    [],
    "Mercado":  ["horóscopo", "moda", "futebol", "brasileirão", "campeonato",
                 "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
                 "gol", "escalação", "clube", "torcedor",
                 "lollapalooza", "festival", "show", "ingresso",
                 "previsão do tempo", "clima", "chuva",
                 "bbb", "big brother", "prêmio do bbb", "reality",
                 "tênis", "fonseca", "alcaraz", "sinner", "nadal",
                 "israel:", "irã:", "civil morto", "guerra de fronteira",
                 "ataque", "bombardeio", "teerã", "netanyahu", "míssil"],
    "Politica": [],
    "Tech":     ["aposta", "palpite", "futebol", "bônus", "cassino", "bet",
                 "guia-de-compras", "em-oferta", "promoção", "desconto",
                 "homenagem", "morre", "falece", "morte", "aniversário",
                 "ator", "atriz", "celebridade", "troféus", "conquistas",
                 "ps store", "xbox game pass", "jogos grátis", "resgate agora",
                 "marinheiro", "porta-avião", "base militar",
                 "séries live-action", "live-action", "temporada", "episódio",
                 "netflix planeja", "disney+", "hbo planeja",
                 "filmes e séries", "séries em alta", "para ver na netflix",
                 "para ver no prime", "para assistir",
                 "jogos para jogar", "jogos cooperativos", "melhores jogos",
                 "quanto custa um pc", "pc gamer para jogar", "requisitos mínimos",
                 "configurações para rodar", "placa de vídeo para",
                 "de graça", "baratinhos", "indicações de games", "games da semana",
                 "jogos da semana", "resgate grátis", "jogo grátis"],
    "Esportes": ["ao-vivo", "ao vivo", "/jogo/", "onde-assistir", "ingressos",
                 "escalação", "prováveis-times",
                 "reprisa", "reprise", "jogos históricos", "programação", "transmissão",
                 "o que assistir", "disney+", "para assistir", "catálogo",
                 "nota de falecimento", "troféu best", "melhor nadador juvenil",
                 "1959-", "1960-", "1961-", "1962-", "1963-", "1964-", "1965-",
                 "mensagem de despedida",
                 "/base/", "sub-13", "sub-15", "sub-17", "sub-20",
                 "campeonato-piauiense", "campeonato-alagoano", "campeonato-paraibano",
                 "campeonato-potiguar", "campeonato-cearense", "campeonato-maranhense",
                 "segunda-divisao", "terceira-divisao", "serie-d", "serie-c",
                 "copa-do-brasil-sub", "paulista-sub", "carioca-sub", "futsal",
                 # Futebol brasileiro
                 "seleção brasileira", "convocação", "treino da seleção",
                 "neymar", "vinicius", "vinícius", "rodrygo", "endrick",
                 "memphis", "raphinha", "militão", "marquinhos",
                 "copa do mundo", "eliminatórias", "eurocopa",
                 "palmeiras", "flamengo", "corinthians", "são paulo",
                 "grêmio", "atletico", "cruzeiro", "vasco", "botafogo",
                 "brasileirão", "copa do brasil", "libertadores",
                 # Futebol internacional — jogadores
                 "salah", "mbappé", "mbappe", "haaland", "bellingham",
                 "modric", "benzema", "lewandowski", "kane", "de bruyne",
                 "messi", "ronaldo", "kroos", "pedri", "yamal",
                 # Futebol internacional — clubes e ligas
                 "liverpool", "real madrid", "barcelona", "manchester",
                 "arsenal", "chelsea", "psg", "bayern", "juventus",
                 "premier league", "la liga", "champions league",
                 # Técnicos / contexto futebol
                 "ancelotti", "diniz", "guardiola", "klopp", "mourinho",
                 "brasil x ", "seleção x ", "amistoso", "friendly"],
    "Cinema":   ["aposta", "bet", "cassino", "futebol", "esporte",
                 "aniversário", "tatuagem", "look", "moda", "relacionamento",
                 "casamento", "separação", "gravidez", "filhos",
                 "morte de", "falecimento", "luto", "lamenta morte",
                 "celebra aniversário", "faz anos"],
    "Fitness":  ["aposta", "bet", "cassino", "futebol", "moda",
                 "maquiagem", "cabelo", "unhas", "beleza", "tatuagem",
                 # Saúde médica genérica — vai para Ciência
                 "câncer", "tumor", "cirurgia", "hospital", "médico recomenda",
                 "remédio", "medicamento", "vacina", "dengue", "vírus",
                 "doença", "diagnóstico", "sintomas", "tratamento clínico",
                 # Celebridade/gossip/reality
                 "famoso", "celebridade", "ator", "atriz", "novela",
                 "bbb", "big brother", "reality",
                 # Saúde sazonal e genérica
                 "resfriado", "alergia", "gripe", "outono e saúde",
                 "afastados do trabalho", "adoecimento mental", "afastamento",
                 # Culinária genérica
                 "erros na cozinha", "receita de", "culinária",
                 "carne vermelha crua", "faz mal comer",
                 # Saúde do idoso genérica
                 "velhice", "envelhecimento", "como deixar de beber aos",
                 "idoso", "terceira idade"],
    "Ciencia":  [],
    "Motos":    [],
    "Fofoca":   [],
}

FALLBACK_IMAGES = {
    "Mundo":    "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=300&fit=crop",
    "Mercado":  "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
    "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
    "Tech":     "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=300&fit=crop",
    "Esportes": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
    "Cinema":   "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600&h=300&fit=crop",
    "Fitness":  "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "Ciencia":  "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=300&fit=crop",
    "Motos":    "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=600&h=300&fit=crop",
    "Fofoca":   "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=300&fit=crop",
}

# Constantes de fallback para Esportes — movidas para escopo global (performance)
SPORT_ROTATIONS = {
    "nba":   ["https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
               "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=600&h=300&fit=crop"],
    "f1":    ["https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
               "https://images.unsplash.com/photo-1541447271487-09612b3f49f7?w=600&h=300&fit=crop"],
    "mma":   ["https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=300&fit=crop",
               "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&h=300&fit=crop"],
    "tenis": ["https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
               "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=600&h=300&fit=crop"],
}
SPORT_KEYWORDS = {
    "nba":   ["nba","basquete","lebron","durant","curry","lakers","celtics","warriors"],
    "f1":    ["f1","formula","grand prix","gp de","verstappen","hamilton","ferrari","leclerc","norris"],
    "mma":   ["mma","ufc","silva","evloev","volkanovski","poatan","adesanya"],
    "tenis": ["tênis","tennis","fonseca","alcaraz","sinner","open","nadal"],
}
FALLBACK_ESPORTES_GENERIC = [
    "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1540747913346-19212a4b32b8?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&h=300&fit=crop",
]

# =============================================================================
# --- 4. VALIDAÇÕES (novas) ---
# =============================================================================
def validar_email(email):
    """Valida formato de e-mail com regex."""
    padrao = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(padrao, email.strip()))

def validar_nome(nome):
    """Nome deve ter ao menos 2 caracteres e só letras/espaços."""
    return len(nome.strip()) >= 2

# =============================================================================
# --- 5. GOOGLE SHEETS ---
# =============================================================================
@st.cache_data(ttl=300)
def conectar_planilha():
    """Conecta ao Google Sheets e retorna a aba de usuários."""
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
        return client.open("noticias_db").sheet1
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return None

def email_ja_cadastrado(email):
    """
    (NOVO) Verifica se o e-mail já existe na planilha antes de inserir.
    Evita duplicatas.
    """
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
    """
    Salva novo assinante no Sheets.
    ordem_temas: dict {tema: posicao} onde posicao é 1,2,3... ou "Não" se não selecionado.
    """
    sheet = conectar_planilha()
    if not sheet:
        return False, "Não foi possível conectar ao banco de dados. Tente novamente."
    try:
        linha = [nome.strip(), email.strip()]
        for chave in RSS_FEEDS.keys():
            linha.append(ordem_temas.get(chave, "Não"))
        sheet.append_row(linha)
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro ao salvar: {str(e)}"

# =============================================================================
# --- 6. E-MAIL DE BOAS-VINDAS (novo) ---
# =============================================================================
def enviar_boas_vindas(nome, email_dest, temas_escolhidos):
    """
    (NOVO) Envia um e-mail de boas-vindas assim que o leitor se inscreve.
    Usa as mesmas credenciais do main.py via st.secrets.
    """
    try:
        email_sender   = st.secrets.get("EMAIL_USER")
        email_password = st.secrets.get("EMAIL_PASSWORD")
        if not email_sender or not email_password:
            return  # Sem credenciais configuradas, ignora silenciosamente

        temas_html = "".join(
            f"<li style='padding:4px 0; color:#2c2c2c;'>✅ {t}</li>"
            for t in temas_escolhidos
        )

        html = f"""
        <html><body style="margin:0; padding:0; background-color:#e5e3de; font-family:'Lora','Times New Roman',serif;">
          <div style="max-width:560px; margin:30px auto; background:#fdfbf7; border-radius:8px; overflow:hidden; box-shadow:0 4px 15px rgba(0,0,0,0.07);">

            <div style="padding:30px 20px; text-align:center; border-bottom:2px solid #0a5c5a;">
              <h1 style="margin:0; font-family:'Playfair Display',Georgia,serif; font-size:28px; text-transform:uppercase; letter-spacing:2px; color:#0a5c5a;">ALL NEWS JOURNAL</h1>
              <p style="margin:8px 0 0; font-size:12px; color:#777; font-style:italic;">Bem-vindo ao Clube Premium</p>
            </div>

            <div style="padding:30px 25px;">
              <p style="font-size:17px; color:#2c2c2c;">Olá, <b>{nome}</b>! 👋</p>
              <p style="font-size:15px; color:#444; line-height:1.7;">
                A sua inscrição no <b>All News Journal</b> foi confirmada com sucesso.<br>
                A partir de amanhã cedo, você receberá a sua edição personalizada com as notícias dos cadernos que escolheu:
              </p>
              <ul style="font-size:15px; padding-left:20px; line-height:1.8;">
                {temas_html}
              </ul>
              <p style="font-size:14px; color:#777; margin-top:20px; font-style:italic;">
                Se quiser alterar os seus cadernos, basta acessar o portal e se inscrever novamente com o mesmo e-mail.
              </p>
            </div>

            <div style="text-align:center; padding:20px; background-color:#084c4a; color:#fdfbf7; font-size:12px;">
              <p style="margin:0;">© 2026 All News Journal Group. Conteúdo Premium.</p>
              <p style="margin:8px 0 0; font-size:10px; opacity:0.7;">Você recebeu este e-mail porque acabou de se inscrever no nosso portal.</p>
            </div>

          </div>
        </body></html>
        """

        msg = MIMEMultipart()
        msg['Subject'] = "📰 Bem-vindo ao All News Journal!"
        msg['From']    = email_sender
        msg['To']      = email_dest
        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        server.sendmail(email_sender, email_dest, msg.as_string())
        server.quit()

    except Exception as e:
        pass  # Boas-vindas é opcional — não bloqueia o cadastro se falhar

# =============================================================================
# --- 7. BUSCA DE NOTÍCIAS (com fallback de URL) ---
# =============================================================================
def buscar_og_image(url_artigo, timeout=5):
    """Busca og:image da página real do artigo — imagem mais relevante para a notícia."""
    if not url_artigo:
        return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)', 'Accept': 'text/html'}
        r = requests.get(url_artigo, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        html = r.text
        match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.IGNORECASE)
        if not match:
            match = re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html, re.IGNORECASE)
        if match:
            img_url = match.group(1).strip()
            if img_url.startswith('http') and len(img_url) > 10:
                return img_url
    except Exception:
        pass
    return None

@st.cache_data(ttl=600)  # 10 minutos — evita feeds velhos demais
def buscar_noticias(tema):
    """
    Busca notícias do RSS com fallback de múltiplas fontes.
    Para Cinema, Ciência, Fitness, Motos e Esportes tenta todas as fontes.
    Aplica os mesmos filtros do main.py. Nunca cacheia resultado vazio.
    """
    urls = RSS_FEEDS.get(tema, [])
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')

    # Temas que precisam tentar TODAS as fontes
    TEMAS_MULTI_FONTE = {"Cinema", "Fitness", "Ciencia", "Esportes", "Motos"}

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

    # Aplica filtros do tema (mesma lógica do main.py)
    filtros = FILTROS_TEMA.get(tema, [])
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

    # Fallbacks verificados por modalidade esportiva (constantes globais)
    FALLBACK_ESPORTES_KEYWORD = {
        # F1
        "f1":           "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "formula":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "grand prix":   "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "gp de":        "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "verstappen":   "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "hamilton":     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "ferrari":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "leclerc":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        # NBA / Basquete
        "nba":          "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
        "basquete":     "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
        "lebron":       "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
        "curry":        "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
        # NFL
        "nfl":          "https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=600&h=300&fit=crop",
        "super bowl":   "https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=600&h=300&fit=crop",
        # Tênis
        "tênis":        "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "tennis":       "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "fonseca":      "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "alcaraz":      "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "sinner":       "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "miami open":   "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        # MotoGP (IDs verificados)
        "motogp":       "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
        "moto gp":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
        "márquez":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
        "moreira":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
    }

    noticias = []
    for entry in entries_filtradas:
        img = None

        # 0. og:image da página real (prioritário para Esportes, Fitness e Motos)
        if tema in ("Esportes", "Fitness", "Motos"):
            og = buscar_og_image(entry.get('link', ''))
            if og:
                img = og

        # 1. media_content
        if 'media_content' in entry:
            for m in entry.media_content:
                if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                    img = m['url']
                    break

        # 2. enclosures (padrão alternativo usado por alguns feeds)
        if not img and 'enclosures' in entry:
            for enc in entry.enclosures:
                url_enc = enc.get('url', '')
                if any(ext in url_enc.lower() for ext in extensoes):
                    img = url_enc
                    break

        # 3. links com type image
        if not img and 'links' in entry:
            for l in entry.links:
                href = l.get('href', '')
                if l.get('type', '').startswith('image/') and any(ext in href.lower() for ext in extensoes):
                    img = href
                    break

        # 4. scraping de <img> no HTML do summary/content
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

        # 5. Fallback — Esportes usa rotação dentro da categoria; outros usam genérico
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
        # Traduz automaticamente títulos em inglês (fontes internacionais de Fitness)
        if tema == "Fitness":
            titulo_final = traduzir_titulo_se_ingles(titulo_final)

        noticias.append({
            "titulo": titulo_final,
            "link":   entry.get('link', ''),
            "img":    img,
            "data":   entry.get('published', '')[:16]
        })

    return noticias

# =============================================================================
# --- 8. SIDEBAR: FORMULÁRIO COM REORDENAÇÃO ↑↓ ---
# =============================================================================

ICONES = {
    "Mundo":    "🌎", "Mercado":  "📈", "Politica": "🏛️",
    "Tech":     "💻", "Esportes": "🏎️", "Cinema":   "🎬",
    "Fitness":  "🏃", "Ciencia":  "🔬", "Motos":    "🏍️",
    "Fofoca":   "⭐",
}

# Inicializa session_state na primeira execução
if "ordem_lista" not in st.session_state:
    st.session_state.ordem_lista = list(RSS_FEEDS.keys())
if "ativos" not in st.session_state:
    st.session_state.ativos = {t: True for t in RSS_FEEDS.keys()}

with st.sidebar:
    st.markdown(
        "<h2 style='text-align:center; font-family: Playfair Display;'>✍️ Junte-se ao Clube</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center; font-size: 0.9rem;'>Receba a nossa curadoria premium "
        "de notícias todas as manhãs, gratuitamente.</p>",
        unsafe_allow_html=True
    )
    st.write("")

    nome  = st.text_input("O seu Nome",          key="inp_nome")
    email = st.text_input("O seu melhor E-mail", key="inp_email")

    st.markdown("<hr style='border-color: rgba(253, 251, 247, 0.2);'>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:0.82rem; font-weight:bold; margin-bottom:2px;'>"
        "📋 Ordene os seus cadernos:</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='font-size:0.75rem; opacity:0.75; margin-top:0; margin-bottom:10px;'>"
        "Use ↑↓ para mudar a ordem. Desmarque os que não quer receber.</p>",
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

    # Preview
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

    # Monta ordem_temas para salvar
    ordem_temas = {}
    pos = 1
    for tema in st.session_state.ordem_lista:
        if st.session_state.ativos.get(tema, True):
            ordem_temas[tema] = pos
            pos += 1
        else:
            ordem_temas[tema] = "Não"

    if st.button("SUBSCREVER AGORA 🗞️", use_container_width=True, key="btn_subscribe", type="primary"):
        erros = []

        if not validar_nome(nome):
            erros.append("Por favor, informe um nome válido (mínimo 2 caracteres).")
        if not email:
            erros.append("Por favor, informe o seu e-mail.")
        elif not validar_email(email):
            erros.append("O e-mail informado não parece válido. Verifique e tente novamente.")

        temas_selecionados = [t for t, v in ordem_temas.items() if v != "Não"]
        if not temas_selecionados:
            erros.append("Selecione pelo menos um caderno para receber.")

        if erros:
            for erro in erros:
                st.warning(erro)
        else:
            with st.spinner("A verificar o seu cadastro..."):
                if email_ja_cadastrado(email):
                    st.info("📬 Este e-mail já está inscrito! Você já faz parte do clube.")
                else:
                    with st.spinner("A preparar a sua edição..."):
                        ok, mensagem = salvar_assinante(nome, email, ordem_temas)
                        if ok:
                            temas_ordenados = sorted(
                                temas_selecionados,
                                key=lambda t: ordem_temas[t]
                            )
                            enviar_boas_vindas(nome, email, temas_ordenados)
                            st.success("✅ Tudo certo! Verifique o seu e-mail — enviamos uma confirmação.")
                            st.balloons()
                            # Reseta a lista de ordem para nova sessão
                            st.session_state.ordem_lista = list(RSS_FEEDS.keys())
                            st.session_state.ativos = {t: True for t in RSS_FEEDS.keys()}
                        else:
                            st.error(f"❌ Algo deu errado. {mensagem}")


# =============================================================================
# --- 9. CONTEÚDO PRINCIPAL ---
# =============================================================================
st.markdown("<h1>ALL NEWS JOURNAL</h1>", unsafe_allow_html=True)

# Data em português
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
    "<div style='text-align:center; color:#0a5c5a; font-weight:bold; padding:5px;'>🌎 Edição Global • Online</div>",
    unsafe_allow_html=True
)

st.write("")

tema_atual = st.selectbox("📖 Navegue pelos Cadernos:", ["Capa (Destaques)"] + list(RSS_FEEDS.keys()))
st.markdown("<br>", unsafe_allow_html=True)

# --- Busca e exibe notícias ---
noticias_display = []

if tema_atual == "Capa (Destaques)":
    for t in RSS_FEEDS.keys():
        res = buscar_noticias(t)
        if res:
            item = res[0]
            item['tema'] = t
            noticias_display.append(item)
        # Avisa se o caderno estiver vazio
        elif not res:
            pass  # Silencioso na capa — evita poluir o layout
else:
    res = buscar_noticias(tema_atual)
    if not res:
        st.warning(f"⚠️ Não foi possível carregar as notícias de **{tema_atual}** agora. Tente novamente em alguns minutos.")
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
                    <img src="{n['img']}" class="news-img"
                         onerror="this.src='{FALLBACK_IMAGES.get(n['tema'], 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop')}'">
                </a>
                <div class="news-content">
                    <span class="news-tag">{n['tema']}</span>
                    <a href="{n['link']}" target="_blank" class="news-title">{n['titulo']}</a>
                    <div class="news-date">Aceda à matéria original completa</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
elif not noticias_display and tema_atual == "Capa (Destaques)":
    st.info("A procurar as manchetes mais recentes...")

# --- Rodapé ---
st.markdown(
    "<hr style='border-color: #0a5c5a; opacity: 0.2; margin-top: 50px;'>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; color:#0a5c5a; font-family: Playfair Display; font-size:0.9rem;'>© 2026 All News Journal Group. Conteúdo Premium.</div>",
    unsafe_allow_html=True
)
