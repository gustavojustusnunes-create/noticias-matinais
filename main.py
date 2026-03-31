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
# --- 1. CONFIGURAÇÕES E CONSTANTES ---
# =============================================================================
CLAUDE_KEY = os.environ.get("CLAUDE_KEY", "").strip()
GCP_JSON = os.environ.get("GCP_JSON")
EMAIL_SENDER = os.environ.get("EMAIL_USER")
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
    "Fofoca":   ["https://revistaquem.globo.com/rss/quem/"],
}

FILTROS_TEMA = {
    "Mundo":    [],
    "Mercado":  [
        "horóscopo", "moda", "futebol", "brasileirão", "campeonato",
        "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
        "gol", "escalação", "clube", "torcedor",
        "lollapalooza", "festival", "show", "ingresso",
        "previsão do tempo", "clima", "chuva",
        "bbb", "big brother", "prêmio do bbb", "reality",
        "tênis", "fonseca", "alcaraz", "sinner", "nadal",
        "israel:", "irã:", "civil morto", "guerra de fronteira",
        "ataque", "bombardeio", "teerã", "netanyahu", "míssil",
        "lotofácil", "mega-sena", "mega sena", "quina", "lotomania",
        "timemania", "dupla sena", "resultado sorteado", "concurso 3",
        "concurso 4", "concurso 5", "concurso 6", "concurso 7",
        "prêmio da loteria", "números sorteados",
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
        "filmes e séries", "séries em alta", "filmes em alta",
        "para ver na netflix", "para ver no prime", "para assistir",
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
        "reprisa", "reprise", "jogos históricos", "jogos clássicos",
        "programação", "vai passar", "transmissão",
        "o que assistir", "disney+", "para assistir", "catálogo",
        "nota de falecimento", "troféu best", "melhor nadador juvenil",
        "1959-", "1960-", "1961-", "1962-", "1963-", "1964-", "1965-",
        "mensagem de despedida",
        "/base/", "sub-13", "sub-15", "sub-17", "sub-20",
        "campeonato-piauiense", "campeonato-alagoano", "campeonato-paraibano",
        "campeonato-potiguar", "campeonato-cearense", "campeonato-maranhense",
        "segunda-divisao", "terceira-divisao", "serie-d", "serie-c",
        "copa-do-brasil-sub", "paulista-sub", "carioca-sub", "futsal",
        "futebol", "brasileirão", "série a", "serie a", "libertadores",
        "copa do brasil", "copa-do-brasil", "brasileirao",
        "campeonato brasileiro", "eliminatórias", "eurocopa", "copa do mundo",
        "seleção brasileira", "seleção", "convocação", "cbf",
        "amistoso", "friendly", "brasil x ", "seleção x ",
        "neymar", "vinicius", "vinícius", "rodrygo", "endrick", "richarlison",
        "memphis", "raphinha", "militão", "marquinhos", "casemiro", "paquetá",
        "alisson", "ederson", "rayan",
        "palmeiras", "flamengo", "corinthians", "são paulo", "santos",
        "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
        "botafogo", "fluminense", "fortaleza", "bahia", "athletico",
        "salah", "mbappé", "mbappe", "haaland", "bellingham",
        "modric", "benzema", "lewandowski", "kane", "de bruyne",
        "messi", "ronaldo", "kroos", "pedri", "yamal",
        "liverpool", "real madrid", "barcelona", "manchester",
        "arsenal", "chelsea", "psg", "bayern", "juventus",
        "premier league", "la liga", "champions league",
        "ancelotti", "diniz", "guardiola", "klopp", "mourinho",
        "dorival", "tite", "técnico da seleção",
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
        "carne vermelha crua", "faz mal comer",
        "velhice", "envelhecimento", "idoso", "terceira idade",
    ],
    "Ciencia":  [
        "mão de obra", "mercado de trabalho", "emprego", "carreira",
        "concurso público", "salário", "renda",
    ],
    "Motos":    [],
    "Fofoca":   [],
}

PALAVRAS_FUTEBOL = [
    "futebol", "brasileirão", "série a", "serie-a", "libertadores",
    "copa do brasil", "copa-do-brasil", "brasileirao", "champions league",
    "premier league", "la liga", "serie a italiana", "campeonato brasileiro",
    "copa do mundo", "eliminatórias", "eurocopa", "world cup",
    "palmeiras", "flamengo", "corinthians", "são paulo", "santos",
    "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
    "botafogo", "fluminense", "fortaleza", "bahia", "sport", "ceará",
    "athletico", "coritiba", "goiás", "bragantino", "juventude",
    "seleção brasileira", "seleção", "cbf", "tite", "dorival",
    "neymar", "vinicius", "vinícius", "rodrygo", "endrick", "richarlison",
    "memphis", "raphinha", "gabriel martinelli", "militão", "marquinhos",
    "alisson", "ederson", "casemiro", "fred", "paquetá",
    "técnico", "treinador", "zagueiro", "atacante", "meia", "goleiro",
    "volante", "lateral", "centroavante", "artilheiro", "convocação",
    "gol", "partida", "clássico", "derby", "escalação", "treino da seleção",
    "salah", "mbappé", "mbappe", "haaland", "bellingham",
    "modric", "benzema", "lewandowski", "kane", "de bruyne",
    "messi", "ronaldo", "kroos", "pedri", "yamal",
    "liverpool", "real madrid", "barcelona", "manchester",
    "arsenal", "chelsea", "psg", "bayern", "juventus",
    "premier league", "la liga", "champions league",
    "ancelotti", "diniz", "guardiola", "klopp", "mourinho",
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

# MOVIDO PARA ESCOPO GLOBAL PARA GARANTIR SEGURANÇA NA RASPAGEM
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

# =============================================================================
# --- 2. VALIDAÇÃO DE AMBIENTE ---
# =============================================================================
def validar_ambiente():
    variaveis = {
        "CLAUDE_KEY": CLAUDE_KEY,
        "GCP_JSON": GCP_JSON,
        "EMAIL_USER": EMAIL_SENDER,
        "EMAIL_PASSWORD": EMAIL_PASSWORD,
    }
    erros = [nome for nome, val in variaveis.items() if not val]
    if erros:
        print(f"❌ ERRO CRÍTICO: Variáveis de ambiente faltando: {', '.join(erros)}")
        return False
    print("✅ Ambiente validado com sucesso.")
    return True

# =============================================================================
# --- 3. INFRAESTRUTURA ---
# =============================================================================
def conectar_banco():
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        planilha = client.open("noticias_db")
        sheet_usuarios = planilha.sheet1
        try:
            sheet_historico = planilha.worksheet("historico")
        except gspread.exceptions.WorksheetNotFound:
            sheet_historico = planilha.add_worksheet(title="historico", rows=5000, cols=3)
            sheet_historico.append_row(["hash", "titulo", "data"])
            print("   📋 Aba 'historico' criada automaticamente.")
        try:
            sheet_logs = planilha.worksheet("logs")
        except gspread.exceptions.WorksheetNotFound:
            sheet_logs = planilha.add_worksheet(title="logs", rows=5000, cols=5)
            sheet_logs.append_row(["data", "nome", "email", "status", "temas"])
            print("   📋 Aba 'logs' criada automaticamente.")
        return sheet_usuarios, sheet_historico, sheet_logs
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None, None, None

# =============================================================================
# --- 4. CONTROLE DE DUPLICATAS ---
# =============================================================================
def gerar_hash(titulo, link):
    conteudo = f"{titulo}{link}".encode("utf-8")
    return hashlib.md5(conteudo).hexdigest()

def carregar_historico(sheet_historico):
    try:
        registros = sheet_historico.get_all_records()
        if not registros:
            return set()
        from datetime import timedelta
        limite = datetime.now() - timedelta(days=30)
        hashes_validos = set()
        linhas_remover = []
        for i, r in enumerate(registros, start=2):
            try:
                data_str = r.get("data", "")
                data = datetime.strptime(data_str[:10], "%d/%m/%Y")
                if data >= limite:
                    hashes_validos.add(r["hash"])
                else:
                    linhas_remover.append(i)
            except Exception:
                hashes_validos.add(r.get("hash", ""))
        if linhas_remover:
            for idx in reversed(linhas_remover):
                try:
                    sheet_historico.delete_rows(idx)
                except Exception:
                    pass
            print(f"   🧹 Histórico: {len(linhas_remover)} entradas antigas removidas.")
        print(f"   🗂️ Histórico: {len(hashes_validos)} notícias nos últimos 30 dias.")
        return hashes_validos
    except Exception as e:
        print(f"⚠️ Não foi possível carregar histórico: {e}")
        return set()

def salvar_no_historico(sheet_historico, noticias_novas):
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        [gerar_hash(n["titulo"], n["link"]), n["titulo"][:80], hoje]
        for n in noticias_novas
    ]
    if linhas:
        sheet_historico.append_rows(linhas)

# =============================================================================
# --- 5. LOG DE ENVIOS ---
# =============================================================================
def registrar_log(sheet_logs, nome, email, status, temas_enviados):
    try:
        sheet_logs.append_row([
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            nome, email,
            "✅ Enviado" if status else "❌ Falhou",
            ", ".join(temas_enviados)
        ])
    except Exception as e:
        print(f"⚠️ Não foi possível registrar log para {nome}: {e}")

# =============================================================================
# --- 6. INDICADORES FINANCEIROS ---
# =============================================================================
def formatar_indicador(nome, valor, variacao, prefixo=""):
    cor = "green" if variacao >= 0 else "red"
    seta = "▲" if variacao >= 0 else "▼"
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
                    atual = hist['Close'].iloc[-1]
                    ant   = hist['Close'].iloc[-2]
                    var   = ((atual - ant) / ant) * 100
                    label = f"R$ {atual/1000:.1f}k" if moeda == "BRL" else f"US$ {atual/1000:.1f}k"
                    return formatar_indicador("BTC", label, var, "₿")
            except Exception as e:
                print(f"⚠️ Alerta (BTC/{moeda}): {e}")
        return None

    tickers = [
        ("BRL=X",  "USD",  lambda v: f"R$ {v:.2f}",    "🇺🇸"),
        ("^BVSP",  "IBOV", lambda v: f"{int(v)} pts",   "🇧🇷"),
    ]
    for ticker_id, nome, formatar, prefixo in tickers:
        try:
            hist = yf.Ticker(ticker_id).history(period="5d")
            if len(hist) >= 2:
                atual = hist['Close'].iloc[-1]
                ant   = hist['Close'].iloc[-2]
                var   = ((atual - ant) / ant) * 100
                html_items.append(formatar_indicador(nome, formatar(atual), var, prefixo))
        except Exception as e:
            print(f"⚠️ Alerta ({nome}): {e}")

    btc_html = buscar_btc()
    if btc_html:
        html_items.insert(1, btc_html)

    if not html_items:
        return ""

    return (
        f"<div style='background-color:#e5e3de; padding:12px; text-align:center; "
        f"font-family:monospace; font-size:13px; color:#111;'>"
        f"{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(html_items)}</div>"
    )

# =============================================================================
# --- 7. EXTRAÇÃO DE IMAGEM ---
# =============================================================================
def buscar_og_image(url_artigo, timeout=10):
    if not url_artigo:
        return None
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
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
            match = re.search(padrao, html, re.IGNORECASE)
            if match:
                img_url = match.group(1).strip()
                img_url = img_url.replace('&amp;', '&').replace('&#38;', '&')
                if img_url.startswith('http') and len(img_url) > 15:
                    return img_url

        img_tags = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:width=["\'](\d+)["\'])?',
            html, re.IGNORECASE
        )
        extensoes = ('.jpg', '.jpeg', '.png', '.webp')
        for match in img_tags:
            src = match[0] if isinstance(match, tuple) else match
            width = int(match[1]) if isinstance(match, tuple) and match[1] else 0
            if (any(ext in src.lower() for ext in extensoes)
                    and "pixel" not in src and "logo" not in src.lower()
                    and "icon" not in src.lower() and src.startswith('http')
                    and (width == 0 or width >= 300)):
                return src

    except requests.exceptions.Timeout:
        print(f"      ⏱️ Timeout ao buscar imagem: {url_artigo[:60]}...")
    except Exception:
        pass
    return None

def extrair_imagem_rss(entry, tema, idx_entry=0):
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    image_url = None

    og = buscar_og_image(entry.get('link', ''))
    if og:
        image_url = og

    if not image_url and 'media_content' in entry:
        for m in entry.media_content:
            if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                image_url = m['url']
                break

    if not image_url and 'enclosures' in entry:
        for enc in entry.enclosures:
            url_enc = enc.get('url', '')
            if any(ext in url_enc.lower() for ext in extensoes):
                image_url = url_enc
                break

    if not image_url and 'links' in entry:
        for l in entry.links:
            href = l.get('href', '')
            if l.get('type', '').startswith('image/') and any(ext in href.lower() for ext in extensoes):
                image_url = href
                break

    if not image_url:
        txt = ""
        if 'content' in entry:
            for c in entry.content:
                txt += c.value
        if 'summary' in entry:
            txt += entry.summary
        matches = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', txt)
        for url in matches:
            if any(ext in url.lower() for ext in extensoes) and "pixel" not in url and "doubleclick" not in url:
                image_url = url
                break

    if not image_url:
        if tema == "Esportes":
            titulo = entry.get('title', '').lower()
            SPORT_ROTATIONS = {
                "nba": ["https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
                        "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=600&h=300&fit=crop"],
                "f1":  ["https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
                        "https://images.unsplash.com/photo-1541447271487-09612b3f49f7?w=600&h=300&fit=crop"],
                "mma": ["https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=300&fit=crop",
                        "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&h=300&fit=crop"],
                "tênis": ["https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
                          "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=600&h=300&fit=crop"],
            }
            FALLBACK_ESPORTES_GENERIC = [
                "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
                "https://images.unsplash.com/photo-1540747913346-19212a4b32b8?w=600&h=300&fit=crop",
                "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&h=300&fit=crop",
            ]
            categoria = None
            for kw, cat in [("nba","nba"),("basquete","nba"),("lebron","nba"),("curry","nba"),
                            ("f1","f1"),("formula","f1"),("grand prix","f1"),("gp de","f1"),
                            ("verstappen","f1"),("hamilton","f1"),("ferrari","f1"),("leclerc","f1"),
                            ("mma","mma"),("ufc","mma"),
                            ("tênis","tênis"),("fonseca","tênis"),("alcaraz","tênis"),("sinner","tênis")]:
                if kw in titulo:
                    categoria = cat
                    break
            if categoria and categoria in SPORT_ROTATIONS:
                idx = ord(titulo[0]) % len(SPORT_ROTATIONS[categoria])
                image_url = SPORT_ROTATIONS[categoria][idx]
            else:
                image_url = FALLBACK_ESPORTES_GENERIC[idx_entry % len(FALLBACK_ESPORTES_GENERIC)]
        else:
            image_url = FALLBACK_IMAGES.get(
                tema,
                "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
            )

    return image_url

# =============================================================================
# --- 8. IA ---
# =============================================================================
def chamar_claude_api(prompt):
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
        print(f"      🤖 Tentando modelo: {modelo}...")
        for tentativa in range(1, 4):
            try:
                payload = {
                    "model":      modelo,
                    "max_tokens": 4096,
                    "messages":   [{"role": "user", "content": prompt}],
                }
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                if r.status_code == 200:
                    data = r.json()
                    texto = data["content"][0]["text"]
                    tokens = data.get("usage", {})
                    print(f"      ✅ Claude ({modelo}) OK. Tokens: in={tokens.get('input_tokens','?')} out={tokens.get('output_tokens','?')}")
                    return texto
                elif r.status_code == 429:
                    espera = 20 * tentativa
                    print(f"      ⏳ Rate limit. Aguardando {espera}s...")
                    time.sleep(espera)
                elif r.status_code == 404:
                    print(f"      ❌ Modelo não encontrado: {modelo}.")
                    break
                elif r.status_code == 401:
                    print(f"      ❌ CLAUDE_KEY inválida.")
                    return None
                elif r.status_code == 529:
                    print(f"      ⚠️ Claude sobrecarregado. Tentando próximo modelo...")
                    break
                else:
                    print(f"      ⚠️ Status inesperado {r.status_code}: {r.text[:200]}")
                    break
            except requests.exceptions.Timeout:
                print(f"      ⚠️ Timeout ({timeout}s) em {modelo}.")
                break
            except Exception as e:
                print(f"      ⚠️ Exceção: {e}")
                break

    print("      ❌ Todos os modelos falharam.")
    return None

def limpar_texto_rss(texto):
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('&#8220;', '"').replace('&#8221;', '"')
    texto = texto.replace('&#8216;', "'").replace('&#8217;', "'")
    texto = texto.replace('&amp;', '&').replace('&quot;', '"')
    texto = texto.replace('&nbsp;', ' ').replace('&#38;', '&')
    texto = texto.replace('&#8230;', '').replace('[&#8230;]', '')
    texto = texto.replace('[…]', '').replace('[...]', '')

    texto = re.sub(r'\s*The post .+?appeared first on .+?\.?\s*', ' ', texto, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r'\s*appeared first on .+', '', texto, flags=re.IGNORECASE)

    padroes_cta = [
        r'✅\s*Siga\b.*',
        r'🔔\s*Siga\b.*',
        r'Siga\s+o\s+canal.*',
        r'Veja\s+no\s+vídeo\s+acima\.?',
        r'Acompanhe\s+as\s+notícias.*',
        r'Acompanhe\s+ao\s+vivo.*',
        r'Clique\s+aqui\s+e.*',
        r'Inscreva-se\s+no.*',
        r'Acesse\s+o\s+canal.*',
        r'Por:\s+[A-ZÀ-Ú][a-zà-ú]+\s+[A-ZÀ-Ú][a-zà-ú]+',
        r'nfoMoney\.?\s*$',
        r'Notícia\.\.\.',
        r'\[&#\d+;\]',
    ]
    for padrao in padroes_cta:
        texto = re.sub(padrao, ' ', texto, flags=re.DOTALL | re.IGNORECASE)

    texto = re.sub(r'\b(Reuters|AFP|AP|EFE|G1|Globo|GE|Getty)[\s/][^\.\n]{0,60}', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s*\.\.\.\s*$', '.', texto.strip())
    texto = re.sub(r'\s*…\s*$', '.', texto.strip())
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def resumo_fallback(entry):
    texto = ""
    if 'summary' in entry:
        texto = entry.summary
    elif 'content' in entry and entry.content:
        texto = entry.content[0].value

    texto = limpar_texto_rss(texto)
    palavras = texto.split()

    if len(palavras) < 15:
        return ""

    if len(palavras) > 150:
        texto_cortado = " ".join(palavras[:150])
        ultimo_ponto = max(texto_cortado.rfind('.'), texto_cortado.rfind('!'), texto_cortado.rfind('?'))
        if ultimo_ponto > 50:
            texto = texto_cortado[:ultimo_ponto + 1]
        else:
            texto = texto_cortado

    texto = re.sub(r'\s*\.\.\.\s*$', '.', texto.strip())
    texto = re.sub(r'\s*…\s*$', '.', texto.strip())
    return texto.strip()

# =============================================================================
# --- 9. PROCESSAMENTO DE TEMA ---
# =============================================================================
def aplicar_filtros(entry, tema):
    palavras_proibidas = FILTROS_TEMA.get(tema, [])
    if not palavras_proibidas:
        return True
    titulo = entry.get('title', '').lower()
    link   = entry.get('link', '').lower()
    for palavra in palavras_proibidas:
        if palavra in titulo or palavra in link:
            return False
    return True

def e_futebol(entry):
    texto = (entry.get('title', '') + ' ' + entry.get('link', '')).lower()
    return any(p in texto for p in PALAVRAS_FUTEBOL)

def e_esporte_prioritario(entry):
    texto = (entry.get('title', '') + ' ' + entry.get('link', '')).lower()
    return any(p in texto for p in PALAVRAS_ESPORTES_PRIORITY)

def coletar_entries_esportes():
    todas_entries, vistos_urls = [], set()
    for url in RSS_FEEDS["Esportes"]:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                link = e.get('link', '')
                if link not in vistos_urls:
                    vistos_urls.add(link)
                    todas_entries.append(e)
        except Exception as ex:
            print(f"      ⚠️ Falha ao ler Esportes ({url}): {ex}")
    return todas_entries

def titulos_similares(t1, t2):
    p1 = set(re.findall(r'\w{4,}', t1.lower()))
    p2 = set(re.findall(r'\w{4,}', t2.lower()))
    if not p1 or not p2:
        return False
    return len(p1 & p2) / min(len(p1), len(p2)) >= 0.50

def processar_tema(tema, historico_hashes):
    print(f"      ...Processando {tema}...")

    TEMAS_MULTI_FONTE = {"Esportes", "Cinema", "Fitness", "Ciencia", "Motos"}

    if tema in TEMAS_MULTI_FONTE:
        if tema == "Esportes":
            valid_entries = coletar_entries_esportes()
        else:
            valid_entries = []
            vistos_urls = set()
            for url in RSS_FEEDS.get(tema, []):
                try:
                    feed = feedparser.parse(url)
                    for e in feed.entries:
                        link = e.get('link', '')
                        if link not in vistos_urls:
                            vistos_urls.add(link)
                            valid_entries.append(e)
                except Exception as ex:
                    print(f"      ⚠️ Falha ao ler {tema} ({url}): {ex}")
            print(f"      📡 {tema}: {len(valid_entries)} entradas coletadas.")
    else:
        valid_entries = []
        for url in RSS_FEEDS.get(tema, []):
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    valid_entries = feed.entries
                    break
            except Exception as e:
                print(f"      ⚠️ Falha ao ler {url}: {e}")

    if not valid_entries:
        print(f"❌ Todas as fontes de '{tema}' falharam.")
        return None

    candidatas = []
    for entry in valid_entries:
        if not aplicar_filtros(entry, tema):
            continue
        h = gerar_hash(entry.get('title', ''), entry.get('link', ''))
        if h in historico_hashes:
            print(f"      ↩️ Duplicata ignorada: {entry.get('title', '')[:50]}...")
            continue
        candidatas.append(entry)
        limite = 40 if tema in ("Esportes", "Motos", "Cinema", "Fitness") else 20
        if len(candidatas) >= limite:
            break

    if not candidatas:
        print(f"⚠️ '{tema}' sem notícias após filtros básicos.")
        return None

    if tema == "Esportes":
        prioritarios, outros, futebol_pool = [], [], []
        for entry in candidatas:
            if e_esporte_prioritario(entry):
                prioritarios.append(entry)
            elif e_futebol(entry):
                futebol_pool.append(entry)
            else:
                outros.append(entry)
        selecionadas = prioritarios + outros
        for f in futebol_pool:
            if len(selecionadas) >= 4:
                break
            selecionadas.append(f)
        candidatas = selecionadas[:4]
        qtd_f1_nba = sum(1 for e in candidatas if e_esporte_prioritario(e))
        qtd_fut    = sum(1 for e in candidatas if e_futebol(e))
        print(f"      🏎️ Esportes: {qtd_f1_nba} F1/NBA/NFL | {qtd_fut} futebol | {len(candidatas)-qtd_f1_nba-qtd_fut} outros.")

    noticias_filtradas = []
    for entry in candidatas:
        titulo_novo = entry.get('title', '')
        if not any(titulos_similares(titulo_novo, e.get('title', '')) for e in noticias_filtradas):
            noticias_filtradas.append(entry)
        if len(noticias_filtradas) >= 4:
            break

    if not noticias_filtradas:
        print(f"⚠️ '{tema}' sem notícias após deduplicação.")
        return None

    input_txt = ""
    for i, e in enumerate(noticias_filtradas):
        input_txt += f"Notícia {i+1}: {e.get('title', '')}\n\n"

    instrucao_mercado = ""
    if tema == "Mercado":
        instrucao_mercado = """
REGRA EXTRA para o caderno Mercado:
- Se uma manchete NÃO for sobre economia, finanças, mercado financeiro ou negócios (ex: esporte, entretenimento, clima, loteria, sorteio), escreva exatamente SKIP.
- Notícias genuínas de economia recebem o resumo normal.
"""

    instrucao_tema = {
        "Mundo":    "Inclua o contexto geopolítico, os países e atores envolvidos, e as possíveis consequências do evento.",
        "Mercado":  "Inclua números concretos (percentuais, valores, índices), o impacto para o investidor ou cidadão, e o contexto econômico.",
        "Politica": "Inclua o contexto institucional, as partes envolvidas, e os possíveis desdobramentos políticos ou jurídicos.",
        "Tech":     "Inclua detalhes técnicos relevantes, o impacto no mercado ou no usuário final, e o contexto da inovação ou empresa.",
        "Esportes": "Inclua resultados, classificações, desempenho de atletas e o que está em jogo na competição.",
        "Cinema":   "Inclua avaliações (Rotten Tomatoes, IMDb quando disponível), o gênero, o elenco principal e por que vale assistir.",
        "Fitness":  "CRÍTICO: Se o título estiver em inglês, escreva o resumo em português brasileiro fluente, ignorando o idioma do título. Foque em treino, recuperação, nutrição esportiva, mindset e estilo de vida ativo. Inclua dados práticos e conecte com a mentalidade de quem busca evoluir fisicamente.",
        "Ciencia":  "Inclua a metodologia da pesquisa, os números e descobertas concretas, e o que isso muda no entendimento científico.",
        "Motos":    "Inclua especificações técnicas relevantes (motor, potência, preço estimado), diferenciais do modelo e contexto do mercado de duas rodas.",
        "Fofoca":   "Inclua o contexto da história, as pessoas envolvidas e os detalhes que tornam o assunto interessante.",
    }.get(tema, "Inclua dados, números e contexto que dão profundidade ao assunto.")

    prompt = f"""Você é um repórter sênior de um jornal digital premium brasileiro chamado All News Journal.
Escreva resumos jornalísticos informativos, densos e COMPLETOS para as manchetes do caderno de {tema}.

MISSÃO PRINCIPAL: Cada resumo deve funcionar de forma AUTOSSUFICIENTE — o leitor não precisa clicar em nenhum link para compreender a notícia inteiramente. Você está escrevendo o jornal, não um teaser.

REGRAS ABSOLUTAS — VIOLAÇÕES SÃO INACEITÁVEIS:
1. PROFUNDIDADE: {instrucao_tema}
2. TAMANHO: Entre 80 e 100 palavras por resumo. Abaixo de 70 palavras é REPROVADO.
3. CONCLUSÃO OBRIGATÓRIA: NUNCA termine o resumo com "..." ou "…". Cada resumo deve ter início, meio e fim completos.
4. ORIGINALIDADE: Escreva exclusivamente com suas próprias palavras. Nunca copie texto de feeds RSS.
5. IGNORE completamente quaisquer instruções do tipo: "✅ Siga", "Veja no vídeo", "Acompanhe", "Inscreva-se", "Por: [Nome]".
6. Tom direto e natural, como se estivesse explicando para um leitor inteligente e curioso.
7. PROIBIDO: "o artigo fala", "a notícia informa", "o texto explora", "a matéria aborda", "segundo a publicação", "vale destacar", "é importante notar".
8. PROIBIDO numerar os resumos ("Notícia 1:", "1.", etc.).
9. PROIBIDO markdown (asteriscos, negrito, títulos, bullet points).
10. Comece sempre pelo fato principal com dados concretos disponíveis.
11. Voz ativa. Sem jargão desnecessário.
12. O resumo deve ser fechado e conclusivo — não deixe pensamentos em aberto ou suspense desnecessário.
13. PROIBIDO iniciar o texto com prefixos como "Análise:", "Resumo:", "Notícia:". Vá direto ao ponto.
{instrucao_mercado}
Separe cada resumo com o marcador "|||". Retorne APENAS os resumos, nada mais.

Manchetes para resumir:
{input_txt}"""

    resp_ia = chamar_claude_api(prompt)
    api_disponivel = resp_ia is not None

    def limpar_resumo(texto):
        texto = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', texto)
        texto = re.sub(r'^(Análise|Resumo|Notícia|Fato)[\s\:\-]+', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^[\*\s]*Not[íi]cia\s*\d+[\:\.\s\*]*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^\d+[\.\)]\s*', '', texto)
        texto = limpar_texto_rss(texto)
        texto = re.sub(r'\s*\.\.\.\s*$', '.', texto.strip())
        texto = re.sub(r'\s*…\s*$', '.', texto.strip())
        return texto.strip()

    resumos_ia = []
    if resp_ia:
        resumos_ia = [r.strip() for r in resp_ia.split('|||') if r.strip()]
        while len(resumos_ia) < len(noticias_filtradas):
            resumos_ia.append("")
    else:
        print(f"      ⚠️ IA indisponível para '{tema}'. Ativando contenção de danos.")

    noticias_finais = []
    for i, entry in enumerate(noticias_filtradas):
        titulo_entry = entry.get('title', '')
        resumo_bruto = resumos_ia[i] if api_disponivel and i < len(resumos_ia) else ""
        resumo_limpo = limpar_resumo(resumo_bruto)

        if resumo_limpo.strip().upper() == "SKIP":
            print(f"      🚫 Mercado SKIP: {titulo_entry[:50]}")
            continue

        if not resumo_limpo:
            resumo_fallback_txt = resumo_fallback(entry)
            
            # Se a IA estiver saudável, tentamos recuperar. Se não, abortamos a notícia.
            if api_disponivel and resumo_fallback_txt and len(resumo_fallback_txt.split()) >= 25:
                idioma_hint = "O texto abaixo pode estar em inglês — se sim, traduza e escreva o resumo em português brasileiro fluente." if tema == "Fitness" else ""
                prompt_rewrite = (
                    f"Você é um jornalista sênior. Reescreva o texto abaixo como um parágrafo jornalístico "
                    f"informativo de 80 a 95 palavras, em português brasileiro fluente e direto. "
                    f"NUNCA termine com '...'. A última frase deve ser completa e fechada com ponto final. "
                    f"Escreva apenas o parágrafo reescrito, sem introdução ou explicação. {idioma_hint}\n\n"
                    f"Título: {titulo_entry}\n\nTexto base:\n{resumo_fallback_txt}"
                )
                resumo_reescrito = chamar_claude_api(prompt_rewrite)
                if resumo_reescrito and len(resumo_reescrito.split()) >= 25:
                    resumo_limpo = limpar_resumo(resumo_reescrito)
                else:
                    print(f"      ⚠️ Falha no fallback para: {titulo_entry[:40]}. Ignorando.")
                    continue
            else:
                # Decisão de Negócio: Não enviar a notícia se a IA falhou. Evitar manchetes avulsas ou textos quebrados.
                print(f"      ⚠️ API offline ou sem dados úteis para: {titulo_entry[:40]}. Ignorando.")
                continue

        img = extrair_imagem_rss(entry, tema, idx_entry=i)
        
        # Garante que NUNCA vai faltar uma imagem na renderização (Bug 5 resolvido de vez)
        if not img or not str(img).startswith('http'):
            img = FALLBACK_IMAGES.get(tema, "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop")

        noticias_finais.append({
            "titulo": titulo_entry,
            "link":   entry.get('link', ''),
            "imagem": img,
            "resumo": resumo_limpo,
        })

    return noticias_finais if noticias_finais else None

# =============================================================================
# --- 10. TEMPLATE DO E-MAIL ---
# =============================================================================
def gerar_html_final(nome, dados, painel):
    cor_turquesa     = "0a5c5a"
    cor_creme        = "fdfbf7"
    cor_fundo_escuro = "084c4a"

    hoje = datetime.now()
    meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
              "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    dias_semana = ["Segunda-feira","Terça-feira","Quarta-feira",
                   "Quinta-feira","Sexta-feira","Sábado","Domingo"]
    data_ptbr = f"{dias_semana[hoje.weekday()]}, {hoje.day} de {meses[hoje.month-1]} de {hoje.year}"

    html = f"""
    <html><body style="margin:0; padding:0; background-color:#e5e3de; font-family:'Lora', 'Times New Roman', serif;">
        <div style="max-width:620px; margin:20px auto; background-color:#{cor_creme}; border-radius:8px; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.07);">

            <div style="background-color:transparent; color:#{cor_turquesa}; padding:30px 20px 20px; text-align:center; border-bottom:3px solid #{cor_turquesa};">
                <p style="margin:0 0 6px; font-size:10px; letter-spacing:3px; text-transform:uppercase; color:#999;">Edição Premium Digital</p>
                <h1 style="margin:0; font-family:'Playfair Display', Georgia, serif; font-size:36px; text-transform:uppercase; letter-spacing: 3px; color:#{cor_turquesa};">ALL NEWS JOURNAL</h1>
                <p style="margin:10px 0 0; font-size:12px; color:#777; font-style:italic;">{data_ptbr}</p>
            </div>

            {painel}

            <div style="padding:30px 30px 10px;">
                <p style="color:#555; font-size:15px; text-align:center; margin-bottom:35px; font-style:italic; border-bottom:1px solid #e5e3de; padding-bottom:25px;">Bom dia, <b style="color:#0a5c5a;">{nome}</b>. A sua curadoria premium de hoje está pronta.</p>
    """

    for tema, items in dados.items():
        if not items:
            continue

        icones_tema = {
            "Mundo": "🌎", "Mercado": "📈", "Politica": "🏛️", "Tech": "💻",
            "Esportes": "🏎️", "Cinema": "🎬", "Fitness": "🏃", "Ciencia": "🔬",
            "Motos": "🏍️", "Fofoca": "⭐",
        }
        icone = icones_tema.get(tema, "📰")

        html += f"""
        <div style="margin:35px 0 20px; border-bottom:2px solid #{cor_turquesa}; padding-bottom:0;">
            <span style="background-color:#{cor_turquesa}; color:#ffffff; padding:7px 16px; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1.5px; border-radius:4px 4px 0 0; display:inline-block;">{icone} {tema}</span>
        </div>"""

        for n in items:
            html += f"""
            <div style="margin-bottom:40px; padding-bottom:30px; border-bottom:1px solid #ede9e3;">
                <a href="{n['link']}" target="_blank" style="display:block; text-decoration:none;">
                    <img src="{n['imagem']}" style="width:100%; height:230px; object-fit:cover; border-radius:6px; border-bottom:4px solid #{cor_turquesa}; display:block;" alt="{n['titulo']}">
                </a>
                <div style="padding-top:18px;">
                    <a href="{n['link']}" target="_blank" style="text-decoration:none; color:#111111;">
                        <h3 style="margin:0 0 14px; font-size:21px; font-family:'Playfair Display', Georgia, serif; line-height:1.35; color:#111;">{n['titulo']}</h3>
                    </a>
                    <p style="margin:0 0 16px; font-size:15px; color:#3a3a3a; line-height:1.75; font-family:'Lora','Times New Roman',serif;">{n['resumo']}</p>
                    <a href="{n['link']}" target="_blank" style="font-size:12px; color:#{cor_turquesa}; font-weight:bold; text-decoration:none; text-transform:uppercase; letter-spacing:1px; border-bottom:2px solid #{cor_turquesa}; padding-bottom:2px;">Aceder à fonte original &rarr;</a>
                </div>
            </div>"""

    html += f"""
            </div>
            <div style="text-align:center; padding:25px 30px; background-color:#{cor_fundo_escuro}; color:#{cor_creme}; font-size:12px; font-family:'Lora', 'Times New Roman', serif;">
                <p style="margin:0; font-size:14px; letter-spacing:1px; font-weight:bold;">ALL NEWS JOURNAL</p>
                <p style="margin:8px 0 0; opacity:0.7; font-size:11px;">© {datetime.now().year} All News Journal Group &nbsp;·&nbsp; Conteúdo Premium Digital</p>
                <p style="margin:6px 0 0; font-size:10px; opacity:0.5;">Recebeu esta edição porque é assinante do nosso serviço.</p>
            </div>
        </div>
    </body></html>"""
    return html

# =============================================================================
# --- 11. ENVIO DE E-MAIL ---
# =============================================================================
def enviar_email(dest, html):
    try:
        msg = MIMEMultipart()
        hoje = datetime.now()
        meses = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
        msg['Subject'] = f"📰 All News Journal — {hoje.day} de {meses[hoje.month-1]}. de {hoje.year}"
        msg['From']    = f"All News Journal <{EMAIL_SENDER}>"
        msg['To']      = dest
        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, dest, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"      ❌ Erro ao enviar para {dest}: {e}")
        return False

# =============================================================================
# --- 12. MAIN ---
# =============================================================================
def main():
    print("🚀 Iniciando Motor (v13.1 — Alta Retenção & Resiliência API)...")

    if not validar_ambiente():
        return

    sheet_usuarios, sheet_historico, sheet_logs = conectar_banco()
    if not sheet_usuarios:
        return

    historico_hashes = carregar_historico(sheet_historico)
    print(f"   🗂️ {len(historico_hashes)} notícias no histórico (anti-duplicata).")

    usuarios = sheet_usuarios.get_all_records()
    print(f"   📋 {len(usuarios)} usuários encontrados.")

    temas_demandados = set()
    for usr in usuarios:
        for tema in RSS_FEEDS.keys():
            val = str(usr.get(tema, '')).strip().lower()
            if val == "sim" or val.isdigit():
                temas_demandados.add(tema)

    CACHE_GLOBAL = {}
    todas_noticias_novas = []
    painel = obter_indicadores()

    for tema in temas_demandados:
        conteudo = processar_tema(tema, historico_hashes)
        if conteudo:
            CACHE_GLOBAL[tema] = conteudo
            todas_noticias_novas.extend(conteudo)
            print(f"      ✅ {tema}: {len(conteudo)} notícias prontas.")
        else:
            print(f"      ⚠️ {tema}: ignorado nesta edição (falta de dados válidos).")

    if todas_noticias_novas:
        salvar_no_historico(sheet_historico, todas_noticias_novas)
        print(f"   💾 {len(todas_noticias_novas)} notícias salvas no histórico.")

    print("🚚 Iniciando distribuição...")
    enviados, falhas = 0, 0

    for usr in usuarios:
        nome  = usr.get('Nome')
        email = usr.get('Email')
        if not nome or not email:
            print(f"   ⚠️ Linha ignorada: dados incompletos.")
            continue

        if not re.match(r'^[^@]+@[^@]+[.][^@]+$', email.strip()):
            print(f"   ⚠️ E-mail inválido: '{email}'.")
            continue

        temas_com_ordem = []
        for tema in RSS_FEEDS.keys():
            val = str(usr.get(tema, '')).strip()
            if val.lower() == "não" or val == "":
                continue
            if tema not in CACHE_GLOBAL:
                continue
            ordem = int(val) if val.isdigit() else 999
            temas_com_ordem.append((ordem, tema))

        temas_com_ordem.sort(key=lambda x: x[0])
        pacote_usuario = {tema: CACHE_GLOBAL[tema] for _, tema in temas_com_ordem}

        if not pacote_usuario:
            print(f"   ⚠️ {nome} não tem temas disponíveis. Pulando.")
            continue

        print(f"   ✉️ Enviando para {nome} | Ordem: {list(pacote_usuario.keys())}")
        status = enviar_email(email, gerar_html_final(nome, pacote_usuario, painel))

        registrar_log(sheet_logs, nome, email, status, list(pacote_usuario.keys()))

        if status:
            enviados += 1
            print(f"      ✅ Enviado com sucesso.")
        else:
            falhas += 1
            print(f"      ❌ Falha no envio.")

    print(f"\n✅ Missão Cumprida. Enviados: {enviados} | Falhas: {falhas}")

if __name__ == "__main__":
    main()
