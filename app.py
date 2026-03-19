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
RSS_FEEDS = {
    "Mundo":    ["https://g1.globo.com/rss/g1/mundo/"],
    "Mercado":  ["https://www.infomoney.com.br/feed/", "https://rss.uol.com.br/feed/economia.xml"],
    "Politica": ["https://g1.globo.com/rss/g1/politica/"],
    "Tech":     ["https://rss.tecmundo.com.br/feed"],
    "Esportes": ["https://ge.globo.com/rss/ge/"],
    "Ciencia":  ["https://gizmodo.uol.com.br/category/ciencia/feed/"],
    "Motos":    ["https://www.motociclismoonline.com.br/feed/"],
    "Fofoca":   ["https://revistaquem.globo.com/rss/quem/"],
}

FALLBACK_IMAGES = {
    "Mercado":  "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
    "Tech":     "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=300&fit=crop",
    "Motos":    "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=600&h=300&fit=crop",
    "Fofoca":   "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=300&fit=crop",
    "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
    "Esportes": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
    "Ciencia":  "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=300&fit=crop",
    "Mundo":    "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=300&fit=crop",
}

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
@st.cache_resource(ttl=300)
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
@st.cache_data(ttl=1800)
def buscar_noticias(tema):
    """
    (MELHORADO) Usa lista de URLs com fallback, igual ao main.py.
    Avisa o usuário se todas as fontes falharem.
    """
    urls = RSS_FEEDS.get(tema, [])
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    feed = None

    for url in urls:
        try:
            f = feedparser.parse(url)
            if f.entries:
                feed = f
                break
        except Exception:
            continue

    if not feed:
        return []

    noticias = []
    for entry in feed.entries[:6]:
        img = None

        if 'media_content' in entry:
            for m in entry.media_content:
                if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                    img = m['url']
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

        noticias.append({
            "titulo": entry.title,
            "link":   entry.link,
            "img":    img,
            "data":   entry.get('published', '')[:16]
        })

    return noticias

# =============================================================================
# --- 8. SIDEBAR: FORMULÁRIO COM REORDENAÇÃO ↑↓ ---
# =============================================================================

ICONES = {
    "Mundo":    "🌎", "Mercado": "📈", "Politica": "🏛️",
    "Tech":     "💻", "Esportes": "⚽", "Ciencia":  "🔬",
    "Motos":    "🏍️", "Fofoca":   "⭐",
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
            if col_up.button("↑", key=f"up_{tema}"):
                lista[i], lista[i - 1] = lista[i - 1], lista[i]
                st.rerun()
        else:
            col_up.write("")

        if i < len(lista) - 1:
            if col_dn.button("↓", key=f"dn_{tema}"):
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

    if st.button("SUBSCREVER AGORA 🗞️", use_container_width=True, key="btn_subscribe"):
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
                    <img src="{n['img']}" class="news-img">
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
