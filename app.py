"""
All News Journal - Portal Streamlit
Preview das notícias e formulário de assinatura.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from config import ORDEM_CADERNOS, ICONES_TEMA

BASE_DIR = Path(__file__).resolve().parent
SUBSCRIBERS_FILE = BASE_DIR / "subscribers.json"
PREVIEW_FILE = BASE_DIR / "preview.html"
BRT = timezone(timedelta(hours=-3))

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="All News Journal",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tema visual turquesa + creme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    .block-container {padding-top: 1.5rem;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #0a5c5a 0%, #0d7a77 60%, #0a5c5a 100%);
    }
    [data-testid="stSidebar"] * {color: #f5f0e8 !important;}
    [data-testid="stSidebar"] input {
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(245,240,232,0.4) !important;
        color: #f5f0e8 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] .stTextInput label {color: #f5f0e8 !important;}
    [data-testid="stSidebar"] .stCheckbox label {color: #f5f0e8 !important;}
    [data-testid="stSidebar"] .stButton button {
        background: #f5f0e8 !important;
        color: #0a5c5a !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        width: 100%;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: #e8e0d0 !important;
    }

    /* Hero */
    .hero-title {
        font-family: 'Playfair Display', 'Times New Roman', serif;
        font-size: 3rem;
        font-weight: 700;
        color: #0a5c5a;
        text-align: center;
        letter-spacing: 3px;
        margin-bottom: 0;
        line-height: 1.1;
    }
    .hero-rule {
        border: none;
        border-top: 3px solid #0a5c5a;
        margin: 10px auto 0;
        width: 80px;
    }

    .stat-card {
        background: #f8f5f0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #e0d8cc;
    }
    .stat-card h3 {color: #0a5c5a; font-size: 2rem; margin: 0;}
    .stat-card p {color: #6c757d; margin: 0.25rem 0 0;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def load_subscribers() -> list[str]:
    if not SUBSCRIBERS_FILE.exists():
        return []
    data = json.loads(SUBSCRIBERS_FILE.read_text(encoding="utf-8"))
    return [e for e in data if isinstance(e, str) and "@" in e]


def save_subscriber(email: str) -> bool:
    subscribers = load_subscribers()
    if email in subscribers:
        return False
    subscribers.append(email)
    SUBSCRIBERS_FILE.write_text(
        json.dumps(subscribers, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True


def remove_subscriber(email: str) -> bool:
    subscribers = load_subscribers()
    if email not in subscribers:
        return False
    subscribers.remove(email)
    SUBSCRIBERS_FILE.write_text(
        json.dumps(subscribers, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True

# ---------------------------------------------------------------------------
# Sidebar — Formulário de assinatura
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        "<h2 style='text-align:center; font-family: Playfair Display, serif; margin-bottom:4px;'>"
        "✍️ Assine o All News Journal</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; font-size: 0.88rem; opacity:0.9;'>"
        "Receba sua edição personalizada todas as manhãs. "
        "Escolha os cadernos, defina a ordem, e nós cuidamos do resto.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    with st.form("subscribe_form"):
        email_input = st.text_input("Seu melhor e-mail", placeholder="voce@email.com")
        st.markdown("<p style='font-size:0.82rem; opacity:0.8;'>Cadernos incluídos na edição diária:</p>", unsafe_allow_html=True)
        for tema in ORDEM_CADERNOS:
            st.markdown(f"<span style='font-size:0.9rem;'>{ICONES_TEMA[tema]} {tema}</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("📬 Assinar gratuitamente", type="primary", use_container_width=True)

        if submitted:
            if not email_input or "@" not in email_input or "." not in email_input:
                st.error("Por favor, insira um e-mail válido.")
            else:
                if save_subscriber(email_input.strip().lower()):
                    st.success(f"Pronto! {email_input} cadastrado com sucesso! 🎉")
                else:
                    st.warning("Este e-mail já está cadastrado.")

    st.divider()
    subscribers = load_subscribers()
    st.caption(f"📊 {len(subscribers)} assinante(s) cadastrado(s)")

    st.markdown(
        "<p style='font-size:0.78rem; opacity:0.7; text-align:center;'>"
        "Entrega às 6h todos os dias. Gratuito. Cancele quando quiser.</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header principal
# ---------------------------------------------------------------------------

st.markdown('<h1 class="hero-title">ALL NEWS JOURNAL</h1>', unsafe_allow_html=True)
st.markdown('<hr class="hero-rule">', unsafe_allow_html=True)

# Manifesto editorial
st.markdown("""
<div style='
    max-width: 720px;
    margin: 25px auto 35px;
    padding: 0 20px;
    text-align: center;
    font-family: "Lora", "Times New Roman", serif;
    color: #2c2c2c;
    line-height: 1.7;
    font-size: 1.05rem;
'>
  <p style='font-style: italic; color: #0a5c5a; font-size: 1.15rem; margin-bottom: 18px;'>
    Notícias relevantes, sem ruído, todas as manhãs.
  </p>
  <p>
    O <b>All News Journal</b> é um jornal digital independente que entrega na sua
    caixa de e-mail, todos os dias às 6h, uma edição <b>personalizada</b> com os
    cadernos que você escolheu — e apenas eles.
  </p>
  <p>
    Cada manchete é resumida por nossa redação editorial em parágrafos completos
    e autossuficientes. Você lê em cinco minutos o que importou no mundo e começa
    o dia informado, sem rolar timeline, sem clicar em link nenhum.
  </p>
  <p style='margin-top: 22px; font-size: 0.95rem; color: #555;'>
    Assine na barra lateral. É gratuito.
  </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs de conteúdo
# ---------------------------------------------------------------------------

tab_preview, tab_cancelar, tab_sobre = st.tabs(["📖 Última Edição", "❌ Cancelar Assinatura", "ℹ️ Sobre"])

# -- Tab: Preview --
with tab_preview:
    if PREVIEW_FILE.exists():
        html_content = PREVIEW_FILE.read_text(encoding="utf-8")
        mod_time = datetime.fromtimestamp(PREVIEW_FILE.stat().st_mtime, tz=BRT)
        st.caption(f"Última atualização: {mod_time.strftime('%d/%m/%Y às %H:%M')}")
        st.components.v1.html(html_content, height=900, scrolling=True)
    else:
        st.info(
            "Nenhuma edição gerada ainda. Execute o pipeline primeiro:\n\n"
            "```\npython main.py --dry-run\n```"
        )

# -- Tab: Cancelar --
with tab_cancelar:
    st.subheader("Cancelar assinatura")
    st.write("Informe seu e-mail abaixo para ser removido da lista.")

    with st.form("cancel_form"):
        cancel_email = st.text_input("Seu e-mail cadastrado", placeholder="voce@email.com")
        cancel_submitted = st.form_submit_button("Cancelar assinatura", type="secondary")

        if cancel_submitted:
            if not cancel_email or "@" not in cancel_email:
                st.error("Por favor, insira um e-mail válido.")
            else:
                if remove_subscriber(cancel_email.strip().lower()):
                    st.success(f"{cancel_email} removido com sucesso.")
                else:
                    st.warning("E-mail não encontrado na lista.")

# -- Tab: Sobre --
with tab_sobre:
    st.subheader("Sobre o All News Journal")
    st.markdown("""
    O **All News Journal** é um jornal digital automatizado que:

    1. **Coleta** notícias de fontes brasileiras e internacionais via RSS
    2. **Filtra** conteúdo indesejado por caderno (apostas, loteria, horóscopo, spam)
    3. **Reescreve** resumos usando inteligência artificial (Claude/Anthropic) com instrução editorial específica por caderno
    4. **Envia** um e-mail formatado para os assinantes toda manhã às 6h

    ### Os 8 Cadernos
    """)

    cadernos_info = {
        "Mundo":    ("🌎", "Geopolítica, relações internacionais, conflitos, eventos globais"),
        "Economia": ("📈", "Mercados, ações, empresas, macro, política monetária"),
        "Politica": ("🏛️", "Política institucional brasileira, simplificada e neutra"),
        "IA":       ("🤖", "OpenAI, Anthropic, Google AI, modelos, papers, regulação de IA"),
        "Wellness": ("🏃", "Endurance, corrida, ciclismo, musculação, nutrição, mindset, sono"),
        "Ciencia":  ("🔬", "Pesquisa, descobertas, saúde científica, espaço"),
        "Cinema":   ("🎬", "Filmes, séries, streaming, festivais, crítica"),
        "Fofoca":   ("⭐", "Cultura pop INTERNACIONAL: Hollywood, K-pop, realeza, viral global"),
    }

    for nome, (icone, descricao) in cadernos_info.items():
        st.markdown(f"**{icone} {nome}** — {descricao}")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="stat-card"><h3>8</h3><p>Cadernos</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="stat-card"><h3>40+</h3><p>Fontes RSS</p></div>', unsafe_allow_html=True)
    with col3:
        n = len(load_subscribers())
        st.markdown(f'<div class="stat-card"><h3>{n}</h3><p>Assinantes</p></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    ### Tecnologias
    - **Python** — Linguagem principal
    - **Claude (Anthropic)** — Reescrita editorial com IA
    - **Streamlit** — Este portal web
    - **GitHub Actions** — Automação diária às 6h BRT
    """)
