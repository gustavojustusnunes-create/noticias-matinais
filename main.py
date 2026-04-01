import os
import smtplib
import feedparser
import requests
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time
import re
import hashlib

# =============================================================================
# --- 1. CONFIGURAÇÕES ---
# =============================================================================
CLAUDE_KEY     = os.environ.get("CLAUDE_KEY", "").strip()
GCP_JSON       = os.environ.get("GCP_JSON")
EMAIL_SENDER   = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

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
        "https://pt.motorsport.com/rss/f1/news/",
        "https://www.theplayoffs.com.br/feed/",
        "https://www.espn.com.br/rss/",
        "https://sportv.globo.com/rss/sportv/",
        "https://www.uol.com.br/esporte/rss.xml",
    ],
    "Cinema":   [
        "https://www.omelete.com.br/rss/",
        "https://www.cinepop.com.br/feed",
        "https://www.papodecinema.com.br/feed/",
        "https://www.adorocinema.com/rss/",
    ],
    "Fitness":  [
        "https://ge.globo.com/rss/eu-atleta/",
        "https://www.runnersworld.com.br/feed/",
        "https://sportv.globo.com/rss/sportv/categoria/bem-estar-e-fitness/",
        "https://www.runnersworld.com/rss/all.xml/",
        "https://www.menshealth.com/rss/all.xml/",
        "https://www.bicycling.com/rss/all.xml/",
    ],
    "Ciencia":  [
        "https://g1.globo.com/rss/g1/ciencia-e-saude/",
        "https://gizmodo.uol.com.br/feed/",
        "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
        "https://www.tecmundo.com.br/ciencia/rss",
    ],
    "Motos":    [
        "https://www.motociclismoonline.com.br/feed/",
        "https://www.motoo.com.br/feed/",
        "https://motoblog.uol.com.br/feed/",
        "https://www.icarros.com.br/noticias/motos/rss.xml",
        "https://revistaautoesporte.globo.com/rss/",
    ],
    # FIX A: Fofoca agora usa fontes com foco internacional/cultura pop global
    "Fofoca":   [
        "https://hugogloss.uol.com.br/feed/",      # Hugo Gloss — melhor cobertura internacional BR
        "https://revistaquem.globo.com/rss/quem/", # Revista Quem — foco em celebridades globais
    ],
}

# =============================================================================
# --- 2. FILTROS DE CONTEÚDO ---
# =============================================================================
FILTROS_TEMA = {
    "Mundo":    [],

    # FIX B: Mercado agora bloqueia política sem foco econômico
    "Mercado":  [
        # Entretenimento e off-topic claro
        "horóscopo", "moda", "futebol", "brasileirão", "campeonato",
        "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
        "gol", "escalação", "clube", "torcedor",
        "lollapalooza", "festival", "show", "ingresso",
        "previsão do tempo", "clima", "chuva",
        "bbb", "big brother", "prêmio do bbb", "reality",
        "tênis", "fonseca", "alcaraz", "sinner", "nadal",
        # Guerra/geopolítica sem gancho econômico
        "israel:", "irã:", "civil morto", "guerra de fronteira",
        "bombardeio", "teerã", "netanyahu", "míssil",
        # Loteria
        "lotofácil", "mega-sena", "mega sena", "quina", "lotomania",
        "timemania", "dupla sena", "resultado sorteado",
        "prêmio da loteria", "números sorteados",
        # NOVO FIX B — Política sem gancho econômico direto
        "lula", "bolsonaro", "lulismo", "bolsonarismo",
        "stf", "congresso", "senado", "câmara dos deputados",
        "eleições", "eleição municipal", "eleição presidencial",
        "haddad", "palocci", "petista", "pt ", " pt,", "psdb", "pl ",
        "partido ", "voto ", "candidato", "deputado", "senador",
        "ministério da", "ministro da", "secretaria de", "governador",
        "prefeito", "política interna", "reforma ministerial",
        "impeachment", "pec ", "proposta de emenda", "orçamento secreto",
        "arthur lira", "rodrigo pacheco", "ciro gomes",
        "flávio dino", "gilmar mendes", "alexandre de moraes",
        "tse afirma", "tse confirma", "tse decide",
        "stj decide", "stf decide", "supremo decide",
        "supremo julga", "moraes determina",
        "operação policial", "preso", "prisão", "mandado de busca",
        "inquérito", "investigação policial", "delegacia",
    ],

    "Politica": [],

    "Tech":     [
        "aposta", "palpite", "futebol", "bônus", "cassino", "bet",
        "guia-de-compras", "em-oferta", "promoção", "desconto",
        "homenagem", "morre", "falece", "morte", "aniversário",
        "ator", "atriz", "celebridade",
        "troféus", "conquistas", "lista de troféus", "ps store",
        "xbox game pass", "jogos grátis", "resgate agora",
        "marinheiro", "porta-avião", "base militar",
        "entenda o final", "spoiler", "temporada final",
        "séries live-action", "live-action", "temporada", "episódio",
        "netflix planeja", "disney+", "hbo planeja",
        "filmes e séries", "para ver na netflix", "para assistir",
        "onde assistir a", "onde ver",
        "jogos para jogar", "jogos cooperativos", "melhores jogos",
        "quanto custa um pc", "pc gamer para jogar", "requisitos mínimos",
        "configurações para rodar", "placa de vídeo para",
        "de graça", "baratinhos", "indicações de games", "games da semana",
        "jogos da semana", "resgate grátis", "jogo grátis",
        "% off", "com até", "em oferta", "promoção de",
        "peaky blinders", "invencível", "house of", "the last of",
        "breaking bad", "game of thrones", "stranger things",
        "pets em ", "roupas para", "como ter pets", "como comprar",
    ],

    "Esportes": [
        "palpite", "apostas", "aposta", "odds", "odd:", "prognóstico",
        "melhores apostas", "mercado de apostas", "bet", "betting",
        "over/under", "handicap",
        "ao-vivo", "ao vivo", "/jogo/", "onde-assistir", "ingressos",
        "escalação", "prováveis-times",
        "reprisa", "reprise", "programação", "vai passar", "transmissão",
        "o que assistir", "disney+", "para assistir",
        "nota de falecimento", "troféu best",
        "/base/", "sub-13", "sub-15", "sub-17", "sub-20",
        "segunda-divisao", "terceira-divisao", "serie-d", "serie-c", "futsal",
        "futebol", "brasileirão", "libertadores", "copa do brasil",
        "eliminatórias", "eurocopa", "copa do mundo",
        "seleção brasileira", "seleção", "convocação", "cbf",
        "amistoso", "brasil x ", "seleção x ",
        "neymar", "vinicius", "vinícius", "rodrygo", "endrick", "richarlison",
        "memphis", "raphinha", "militão", "marquinhos", "casemiro", "paquetá",
        "palmeiras", "flamengo", "corinthians", "são paulo", "santos",
        "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
        "botafogo", "fluminense", "fortaleza", "bahia", "athletico",
        "salah", "mbappé", "mbappe", "haaland", "bellingham",
        "modric", "benzema", "lewandowski", "kane", "de bruyne",
        "messi", "ronaldo", "kroos", "pedri", "yamal",
        "liverpool", "real madrid", "barcelona", "manchester",
        "arsenal", "chelsea", "psg", "bayern", "juventus",
        "premier league", "la liga", "champions league",
        "ancelotti", "guardiola", "klopp", "mourinho",
    ],

    "Cinema":   [
        "aposta", "bet", "cassino", "futebol", "esporte",
        "aniversário", "tatuagem", "look", "moda", "relacionamento",
        "casamento", "separação", "gravidez", "filhos",
        "morte de", "falecimento", "luto", "velório",
        "lamenta morte", "celebra aniversário", "faz anos",
    ],

    "Fitness":  [
        "aposta", "bet", "cassino", "futebol", "moda",
        "maquiagem", "cabelo", "unhas", "beleza", "tatuagem",
        "câncer", "tumor", "cirurgia", "hospital", "médico recomenda",
        "remédio", "medicamento", "vacina", "dengue", "vírus",
        "doença", "diagnóstico", "sintomas", "tratamento clínico",
        "famoso", "celebridade", "ator", "atriz", "novela",
        "bbb", "big brother", "reality",
        "resfriado", "alergia", "gripe",
        "erros na cozinha", "receita de", "culinária",
        "velhice", "envelhecimento", "idoso", "terceira idade",
    ],

    "Ciencia":  [
        "mão de obra", "mercado de trabalho", "emprego",
        "carreira", "concurso público", "salário",
    ],

    "Motos":    [],

    # Fofoca: pré-filtros de URL/título para lixo óbvio nacional
    "Fofoca":   [
        "ex-bbb", "ex bbb", "bbb ", "big brother",
        "fazenda ", "a fazenda", "reality show",
        "sertanejo", "pagodeiro", "funkeiro", "funk",
        "mc ", "mc.", "dj ",
    ],
}

PALAVRAS_FUTEBOL = [
    "futebol", "brasileirão", "série a", "serie-a", "libertadores",
    "copa do brasil", "copa-do-brasil", "brasileirao", "champions league",
    "premier league", "la liga", "campeonato brasileiro", "copa do mundo",
    "eliminatórias", "eurocopa", "world cup",
    "palmeiras", "flamengo", "corinthians", "são paulo", "santos",
    "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
    "botafogo", "fluminense", "fortaleza", "bahia",
    "seleção brasileira", "seleção", "cbf",
    "neymar", "vinicius", "vinícius", "rodrygo", "endrick", "richarlison",
    "memphis", "raphinha", "gabriel martinelli", "militão", "marquinhos",
    "alisson", "ederson", "casemiro", "paquetá",
    "salah", "mbappé", "mbappe", "haaland", "bellingham",
    "modric", "benzema", "lewandowski", "kane", "de bruyne",
    "messi", "ronaldo", "kroos", "pedri", "yamal",
    "liverpool", "real madrid", "barcelona", "manchester",
    "arsenal", "chelsea", "psg", "bayern", "juventus",
    "premier league", "la liga", "champions league",
    "ancelotti", "guardiola", "klopp", "mourinho",
    "brasil x ", "seleção x ", "amistoso",
]

PALAVRAS_ESPORTES_PRIORITY = [
    "formula 1", "formula1", "fórmula 1", "fórmula1", "f1", "gp de",
    "grand prix", "verstappen", "hamilton", "leclerc", "norris", "ferrari",
    "red bull racing", "mercedes f1", "mclaren f1",
    "nba", "basquete", "basquetebol", "lakers", "warriors", "celtics",
    "lebron", "curry", "nfl", "futebol americano", "super bowl",
    "touchdown", "quarterback",
]

# =============================================================================
# --- 3. VALIDAÇÃO DE AMBIENTE ---
# =============================================================================
def validar_ambiente():
    variaveis = {
        "CLAUDE_KEY":     CLAUDE_KEY,
        "GCP_JSON":       GCP_JSON,
        "EMAIL_USER":     EMAIL_SENDER,
        "EMAIL_PASSWORD": EMAIL_PASSWORD,
    }
    erros = [nome for nome, val in variaveis.items() if not val]
    if erros:
        print(f"❌ ERRO CRÍTICO: Variáveis faltando: {', '.join(erros)}")
        return False
    print("✅ Ambiente validado.")
    return True

# =============================================================================
# --- 4. INFRAESTRUTURA ---
# =============================================================================
def conectar_banco():
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        planilha       = client.open("noticias_db")
        sheet_usuarios = planilha.sheet1

        try:
            sheet_historico = planilha.worksheet("historico")
        except gspread.exceptions.WorksheetNotFound:
            sheet_historico = planilha.add_worksheet(title="historico", rows=5000, cols=3)
            sheet_historico.append_row(["hash", "titulo", "data"])

        try:
            sheet_logs = planilha.worksheet("logs")
        except gspread.exceptions.WorksheetNotFound:
            sheet_logs = planilha.add_worksheet(title="logs", rows=5000, cols=5)
            sheet_logs.append_row(["data", "nome", "email", "status", "temas"])

        return sheet_usuarios, sheet_historico, sheet_logs
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None, None, None

# =============================================================================
# --- 5. CONTROLE DE DUPLICATAS ---
# =============================================================================
def gerar_hash(titulo, link):
    return hashlib.md5(f"{titulo}{link}".encode("utf-8")).hexdigest()

def carregar_historico(sheet_historico):
    try:
        from datetime import timedelta
        registros    = sheet_historico.get_all_records()
        if not registros:
            return set()

        limite       = datetime.now() - timedelta(days=30)
        hashes       = set()
        remover      = []

        for i, r in enumerate(registros, start=2):
            try:
                data = datetime.strptime(r.get("data", "")[:10], "%d/%m/%Y")
                if data >= limite:
                    hashes.add(r["hash"])
                else:
                    remover.append(i)
            except Exception:
                hashes.add(r.get("hash", ""))

        for idx in reversed(remover):
            try:
                sheet_historico.delete_rows(idx)
            except Exception:
                pass
        if remover:
            print(f"   🧹 Histórico: {len(remover)} entradas antigas removidas.")

        print(f"   🗂️ Histórico: {len(hashes)} notícias nos últimos 30 dias.")
        return hashes
    except Exception as e:
        print(f"⚠️ Histórico indisponível: {e}")
        return set()

def salvar_no_historico(sheet_historico, noticias_novas):
    hoje   = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        [gerar_hash(n["titulo"], n["link"]), n["titulo"][:80], hoje]
        for n in noticias_novas
    ]
    if linhas:
        sheet_historico.append_rows(linhas)

# =============================================================================
# --- 6. LOG DE ENVIOS ---
# =============================================================================
def registrar_log(sheet_logs, nome, email, status, temas_enviados):
    try:
        sheet_logs.append_row([
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            nome, email,
            "✅ Enviado" if status else "❌ Falhou",
            ", ".join(temas_enviados),
        ])
    except Exception as e:
        print(f"⚠️ Log não registrado ({nome}): {e}")

# =============================================================================
# --- 7. INDICADORES FINANCEIROS ---
# =============================================================================
def formatar_indicador(nome, valor, variacao, prefixo=""):
    cor   = "green" if variacao >= 0 else "red"
    seta  = "▲" if variacao >= 0 else "▼"
    sinal = "+" if variacao > 0 else ""
    return (
        f"{prefixo} <b>{nome}:</b> {valor} "
        f"<span style='color:{cor}; font-size:11px;'>{seta} {sinal}{variacao:.2f}%</span>"
    )

def obter_indicadores():
    html_items = []

    def buscar_btc():
        for ticker_id, moeda in [("BTC-BRL", "BRL"), ("BTC-USD", "USD")]:
            try:
                hist = yf.Ticker(ticker_id).history(period="5d")
                if len(hist) >= 2:
                    atual = hist["Close"].iloc[-1]
                    ant   = hist["Close"].iloc[-2]
                    var   = (atual - ant) / ant * 100
                    label = f"R$ {atual/1000:.1f}k" if moeda == "BRL" else f"US$ {atual/1000:.1f}k"
                    return formatar_indicador("BTC", label, var, "₿")
            except Exception as e:
                print(f"⚠️ BTC/{moeda}: {e}")
        return None

    for ticker_id, nome, fmt, pfx in [
        ("BRL=X",  "USD",  lambda v: f"R$ {v:.2f}", "🇺🇸"),
        ("^BVSP",  "IBOV", lambda v: f"{int(v)} pts", "🇧🇷"),
    ]:
        try:
            hist = yf.Ticker(ticker_id).history(period="5d")
            if len(hist) >= 2:
                atual = hist["Close"].iloc[-1]
                ant   = hist["Close"].iloc[-2]
                var   = (atual - ant) / ant * 100
                html_items.append(formatar_indicador(nome, fmt(atual), var, pfx))
        except Exception as e:
            print(f"⚠️ {nome}: {e}")

    btc = buscar_btc()
    if btc:
        html_items.insert(1, btc)

    if not html_items:
        return ""
    return (
        "<div style='background-color:#e5e3de; padding:12px; text-align:center; "
        "font-family:monospace; font-size:13px; color:#111;'>"
        + " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(html_items)
        + "</div>"
    )

# =============================================================================
# --- 8. EXTRAÇÃO DE IMAGEM ---
# =============================================================================
def buscar_og_image(url_artigo, timeout=10):
    if not url_artigo:
        return None
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control":   "no-cache",
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
            r'<meta[^>]+property=["\']og:image:url["\'][^>]+content=["\']([^"\']+)["\']',
        ]
        for padrao in padroes:
            m = re.search(padrao, html, re.IGNORECASE)
            if m:
                url = m.group(1).strip().replace("&amp;", "&").replace("&#38;", "&")
                if url.startswith("http") and len(url) > 15:
                    return url

        # Fallback: primeira imagem grande na página
        extensoes = (".jpg", ".jpeg", ".png", ".webp")
        for m in re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:width=["\'](\d+)["\'])?',
            html, re.IGNORECASE
        ):
            src   = m[0] if isinstance(m, tuple) else m
            width = int(m[1]) if isinstance(m, tuple) and m[1] else 0
            if (
                any(ext in src.lower() for ext in extensoes)
                and src.startswith("http")
                and "pixel" not in src
                and "logo"  not in src.lower()
                and "icon"  not in src.lower()
                and (width == 0 or width >= 300)
            ):
                return src

    except requests.exceptions.Timeout:
        print(f"      ⏱️ Timeout na imagem: {url_artigo[:60]}...")
    except Exception:
        pass
    return None

FALLBACK_IMAGES = {
    "Mundo":    "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=300&fit=crop",
    "Mercado":  "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
    "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
    "Tech":     "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=300&fit=crop",
    "Cinema":   "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600&h=300&fit=crop",
    "Fitness":  "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "Ciencia":  "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=300&fit=crop",
    "Motos":    "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=600&h=300&fit=crop",
    "Fofoca":   "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=300&fit=crop",
    "Esportes": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
}

FALLBACK_ESPORTES_GENERIC = [
    "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1540747913346-19212a4b32b8?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&h=300&fit=crop",
]

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
    "nba":   ["nba", "basquete", "lebron", "curry", "lakers", "celtics", "warriors"],
    "f1":    ["f1", "formula", "grand prix", "gp de", "verstappen", "hamilton", "ferrari", "leclerc"],
    "mma":   ["mma", "ufc", "evloev", "volkanovski", "poatan", "adesanya"],
    "tenis": ["tênis", "tennis", "fonseca", "alcaraz", "sinner", "open"],
}

def extrair_imagem_rss(entry, tema, idx_entry=0):
    extensoes = (".jpg", ".jpeg", ".png", ".webp")
    image_url = None

    # Prioridade 1: og:image / twitter:image da página real
    image_url = buscar_og_image(entry.get("link", ""))

    # Prioridade 2: media_content do RSS
    if not image_url:
        for m in entry.get("media_content", []):
            if "url" in m and any(ext in m["url"].lower() for ext in extensoes):
                image_url = m["url"]
                break

    # Prioridade 3: enclosures
    if not image_url:
        for enc in entry.get("enclosures", []):
            url_enc = enc.get("url", "")
            if any(ext in url_enc.lower() for ext in extensoes):
                image_url = url_enc
                break

    # Prioridade 4: links com type image
    if not image_url:
        for l in entry.get("links", []):
            href = l.get("href", "")
            if l.get("type", "").startswith("image/") and any(ext in href.lower() for ext in extensoes):
                image_url = href
                break

    # Prioridade 5: scraping de <img> no HTML do summary/content
    if not image_url:
        txt = "".join(c.value for c in entry.get("content", []))
        txt += entry.get("summary", "")
        for url in re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', txt):
            if (any(ext in url.lower() for ext in extensoes)
                    and "pixel" not in url and "doubleclick" not in url):
                image_url = url
                break

    # Fallback temático
    if not image_url:
        if tema == "Esportes":
            titulo  = entry.get("title", "").lower()
            categoria = next(
                (cat for cat, kws in SPORT_KEYWORDS.items() if any(kw in titulo for kw in kws)),
                None
            )
            if categoria:
                image_url = SPORT_ROTATIONS[categoria][ord(titulo[0]) % 2]
            else:
                image_url = FALLBACK_ESPORTES_GENERIC[idx_entry % len(FALLBACK_ESPORTES_GENERIC)]
        else:
            image_url = FALLBACK_IMAGES.get(
                tema,
                "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
            )

    return image_url

# =============================================================================
# --- 9. CAMADA DE IA ---
# =============================================================================
def chamar_claude_api(prompt, max_tokens=4096):
    if not CLAUDE_KEY:
        print("      ❌ CLAUDE_KEY não definida.")
        return None

    modelos = [
        ("claude-sonnet-4-6",         90),
        ("claude-haiku-4-5-20251001", 60),
    ]
    headers = {
        "x-api-key":         CLAUDE_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    for modelo, timeout in modelos:
        print(f"      🤖 {modelo}...")
        for tentativa in range(1, 4):
            try:
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": modelo, "max_tokens": max_tokens,
                          "messages": [{"role": "user", "content": prompt}]},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    data   = r.json()
                    texto  = data["content"][0]["text"]
                    tokens = data.get("usage", {})
                    print(f"      ✅ OK  in={tokens.get('input_tokens','?')}  out={tokens.get('output_tokens','?')}")
                    return texto
                elif r.status_code == 429:
                    espera = 20 * tentativa
                    print(f"      ⏳ Rate-limit. Aguardando {espera}s…")
                    time.sleep(espera)
                elif r.status_code == 404:
                    print(f"      ❌ Modelo não encontrado: {modelo}")
                    break
                elif r.status_code == 401:
                    print("      ❌ CLAUDE_KEY inválida.")
                    return None
                elif r.status_code == 529:
                    print("      ⚠️ Sobrecarga. Próximo modelo…")
                    break
                else:
                    print(f"      ⚠️ HTTP {r.status_code}: {r.text[:150]}")
                    break
            except requests.exceptions.Timeout:
                print(f"      ⚠️ Timeout ({timeout}s) em {modelo}.")
                break
            except Exception as e:
                print(f"      ⚠️ Exceção: {e}")
                break

    print("      ❌ Todos os modelos falharam.")
    return None

# =============================================================================
# --- 10. LIMPEZA DE TEXTO RSS ---
# =============================================================================
def limpar_texto_rss(texto):
    """Remove HTML, entidades, CTAs de engajamento e lixo de feeds."""
    texto = re.sub(r"<[^>]+>", "", texto)

    # Entidades HTML
    entidades = {
        "&#8220;": '"', "&#8221;": '"', "&#8216;": "'", "&#8217;": "'",
        "&amp;": "&", "&quot;": '"', "&nbsp;": " ", "&#38;": "&",
        "&#8230;": "", "[&#8230;]": "", "[…]": "", "[...]": "",
    }
    for ent, sub in entidades.items():
        texto = texto.replace(ent, sub)

    # Rodapés WordPress
    texto = re.sub(r"\s*The post .+?appeared first on .+?\.?\s*", " ", texto,
                   flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r"\s*appeared first on .+", "", texto, flags=re.IGNORECASE)

    # CTAs e ruído de redes sociais
    padroes_cta = [
        r"✅\s*Siga\b.*",
        r"🔔\s*Siga\b.*",
        r"Siga\s+o\s+canal.*",
        r"Veja\s+no\s+vídeo\s+acima\.?",
        r"Acompanhe\s+as\s+notícias.*",
        r"Acompanhe\s+ao\s+vivo.*",
        r"Clique\s+aqui\s+e.*",
        r"Inscreva-se\s+no.*",
        r"Acesse\s+o\s+canal.*",
        r"Por:\s+[A-ZÀ-Ú][a-zà-ú]+\s+[A-ZÀ-Ú][a-zà-ú]+",
        r"nfoMoney\.?\s*$",
        r"Notícia\.\.\.",
        r"\[&#\d+;\]",
    ]
    for padrao in padroes_cta:
        texto = re.sub(padrao, " ", texto, flags=re.DOTALL | re.IGNORECASE)

    # Créditos de foto
    texto = re.sub(
        r"\b(Reuters|AFP|AP|EFE|G1|Globo|GE|Getty)[\s/][^\.\n]{0,60}",
        " ", texto, flags=re.IGNORECASE
    )

    # Reticências residuais
    texto = re.sub(r"\s*\.\.\.\s*$", ".", texto.strip())
    texto = re.sub(r"\s*…\s*$", ".", texto.strip())

    return re.sub(r"\s+", " ", texto).strip()

# =============================================================================
# --- 11. EXTRAÇÃO DE CONTEXTO BASE (FIX C) ---
# =============================================================================
def extrair_contexto_base(entry, max_chars: int = 800) -> str:
    """
    Extrai o melhor texto disponível da entrada RSS para injetar no prompt.
    Hierarquia: content > summary > description.
    Remove lixo, limita a max_chars caracteres e garante que termina numa
    frase completa (não corta no meio de uma palavra).
    """
    texto = ""
    if "content" in entry:
        for c in entry.content:
            texto += c.value
    if not texto.strip() and "summary" in entry:
        texto = entry.summary
    if not texto.strip():
        texto = entry.get("description", "")

    texto = limpar_texto_rss(texto)

    if len(texto) > max_chars:
        cortado = texto[:max_chars]
        # Tenta encerrar na última frase completa
        ultimo_ponto = max(cortado.rfind("."), cortado.rfind("!"), cortado.rfind("?"))
        if ultimo_ponto > max_chars // 2:
            cortado = cortado[: ultimo_ponto + 1]
        texto = cortado

    return texto.strip()

# =============================================================================
# --- 12. PROCESSAMENTO DE TEMA ---
# =============================================================================
def aplicar_filtros(entry, tema):
    palavras = FILTROS_TEMA.get(tema, [])
    if not palavras:
        return True
    titulo = entry.get("title", "").lower()
    link   = entry.get("link",  "").lower()
    return not any(p in titulo or p in link for p in palavras)

def e_futebol(entry):
    texto = (entry.get("title", "") + " " + entry.get("link", "")).lower()
    return any(p in texto for p in PALAVRAS_FUTEBOL)

def e_esporte_prioritario(entry):
    texto = (entry.get("title", "") + " " + entry.get("link", "")).lower()
    return any(p in texto for p in PALAVRAS_ESPORTES_PRIORITY)

def coletar_entries_esportes():
    todas, vistos = [], set()
    for url in RSS_FEEDS["Esportes"]:
        try:
            for e in feedparser.parse(url).entries:
                link = e.get("link", "")
                if link not in vistos:
                    vistos.add(link)
                    todas.append(e)
        except Exception as ex:
            print(f"      ⚠️ Esportes ({url}): {ex}")
    return todas

def titulos_similares(t1, t2):
    p1 = set(re.findall(r"\w{4,}", t1.lower()))
    p2 = set(re.findall(r"\w{4,}", t2.lower()))
    if not p1 or not p2:
        return False
    return len(p1 & p2) / min(len(p1), len(p2)) >= 0.50

# ---------------------------------------------------------------------------
# Instruções por tema para o prompt principal
# ---------------------------------------------------------------------------
INSTRUCAO_TEMA = {
    "Mundo": (
        "Inclua o contexto geopolítico completo: países envolvidos, atores principais, "
        "linha do tempo do evento e as possíveis consequências regionais e globais."
    ),
    "Mercado": (
        "Inclua obrigatoriamente: números (percentuais, valores em R$ ou US$, variações "
        "de índices), o impacto direto para o investidor ou consumidor brasileiro e o "
        "contexto macroeconômico que explica o movimento.\n"
        "REGRA CRÍTICA DE FILTRAGEM: Se a manchete for sobre política, partidos, "
        "eleições, decisões judiciais ou segurança pública SEM impacto econômico direto "
        "e mensurável, retorne EXATAMENTE a palavra SKIP e nada mais."
    ),
    "Politica": (
        "Inclua o contexto institucional, as partes envolvidas (partidos, tribunais, "
        "parlamentares), o que está sendo decidido e os possíveis desdobramentos "
        "políticos ou jurídicos para o cidadão."
    ),
    "Tech": (
        "Inclua detalhes técnicos relevantes (versão, especificações, arquitetura), "
        "o impacto no mercado ou no usuário final e o contexto competitivo da empresa "
        "ou inovação em questão."
    ),
    "Esportes": (
        "Inclua: resultados concretos (placar, tempo, posição), desempenho individual "
        "de atletas com estatísticas, o que estava em jogo na competição e o impacto "
        "no campeonato ou temporada."
    ),
    "Cinema": (
        "Inclua: gênero, elenco principal, diretor, sinopse objetiva (sem spoilers), "
        "avaliações de crítica (Rotten Tomatoes, IMDb) quando disponíveis e por que "
        "o filme ou série vale atenção do leitor."
    ),
    # FIX 3: Fitness — ênfase máxima em tradução e foco em performance
    "Fitness": (
        "REGRA CRÍTICA DE IDIOMA: O texto base pode estar em inglês. "
        "Independentemente disso, o resumo final DEVE ser escrito EXCLUSIVAMENTE "
        "em Português Brasileiro fluente e natural — jamais use palavras em inglês "
        "no corpo do texto.\n"
        "FOCO DE CONTEÚDO: Escreva com a linguagem da cultura de saúde e performance: "
        "treino, recuperação, nutrição esportiva, mindset atlético, protocolos de "
        "ciclismo, corrida, musculação ou mobilidade. Inclua dados práticos "
        "(séries, distâncias, zonas de frequência cardíaca, macros) sempre que o "
        "texto base os fornecer. Evite tom de consultório médico."
    ),
    "Ciencia": (
        "Inclua: instituição/pesquisadores envolvidos, metodologia resumida, "
        "principais números e descobertas e o que muda no entendimento científico "
        "ou na prática clínica com esse resultado."
    ),
    "Motos": (
        "Inclua: modelo, cilindrada, potência (cv/kW), torque, preço estimado no "
        "Brasil (quando disponível), diferenciais em relação à concorrência e o "
        "perfil de piloto para o qual a moto foi projetada."
    ),
    # FIX 4: Fofoca — filtro semântico de IA para subcelebridades e BBBs
    "Fofoca": (
        "O caderno Fofoca tem foco em cultura pop INTERNACIONAL: atores e atrizes de "
        "Hollywood, músicos globais (BTS, Taylor Swift, Beyoncé, etc.), realeza europeia "
        "e celebridades de alcance mundial.\n"
        "REGRA CRÍTICA DE FILTRAGEM: Se a notícia for sobre subcelebridade brasileira, "
        "ex-participante de BBB, cantor sertanejo, funkeiro, influenciador digital sem "
        "relevância global ou qualquer figura desconhecida fora do Brasil, retorne "
        "EXATAMENTE a palavra SKIP e nada mais.\n"
        "Para notícias aprovadas: inclua contexto da celebridade, o que aconteceu, "
        "reações do público e por que o assunto é relevante globalmente."
    ),
}

def processar_tema(tema, historico_hashes):
    """
    Pipeline completo para um tema:
    1. Coleta (multi-fonte ou fonte única)
    2. Filtra (palavras-chave + hash anti-duplicata)
    3. Deduplica por similaridade de título
    4. Monta input com TÍTULO + CONTEXTO BASE (FIX C)
    5. Chama Claude com prompt enriquecido
    6. Aplica fallbacks em cascata para garantir resumo de qualidade
    """
    print(f"   📂 Processando: {tema}")

    TEMAS_MULTI_FONTE = {"Esportes", "Cinema", "Fitness", "Ciencia", "Motos", "Fofoca"}

    # ── Coleta ──────────────────────────────────────────────────────────────
    if tema == "Esportes":
        valid_entries = coletar_entries_esportes()
    elif tema in TEMAS_MULTI_FONTE:
        valid_entries, vistos = [], set()
        for url in RSS_FEEDS.get(tema, []):
            try:
                for e in feedparser.parse(url).entries:
                    link = e.get("link", "")
                    if link not in vistos:
                        vistos.add(link)
                        valid_entries.append(e)
            except Exception as ex:
                print(f"      ⚠️ {tema} ({url}): {ex}")
        print(f"      📡 {len(valid_entries)} entradas coletadas.")
    else:
        valid_entries = []
        for url in RSS_FEEDS.get(tema, []):
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    valid_entries = feed.entries
                    break
            except Exception as ex:
                print(f"      ⚠️ {url}: {ex}")

    if not valid_entries:
        print(f"      ❌ Nenhuma entrada para '{tema}'.")
        return None

    # ── Filtragem por palavras-chave + anti-duplicata ────────────────────────
    candidatas = []
    limite = 40 if tema in TEMAS_MULTI_FONTE else 20
    for entry in valid_entries:
        if not aplicar_filtros(entry, tema):
            continue
        if gerar_hash(entry.get("title", ""), entry.get("link", "")) in historico_hashes:
            continue
        candidatas.append(entry)
        if len(candidatas) >= limite:
            break

    if not candidatas:
        print(f"      ⚠️ '{tema}' vazio após filtros.")
        return None

    # ── Diversidade Esportes ─────────────────────────────────────────────────
    if tema == "Esportes":
        prio, outros, fut = [], [], []
        for e in candidatas:
            if e_esporte_prioritario(e):
                prio.append(e)
            elif e_futebol(e):
                fut.append(e)
            else:
                outros.append(e)
        sel = prio + outros
        for f in fut:
            if len(sel) >= 4:
                break
            sel.append(f)
        candidatas = sel[:4]
        print(f"      🏎️  F1/NBA={sum(1 for e in candidatas if e_esporte_prioritario(e))} "
              f"| Outros={sum(1 for e in candidatas if not e_futebol(e) and not e_esporte_prioritario(e))} "
              f"| Fut={sum(1 for e in candidatas if e_futebol(e))}")

    # ── Deduplicação por similaridade de título ──────────────────────────────
    noticias_filtradas = []
    for entry in candidatas:
        if not any(titulos_similares(entry.get("title", ""), e.get("title", ""))
                   for e in noticias_filtradas):
            noticias_filtradas.append(entry)
        if len(noticias_filtradas) >= 4:
            break

    if not noticias_filtradas:
        print(f"      ⚠️ '{tema}' vazio após deduplicação.")
        return None

    # ── Monta input COM contexto base (FIX C) ───────────────────────────────
    input_txt = ""
    for i, e in enumerate(noticias_filtradas):
        titulo  = e.get("title", "")
        contexto = extrair_contexto_base(e, max_chars=800)
        if contexto and contexto.lower() != titulo.lower():
            input_txt += (
                f"Notícia {i + 1}:\n"
                f"Título: {titulo}\n"
                f"Texto Base: {contexto}\n\n"
            )
        else:
            # Sem contexto disponível — só o título (fallback posterior cuida disso)
            input_txt += f"Notícia {i + 1}:\nTítulo: {titulo}\n\n"

    instrucao = INSTRUCAO_TEMA.get(tema, "Inclua dados, números e contexto relevantes.")

    # ── Prompt principal ─────────────────────────────────────────────────────
    prompt = f"""Você é um repórter sênior do All News Journal, jornal digital premium brasileiro.
Escreva resumos jornalísticos COMPLETOS e AUTOSSUFICIENTES para o caderno de {tema}.

O leitor NÃO vai clicar em nenhum link — o resumo é a notícia inteira.

═══════════════════════════════════════
DIRETRIZES EDITORIAIS — {tema.upper()}
═══════════════════════════════════════
{instrucao}

═══════════════════════════════════════
REGRAS ABSOLUTAS DE FORMATO
═══════════════════════════════════════
1. TAMANHO: 85 a 105 palavras por resumo. Abaixo de 70 = REPROVADO.
2. CONCLUSÃO: NUNCA termine com "…" ou "...". Última frase fechada com ponto final.
3. IDIOMA: Sempre em Português Brasileiro fluente. Mesmo que o texto base esteja em inglês.
4. TOM: Direto, ativo, jornalístico. Sem jargões. Sem linguagem de teaser.
5. PROIBIDO: "o artigo fala", "a notícia informa", "segundo a publicação", "vale destacar".
6. PROIBIDO: numeração ("1.", "Notícia 1:"), markdown (asteriscos, negrito, bullets).
7. INÍCIO: Comece sempre pelo fato principal com dados concretos.

Separe cada resumo com "|||". Retorne APENAS os resumos.

═══════════════════════════════════════
MANCHETES E CONTEXTO
═══════════════════════════════════════
{input_txt}"""

    resp_ia = chamar_claude_api(prompt)

    # ── Limpeza dos resumos retornados ───────────────────────────────────────
    def limpar_resumo(texto: str) -> str:
        texto = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", texto)
        texto = re.sub(r"^[\*\s]*Not[íi]cia\s*\d+[\:\.\s\*]*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"^\d+[\.\)]\s*", "", texto)
        texto = limpar_texto_rss(texto)
        texto = re.sub(r"\s*\.\.\.\s*$", ".", texto.strip())
        texto = re.sub(r"\s*…\s*$", ".", texto.strip())
        return texto.strip()

    resumos_ia: list[str] = []
    if resp_ia:
        resumos_ia = [r.strip() for r in resp_ia.split("|||") if r.strip()]
        while len(resumos_ia) < len(noticias_filtradas):
            resumos_ia.append("")
    else:
        print(f"      ⚠️ IA indisponível para '{tema}'. Ativando fallbacks.")

    # ── Monta notícias finais com fallback em cascata ────────────────────────
    noticias_finais = []

    for i, entry in enumerate(noticias_filtradas):
        titulo_entry = entry.get("title", "")
        resumo_bruto = resumos_ia[i] if i < len(resumos_ia) else ""
        resumo_limpo = limpar_resumo(resumo_bruto)

        # FIX D: SKIP funciona para QUALQUER tema, não apenas Mercado
        if resumo_limpo.strip().upper() == "SKIP":
            print(f"      🚫 SKIP [{tema}]: {titulo_entry[:60]}")
            continue

        # ── Fallback 1: Claude reescreve o contexto base se IA primária falhou ──
        if not resumo_limpo:
            contexto_base = extrair_contexto_base(entry, max_chars=800)
            if contexto_base and len(contexto_base.split()) >= 20:
                idioma_hint = (
                    "O texto base pode estar em inglês. "
                    "O resumo DEVE ser escrito em Português Brasileiro fluente."
                    if tema == "Fitness" else ""
                )
                prompt_rewrite = (
                    f"Você é um jornalista sênior. Reescreva o texto abaixo como um "
                    f"parágrafo jornalístico de 85 a 100 palavras em Português Brasileiro "
                    f"direto e fluente. NUNCA termine com '...' ou '…'. "
                    f"Última frase fechada com ponto final. "
                    f"Retorne APENAS o parágrafo. {idioma_hint}\n\n"
                    f"Título: {titulo_entry}\n\nTexto base:\n{contexto_base}"
                )
                reescrito = chamar_claude_api(prompt_rewrite, max_tokens=512)
                if reescrito and len(reescrito.split()) >= 20:
                    resumo_limpo = limpar_resumo(reescrito)

        # ── Fallback 2: Claude gera a partir do título apenas ─────────────────
        if not resumo_limpo:
            idioma_hint = (
                "Escreva em Português Brasileiro mesmo que o título esteja em inglês."
                if tema == "Fitness" else ""
            )
            prompt_mini = (
                f"Você é um jornalista sênior. Com base APENAS no título abaixo, "
                f"escreva um parágrafo jornalístico de 3 frases (80 a 95 palavras) "
                f"em Português Brasileiro. Escreva como fato estabelecido — sem "
                f"'provavelmente', 'deve' ou linguagem especulativa. "
                f"NUNCA termine com '...' ou '…'. Ponto final obrigatório na última frase. "
                f"Retorne APENAS o parágrafo. {idioma_hint}\n\n"
                f"Título: {titulo_entry}"
            )
            mini = chamar_claude_api(prompt_mini, max_tokens=512)
            if mini and len(mini.split()) >= 20:
                resumo_limpo = limpar_resumo(mini)

        # ── Fallback 3 (último recurso): usa contexto base limpo ─────────────
        if not resumo_limpo:
            ctx = extrair_contexto_base(entry, max_chars=600)
            resumo_limpo = ctx if len(ctx.split()) >= 10 else titulo_entry

        img = extrair_imagem_rss(entry, tema, idx_entry=i)
        noticias_finais.append({
            "titulo": titulo_entry,
            "link":   entry.get("link", ""),
            "imagem": img,
            "resumo": resumo_limpo,
        })

    return noticias_finais if noticias_finais else None

# =============================================================================
# --- 13. TEMPLATE DO E-MAIL ---
# =============================================================================
ICONES_TEMA = {
    "Mundo": "🌎", "Mercado": "📈", "Politica": "🏛️", "Tech": "💻",
    "Esportes": "🏎️", "Cinema": "🎬", "Fitness": "🏃", "Ciencia": "🔬",
    "Motos": "🏍️", "Fofoca": "⭐",
}

def gerar_html_final(nome, dados, painel):
    TURQUESA = "0a5c5a"
    CREME    = "fdfbf7"
    ESCURO   = "084c4a"

    hoje = datetime.now()
    MESES     = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    DIAS      = ["Segunda-feira","Terça-feira","Quarta-feira",
                 "Quinta-feira","Sexta-feira","Sábado","Domingo"]
    data_ptbr = f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}"

    html = f"""
<html><body style="margin:0;padding:0;background-color:#e5e3de;font-family:'Lora','Times New Roman',serif;">
<div style="max-width:620px;margin:20px auto;background-color:#{CREME};border-radius:8px;
            overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.07);">

  <!-- CABEÇALHO -->
  <div style="padding:30px 20px 20px;text-align:center;border-bottom:3px solid #{TURQUESA};">
    <p style="margin:0 0 6px;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#999;">
      Edição Premium Digital
    </p>
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:36px;
               text-transform:uppercase;letter-spacing:3px;color:#{TURQUESA};">
      ALL NEWS JOURNAL
    </h1>
    <p style="margin:10px 0 0;font-size:12px;color:#777;font-style:italic;">{data_ptbr}</p>
  </div>

  <!-- PAINEL FINANCEIRO -->
  {painel}

  <!-- SAUDAÇÃO -->
  <div style="padding:30px 30px 10px;">
    <p style="color:#555;font-size:15px;text-align:center;margin-bottom:35px;
              font-style:italic;border-bottom:1px solid #e5e3de;padding-bottom:25px;">
      Bom dia, <b style="color:#{TURQUESA};">{nome}</b>. A sua curadoria premium de hoje está pronta.
    </p>
"""

    for tema, items in dados.items():
        if not items:
            continue
        icone = ICONES_TEMA.get(tema, "📰")
        html += f"""
    <!-- CADERNO: {tema.upper()} -->
    <div style="margin:35px 0 20px;border-bottom:2px solid #{TURQUESA};">
      <span style="background-color:#{TURQUESA};color:#fff;padding:7px 16px;
                   font-size:11px;font-weight:bold;text-transform:uppercase;
                   letter-spacing:1.5px;border-radius:4px 4px 0 0;display:inline-block;">
        {icone} {tema}
      </span>
    </div>"""

        for n in items:
            titulo_safe = n["titulo"].replace('"', '&quot;').replace("'", "&#39;")
            html += f"""
    <div style="margin-bottom:40px;padding-bottom:30px;border-bottom:1px solid #ede9e3;">
      <a href="{n['link']}" target="_blank" style="display:block;text-decoration:none;">
        <img src="{n['imagem']}"
             alt="{titulo_safe}"
             style="width:100%;height:230px;object-fit:cover;border-radius:6px;
                    border-bottom:4px solid #{TURQUESA};display:block;">
      </a>
      <div style="padding-top:18px;">
        <a href="{n['link']}" target="_blank" style="text-decoration:none;color:#111;">
          <h3 style="margin:0 0 14px;font-size:21px;
                     font-family:'Playfair Display',Georgia,serif;
                     line-height:1.35;color:#111;">
            {n['titulo']}
          </h3>
        </a>
        <p style="margin:0 0 16px;font-size:15px;color:#3a3a3a;line-height:1.75;
                  font-family:'Lora','Times New Roman',serif;">
          {n['resumo']}
        </p>
        <a href="{n['link']}" target="_blank"
           style="font-size:12px;color:#{TURQUESA};font-weight:bold;text-decoration:none;
                  text-transform:uppercase;letter-spacing:1px;
                  border-bottom:2px solid #{TURQUESA};padding-bottom:2px;">
          Aceder à fonte original &rarr;
        </a>
      </div>
    </div>"""

    MESES_ABREV = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    html += f"""
  </div><!-- /conteúdo -->

  <!-- RODAPÉ -->
  <div style="text-align:center;padding:25px 30px;background-color:#{ESCURO};
              color:#{CREME};font-family:'Lora','Times New Roman',serif;">
    <p style="margin:0;font-size:14px;letter-spacing:1px;font-weight:bold;">
      ALL NEWS JOURNAL
    </p>
    <p style="margin:8px 0 0;opacity:0.7;font-size:11px;">
      © {hoje.year} All News Journal Group &nbsp;·&nbsp; Conteúdo Premium Digital
    </p>
    <p style="margin:6px 0 0;font-size:10px;opacity:0.5;">
      Recebeu esta edição porque é assinante do nosso serviço.
    </p>
  </div>

</div><!-- /wrapper -->
</body></html>"""
    return html

# =============================================================================
# --- 14. ENVIO DE E-MAIL ---
# =============================================================================
def enviar_email(dest, html):
    try:
        hoje  = datetime.now()
        MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
        msg   = MIMEMultipart()
        msg["Subject"] = f"📰 All News Journal — {hoje.day} de {MESES[hoje.month - 1]}. de {hoje.year}"
        msg["From"]    = f"All News Journal <{EMAIL_SENDER}>"
        msg["To"]      = dest
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, dest, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"      ❌ Erro ao enviar para {dest}: {e}")
        return False

# =============================================================================
# --- 15. MAIN ---
# =============================================================================
def main():
    print("🚀 All News Journal — Motor v14.0")
    print("   Fixes: Contexto Base | Mercado≠Política | Fitness PT-BR | Fofoca Global")
    print("─" * 65)

    if not validar_ambiente():
        return

    sheet_usuarios, sheet_historico, sheet_logs = conectar_banco()
    if not sheet_usuarios:
        return

    historico_hashes = carregar_historico(sheet_historico)
    usuarios         = sheet_usuarios.get_all_records()
    print(f"   👥 {len(usuarios)} assinantes encontrados.")

    # Descobre temas necessários
    temas_demandados = {
        tema
        for usr in usuarios
        for tema in RSS_FEEDS
        if str(usr.get(tema, "")).strip().lower() in {"sim"} or str(usr.get(tema, "")).strip().isdigit()
    }
    print(f"   📰 Temas a processar: {', '.join(sorted(temas_demandados))}")

    # Processa cada tema uma vez (cache global)
    painel       = obter_indicadores()
    CACHE_GLOBAL = {}
    novas        = []

    for tema in temas_demandados:
        resultado = processar_tema(tema, historico_hashes)
        if resultado:
            CACHE_GLOBAL[tema] = resultado
            novas.extend(resultado)
            print(f"      ✅ {tema}: {len(resultado)} notícias prontas.")
        else:
            print(f"      ⚠️ {tema}: nenhuma notícia disponível hoje.")

    if novas:
        salvar_no_historico(sheet_historico, novas)
        print(f"   💾 {len(novas)} notícias salvas no histórico.")

    # Distribui para cada assinante
    print("\n🚚 Iniciando distribuição…")
    enviados = falhas = 0

    for usr in usuarios:
        nome  = usr.get("Nome",  "").strip()
        email = usr.get("Email", "").strip()

        if not nome or not email:
            continue
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            print(f"   ⚠️ E-mail inválido: '{email}' — pulando.")
            continue

        # Monta pacote respeitando a ordem personalizada do assinante
        temas_com_ordem = []
        for tema in RSS_FEEDS:
            val = str(usr.get(tema, "")).strip()
            if val.lower() in {"", "não"}:
                continue
            if tema not in CACHE_GLOBAL:
                continue
            ordem = int(val) if val.isdigit() else 999
            temas_com_ordem.append((ordem, tema))

        temas_com_ordem.sort(key=lambda x: x[0])
        pacote = {tema: CACHE_GLOBAL[tema] for _, tema in temas_com_ordem}

        if not pacote:
            print(f"   ⚠️ {nome}: nenhum tema disponível.")
            continue

        print(f"   ✉️  {nome} → {list(pacote.keys())}")
        ok = enviar_email(email, gerar_html_final(nome, pacote, painel))
        registrar_log(sheet_logs, nome, email, ok, list(pacote.keys()))

        if ok:
            enviados += 1
        else:
            falhas += 1

    print(f"\n{'─'*65}")
    print(f"✅ Concluído — Enviados: {enviados}  |  Falhas: {falhas}")

if __name__ == "__main__":
    main()
