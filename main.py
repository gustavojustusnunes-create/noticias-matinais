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
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()
GCP_JSON = os.environ.get("GCP_JSON")
EMAIL_SENDER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

RSS_FEEDS = {
    # Ordem padrão do sistema
    "Mundo":    ["https://g1.globo.com/rss/g1/mundo/"],
    "Mercado":  ["https://www.infomoney.com.br/feed/", "https://rss.uol.com.br/feed/economia.xml"],
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
        "https://g1.globo.com/rss/g1/bem-estar/",                # G1 Bem-Estar
        "https://extra.globo.com/rss/saude-e-ciencia/",          # Extra Saúde
        "https://oglobo.globo.com/rss/saude/",                   # O Globo Saúde
        "https://www.uol.com.br/vivabem/rss.xml",                # UOL VivaBem
        "https://saude.abril.com.br/feed/",                      # Saúde Abril
    ],
    "Ciencia":  [
        "https://g1.globo.com/rss/g1/ciencia-e-saude/",          # G1 Ciência e Saúde
        "https://gizmodo.uol.com.br/feed/",                      # Gizmodo UOL
        "https://www.inovacaotecnologica.com.br/boletim/rss.xml",# Inovação Tecnológica
        "https://www.tecmundo.com.br/ciencia/rss",               # TecMundo ciência
    ],
    "Motos":    [
        "https://www.motociclismoonline.com.br/feed/",           # Motociclismo Online
        "https://www.motoo.com.br/feed/",                        # Motoo
        "https://quatrorodas.abril.com.br/motos/feed/",          # Quatro Rodas motos
        "https://www.webmotors.com.br/noticias/motos/feed/",     # WebMotors motos
    ],
    "Fofoca":   ["https://revistaquem.globo.com/rss/quem/"],
}

# Filtros de palavras indesejadas por tema
FILTROS_TEMA = {
    "Mundo":    [],
    "Mercado":  ["horóscopo", "moda", "futebol", "brasileirão", "campeonato",
                 "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
                 "gol", "escalação", "clube", "torcedor",
                 "lollapalooza", "festival", "show", "ingresso",
                 "previsão do tempo", "clima", "chuva",
                 "bbb", "big brother", "prêmio do bbb", "reality",
                 "tênis", "fonseca", "alcaraz", "sinner", "nadal"],
    "Politica": [],
    "Tech":     ["aposta", "palpite", "futebol", "bônus", "cassino", "bet",
                 "guia-de-compras", "em-oferta", "promoção", "desconto",
                 "homenagem", "morre", "falece", "morte", "aniversário",
                 "ator", "atriz", "celebridade", "chuck norris", "stallone",
                 "troféus", "conquistas", "lista de troféus", "ps store",
                 "xbox game pass", "jogos grátis", "resgate agora",
                 "marinheiro", "porta-avião", "base militar",
                 # Séries e filmes — vão para Cinema
                 "séries live-action", "live-action", "temporada", "episódio",
                 "netflix planeja", "disney+", "hbo planeja",
                 "filmes e séries", "séries em alta", "filmes em alta",
                 "para ver na netflix", "para ver no prime", "para assistir",
                 # Listas de jogos — vão para Cinema ou são off-topic
                 "jogos para jogar", "jogos cooperativos", "melhores jogos",
                 # PC gamer off-topic
                 "quanto custa um pc", "pc gamer para jogar", "requisitos mínimos",
                 "configurações para rodar", "placa de vídeo para"],
    "Esportes": [
        "ao-vivo", "ao vivo", "/jogo/", "onde-assistir", "ingressos",
        "escalação", "prováveis-times",
        "reprisa", "reprise", "jogos históricos", "jogos clássicos",
        "programação", "vai passar", "transmissão",
        "/base/", "sub-13", "sub-15", "sub-17", "sub-20",
        "campeonato-piauiense", "campeonato-alagoano", "campeonato-paraibano",
        "campeonato-potiguar", "campeonato-cearense", "campeonato-maranhense",
        "segunda-divisao", "terceira-divisao", "serie-d", "serie-c",
        "copa-do-brasil-sub", "paulista-sub", "carioca-sub", "futsal",
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
    ],
    "Ciencia":  [],
    "Motos":    [],
    "Fofoca":   [],
}

# Palavras-chave de futebol para controle de proporção no caderno Esportes
# (máx 1 futebol em 4 — liberando espaço para F1, NBA, NFL)
PALAVRAS_FUTEBOL = [
    "futebol", "brasileirão", "série a", "serie-a", "libertadores",
    "copa do brasil", "palmeiras", "flamengo", "corinthians", "são paulo",
    "santos", "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
    "botafogo", "fluminense", "fortaleza", "bahia", "gol", "técnico",
    "treinador", "zagueiro", "atacante", "meia", "goleiro", "volante",
    "campeonato brasileiro", "premier league", "la liga", "serie a italiana",
    "champions league", "copa-do-brasil", "brasileirao"
]

# Palavras-chave de esportes prioritários (F1, NBA, NFL)
PALAVRAS_ESPORTES_PRIORITY = [
    "formula 1", "formula1", "fórmula 1", "fórmula1", "f1", "gp de",
    "grand prix", "verstappen", "hamilton", "leclerc", "norris", "ferrari",
    "red bull racing", "mercedes f1", "mclaren f1",
    "nba", "basquete", "basquetebol", "lakers", "warriors", "celtics",
    "lebron", "curry", "nfl", "futebol americano", "super bowl",
    "touchdown", "quarterback",
]

# =============================================================================
# --- 2. VALIDAÇÃO DE AMBIENTE (nova) ---
# =============================================================================
def validar_ambiente():
    """
    Valida todas as variáveis de ambiente obrigatórias antes de qualquer execução.
    Retorna True se tudo ok, False se algo estiver faltando.
    """
    variaveis = {
        "GEMINI_KEY": GEMINI_KEY,
        "GCP_JSON": GCP_JSON,
        "EMAIL_USER": EMAIL_SENDER,
        "EMAIL_PASSWORD": EMAIL_PASSWORD,
    }
    erros = [nome for nome, val in variaveis.items() if not val]
    if erros:
        print(f"❌ ERRO CRÍTICO: Variáveis de ambiente faltando: {', '.join(erros)}")
        print("   Configure-as nos Secrets do GitHub Actions antes de continuar.")
        return False
    print("✅ Ambiente validado com sucesso.")
    return True

# =============================================================================
# --- 3. INFRAESTRUTURA (banco de dados) ---
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

        # Garante que as abas auxiliares existam
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
# --- 4. CONTROLE DE DUPLICATAS (novo) ---
# =============================================================================
def gerar_hash(titulo, link):
    """Gera um hash único baseado no título e link da notícia."""
    conteudo = f"{titulo}{link}".encode("utf-8")
    return hashlib.md5(conteudo).hexdigest()

def carregar_historico(sheet_historico):
    """Carrega todos os hashes de notícias já enviadas."""
    try:
        registros = sheet_historico.get_all_records()
        return {r["hash"] for r in registros}
    except Exception as e:
        print(f"⚠️ Não foi possível carregar histórico: {e}")
        return set()

def salvar_no_historico(sheet_historico, noticias_novas):
    """Salva os hashes das novas notícias processadas nesta execução."""
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        [gerar_hash(n["titulo"], n["link"]), n["titulo"][:80], hoje]
        for n in noticias_novas
    ]
    if linhas:
        sheet_historico.append_rows(linhas)

# =============================================================================
# --- 5. LOG DE ENVIOS (novo) ---
# =============================================================================
def registrar_log(sheet_logs, nome, email, status, temas_enviados):
    """Registra o resultado de cada envio na aba de logs."""
    try:
        sheet_logs.append_row([
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            nome,
            email,
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

    # BTC: tenta BRL primeiro, cai para USD (converte na hora) se falhar
    def buscar_btc():
        for ticker_id, moeda in [("BTC-BRL", "BRL"), ("BTC-USD", "USD")]:
            try:
                hist = yf.Ticker(ticker_id).history(period="5d")
                if len(hist) >= 2:
                    atual = hist['Close'].iloc[-1]
                    ant   = hist['Close'].iloc[-2]
                    var   = ((atual - ant) / ant) * 100
                    if moeda == "BRL":
                        label = f"R$ {atual/1000:.1f}k"
                    else:
                        label = f"US$ {atual/1000:.1f}k"
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

    # BTC entra entre USD e IBOV
    btc_html = buscar_btc()
    if btc_html:
        html_items.insert(1, btc_html)  # posição 1 = entre USD e IBOV

    if not html_items:
        return ""

    return (
        f"<div style='background-color:#e5e3de; padding:12px; text-align:center; "
        f"font-family:monospace; font-size:13px; color:#111;'>"
        f"{' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(html_items)}</div>"
    )

# =============================================================================
# --- 7. EXTRATOR DE IMAGEM ---
# =============================================================================

# Fallbacks específicos por esporte (usados quando o feed não tem imagem)
FALLBACK_ESPORTES_KEYWORD = {
    "f1":           "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "formula":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "grand prix":   "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "gp de":        "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "verstappen":   "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "hamilton":     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "ferrari":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "leclerc":      "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
    "nba":          "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
    "basquete":     "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
    "lebron":       "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
    "curry":        "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
    "nfl":          "https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=600&h=300&fit=crop",
    "super bowl":   "https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=600&h=300&fit=crop",
    "tênis":        "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "tennis":       "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "fonseca":      "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "alcaraz":      "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "sinner":       "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "miami open":   "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
    "motogp":       "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
    "moto gp":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
    "márquez":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
    "moreira":      "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=600&h=300&fit=crop",
}

FALLBACK_ESPORTES_GENERIC = [
    "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1540747913346-19212a4b32b8?w=600&h=300&fit=crop",
    "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&h=300&fit=crop",
]

def extrair_imagem_rss(entry, tema, idx_entry=0):
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    image_url = None

    # 1. media_content
    if 'media_content' in entry:
        for m in entry.media_content:
            if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                image_url = m['url']
                break

    # 2. enclosures (comum em feeds de podcast/news)
    if not image_url and 'enclosures' in entry:
        for enc in entry.enclosures:
            url_enc = enc.get('url', '')
            if any(ext in url_enc.lower() for ext in extensoes):
                image_url = url_enc
                break

    # 3. links com type image
    if not image_url and 'links' in entry:
        for l in entry.links:
            href = l.get('href', '')
            if l.get('type', '').startswith('image/') and any(ext in href.lower() for ext in extensoes):
                image_url = href
                break

    # 4. scraping de <img> no summary/content
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

    # 5. Fallback com rotação por esporte para evitar imagens repetidas
    if not image_url:
        if tema == "Esportes":
            titulo = entry.get('title', '').lower()
            # Rotação dentro da mesma categoria esportiva
            SPORT_ROTATIONS = {
                "nba":      ["https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
                             "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=600&h=300&fit=crop"],
                "f1":       ["https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
                             "https://images.unsplash.com/photo-1541447271487-09612b3f49f7?w=600&h=300&fit=crop"],
                "mma":      ["https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=300&fit=crop",
                             "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&h=300&fit=crop"],
                "tênis":    ["https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
                             "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=600&h=300&fit=crop"],
            }
            # Detecta categoria
            categoria = None
            for kw, cat in [("nba","nba"),("basquete","nba"),("lebron","nba"),("durant","nba"),("curry","nba"),
                            ("f1","f1"),("formula","f1"),("grand prix","f1"),("gp de","f1"),("verstappen","f1"),("hamilton","f1"),("ferrari","f1"),("leclerc","f1"),
                            ("mma","mma"),("ufc","mma"),("silva","mma"),("evloev","mma"),("volkanovski","mma"),
                            ("tênis","tênis"),("fonseca","tênis"),("alcaraz","tênis"),("sinner","tênis"),("open","tênis")]:
                if kw in titulo:
                    categoria = cat
                    break
            if categoria and categoria in SPORT_ROTATIONS:
                # Usa keyword para escolher imagem — alterna entre as duas do par pela primeira letra do título
                idx = ord(titulo[0]) % len(SPORT_ROTATIONS[categoria])
                image_url = SPORT_ROTATIONS[categoria][idx]
            else:
                # Sem categoria específica: usa fallback genérico rotativo
                image_url = FALLBACK_ESPORTES_GENERIC[idx_entry % len(FALLBACK_ESPORTES_GENERIC)]
        else:
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
            }
            image_url = FALLBACK_IMAGES.get(
                tema,
                "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
            )

    return image_url

# =============================================================================
# --- 8. IA (GEMINI) ---
# =============================================================================
def chamar_gemini_api(prompt):
    if not GEMINI_KEY:
        return None
    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}"
        for tentativa in range(1, 4):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    return r.json()['candidates'][0]['content']['parts'][0]['text']
                elif r.status_code == 429:
                    print(f"      ⏳ Rate limit Gemini. Aguardando {20 * tentativa}s...")
                    time.sleep(20 * tentativa)
                else:
                    print(f"      ⚠️ Gemini retornou status {r.status_code}. Tentando próximo modelo...")
                    break
            except Exception as e:
                print(f"      ⚠️ Exceção ao chamar Gemini: {e}")
                break
    return None

def limpar_texto_rss(texto):
    """
    Remove lixo comum de feeds RSS:
    - Tags HTML
    - Rodapés 'The post X appeared first on Y.' (qualquer posição, com ou sem \n)
    - Créditos de foto (Reuters/X, AFP, AP etc.) em qualquer posição
    - Entidades HTML
    - Espaços/quebras duplicados
    """
    # Remove tags HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    # Decodifica entidades HTML ANTES de aplicar outros filtros
    texto = texto.replace('&#8220;', '"').replace('&#8221;', '"')
    texto = texto.replace('&#8216;', "'").replace('&#8217;', "'")
    texto = texto.replace('&amp;', '&').replace('&quot;', '"')
    texto = texto.replace('&nbsp;', ' ')
    # Remove rodapé InfoMoney/WordPress em qualquer posição (com \n ou sem)
    texto = re.sub(r'\s*The post .+?appeared first on .+?\.?\s*', ' ', texto, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r'\s*appeared first on .+', '', texto, flags=re.IGNORECASE)
    # Remove créditos de foto em qualquer posição: "Reuters/Nome", "AFP/Nome", "AP Photo/Nome"
    texto = re.sub(r'\b(Reuters|AFP|AP|EFE|G1|Globo|GE|Getty)[\s/][^\.\n]{0,60}', ' ', texto, flags=re.IGNORECASE)
    # Remove frases só de legenda de foto (começa com agência de notícia)
    texto = re.sub(r'(Reuters|AFP|AP|EFE)/\S+', '', texto, flags=re.IGNORECASE)
    # Remove espaços/quebras duplicados
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def resumo_fallback(entry):
    """
    Fallback quando a IA não retorna resumo.
    Tenta em ordem: summary → content → nada.
    Limpa lixo, limita a 60 palavras.
    Nunca retorna texto menor que 15 palavras (sinal de lixo restante).
    """
    texto = ""
    if 'summary' in entry:
        texto = entry.summary
    elif 'content' in entry and entry.content:
        texto = entry.content[0].value

    texto = limpar_texto_rss(texto)
    palavras = texto.split()

    # Se sobrou menos de 15 palavras úteis, provavelmente é lixo
    if len(palavras) < 15:
        return ""  # sinaliza para o chamador que não tem texto

    if len(palavras) > 60:
        texto = " ".join(palavras[:60]) + "..."

    return texto

# =============================================================================
# --- 9. PROCESSAMENTO DE TEMA ---
# =============================================================================
def aplicar_filtros(entry, tema):
    """Filtro por tema. Verifica título e link contra lista de palavras proibidas."""
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
    """Retorna True se a notícia for predominantemente sobre futebol."""
    texto = (entry.get('title', '') + ' ' + entry.get('link', '')).lower()
    return any(p in texto for p in PALAVRAS_FUTEBOL)

def e_esporte_prioritario(entry):
    """Retorna True se for F1, NBA ou NFL."""
    texto = (entry.get('title', '') + ' ' + entry.get('link', '')).lower()
    return any(p in texto for p in PALAVRAS_ESPORTES_PRIORITY)

def coletar_entries_esportes():
    """
    Coleta de múltiplas fontes com ordem de prioridade:
    1. F1, NBA, NFL (esportes prioritários) — até 3 notícias
    2. Outros esportes não-futebol — completa até 4
    3. Futebol — máx 1 para fechar o slot se necessário
    """
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
    """Detecta quasi-duplicatas: se >50% das palavras significativas coincidem."""
    p1 = set(re.findall(r'\w{4,}', t1.lower()))
    p2 = set(re.findall(r'\w{4,}', t2.lower()))
    if not p1 or not p2:
        return False
    return len(p1 & p2) / min(len(p1), len(p2)) >= 0.50

def processar_tema(tema, historico_hashes):
    """
    Coleta, filtra e resume notícias do tema.
    - Uma única chamada Gemini por tema
    - Filtro semântico de Mercado embutido no prompt (SKIP para off-topic)
    - Esportes: prioriza F1/NBA/NFL, máx 1 futebol em 4
    - Fallback robusto para feeds sem summary
    """
    print(f"      ...Processando {tema}...")

    # --- Coleta ---
    # Esportes: coleta de todas as fontes para ter pool diverso
    # Cinema/Fitness: também tenta todas as fontes pois feeds individuais são pequenos
    TEMAS_MULTI_FONTE = {"Esportes", "Cinema", "Fitness"}

    if tema in TEMAS_MULTI_FONTE:
        if tema == "Esportes":
            valid_entries = coletar_entries_esportes()
        else:
            # Coleta de todas as fontes, sem parar na primeira
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
            print(f"      📡 {tema}: {len(valid_entries)} entradas coletadas de todas as fontes.")
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

    # --- Filtros de conteúdo + hash ---
    candidatas = []
    for entry in valid_entries:
        if not aplicar_filtros(entry, tema):
            continue
        h = gerar_hash(entry.get('title', ''), entry.get('link', ''))
        if h in historico_hashes:
            print(f"      ↩️ Duplicata ignorada: {entry.get('title', '')[:50]}...")
            continue
        candidatas.append(entry)
        # Pool maior para temas que precisam de diversidade
        limite = 40 if tema in ("Esportes", "Motos", "Cinema", "Fitness") else 20
        if len(candidatas) >= limite:
            break

    if not candidatas:
        print(f"⚠️ '{tema}' sem notícias após filtros básicos.")
        return None

    # --- Diversidade Esportes: prioriza F1/NBA/NFL, máx 1 futebol em 4 ---
    if tema == "Esportes":
        prioritarios, outros, futebol_pool = [], [], []
        for entry in candidatas:
            if e_esporte_prioritario(entry):
                prioritarios.append(entry)
            elif e_futebol(entry):
                futebol_pool.append(entry)
            else:
                outros.append(entry)

        # Ordem: F1/NBA/NFL → outros esportes → futebol (último recurso)
        selecionadas = prioritarios + outros
        # Completa com futebol se ainda faltar
        for f in futebol_pool:
            if len(selecionadas) >= 4:
                break
            selecionadas.append(f)
        candidatas = selecionadas[:4]
        qtd_f1_nba = sum(1 for e in candidatas if e_esporte_prioritario(e))
        qtd_fut    = sum(1 for e in candidatas if e_futebol(e))
        print(f"      🏎️ Esportes: {qtd_f1_nba} F1/NBA/NFL | {qtd_fut} futebol | {len(candidatas)-qtd_f1_nba-qtd_fut} outros.")

    # --- Deduplicação por similaridade de título ---
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

    # --- Monta input para Gemini ---
    input_txt = ""
    for i, e in enumerate(noticias_filtradas):
        input_txt += f"Notícia {i+1}: {e.get('title', '')}\n\n"

    # Instrução extra para Mercado
    instrucao_mercado = ""
    if tema == "Mercado":
        instrucao_mercado = """
REGRA EXTRA para o caderno Mercado:
- Se uma manchete NÃO for sobre economia, finanças, mercado financeiro ou negócios
  (ex: esporte, entretenimento, clima, festivais), escreva exatamente a palavra SKIP.
- Notícias genuínas de economia recebem o resumo normal.
"""

    # Instruções específicas por tema para aumentar profundidade
    instrucao_tema = {
        "Mundo":    "Inclua o contexto geopolítico, os países e atores envolvidos, e as possíveis consequências do evento.",
        "Mercado":  "Inclua números concretos (percentuais, valores, índices), o impacto para o investidor ou cidadão, e o contexto econômico.",
        "Politica": "Inclua o contexto institucional, as partes envolvidas, e os possíveis desdobramentos políticos ou jurídicos.",
        "Tech":     "Inclua detalhes técnicos relevantes, o impacto no mercado ou no usuário final, e o contexto da inovação ou empresa.",
        "Esportes": "Inclua resultados, classificações, desempenho de atletas e o que está em jogo na competição.",
        "Cinema":   "Inclua avaliações (Rotten Tomatoes, IMDb quando disponível), o gênero, o elenco principal e por que vale assistir.",
        "Fitness":  "Inclua dados científicos, recomendações práticas com números (tempo, repetições, nutrientes) e benefícios comprovados.",
        "Ciencia":  "Inclua a metodologia da pesquisa, os números e descobertas concretas, e o que isso muda no entendimento científico.",
        "Motos":    "Inclua especificações técnicas relevantes (motor, potência, preço), diferenciais do modelo e contexto do mercado.",
        "Fofoca":   "Inclua o contexto da história, as pessoas envolvidas e os detalhes que tornam o assunto interessante.",
    }.get(tema, "Inclua dados, números e contexto que dão profundidade ao assunto.")

    prompt = f"""Você é um jornalista sênior de um jornal digital premium brasileiro.
Escreva resumos informativos e densos para as manchetes do caderno de {tema}.

MISSÃO: Cada resumo deve ler como um parágrafo de um artigo real — com dados, contexto e substância.
NÃO escreva manchetes longas. Escreva jornalismo de verdade.

REGRAS OBRIGATÓRIAS:
1. PROFUNDIDADE: {instrucao_tema}
2. TAMANHO: Entre 70 e 90 palavras por resumo. Resumos curtos (abaixo de 60 palavras) são INACEITÁVEIS.
3. Tom direto e natural — como se estivesse explicando para um leitor inteligente e curioso.
4. PROIBIDO: "o artigo fala", "a notícia informa", "o texto explora", "a matéria aborda",
   "o post detalha", "o que se espera", "a notícia detalha", "a notícia destaca",
   "vale destacar", "é importante notar", "segundo a publicação".
5. PROIBIDO numerar os resumos ("Notícia 1:", "1.", etc.).
6. PROIBIDO markdown (asteriscos, negrito, títulos, bullet points).
7. Comece sempre pelo fato principal com dados concretos quando disponíveis.
8. Voz ativa. Sem jargão desnecessário.
{instrucao_mercado}
Separe cada resumo com "|||". Nada mais além dos resumos.

Manchetes:
{input_txt}"""

    resp_ia = chamar_gemini_api(prompt)

    def limpar_resumo(texto):
        # Remove markdown residual
        texto = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', texto)
        texto = re.sub(r'^[\*\s]*Not[íi]cia\s*\d+[\:\.\s\*]*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^\d+[\.\)]\s*', '', texto)
        # Remove lixo RSS que possa ter escapado
        texto = limpar_texto_rss(texto)
        return texto.strip()

    resumos_ia = []
    if resp_ia:
        resumos_ia = [r.strip() for r in resp_ia.split('|||') if r.strip()]
        # Garante que temos resumos suficientes (Gemini às vezes retorna menos)
        while len(resumos_ia) < len(noticias_filtradas):
            resumos_ia.append("")
    else:
        print(f"      ⚠️ IA indisponível para '{tema}'. Usando fallback RSS.")

    # --- Monta notícias finais ---
    noticias_finais = []
    for i, entry in enumerate(noticias_filtradas):
        resumo_bruto = resumos_ia[i] if resp_ia and i < len(resumos_ia) else ""
        resumo_limpo = limpar_resumo(resumo_bruto)

        # Se Gemini retornou SKIP (filtro semântico de Mercado) → pula
        if resumo_limpo.strip().upper() == "SKIP":
            print(f"      🚫 Mercado SKIP: {entry.get('title','')[:50]}")
            continue

        # Se resumo da IA ficou vazio → usa fallback do RSS
        if not resumo_limpo:
            resumo_fallback_txt = resumo_fallback(entry)
            # Se fallback também ficou vazio → gera aviso genérico com o título
            if not resumo_fallback_txt:
                titulo = entry.get('title', '')
                resumo_limpo = f"Confira o que está acontecendo: {titulo}."
            else:
                resumo_limpo = resumo_fallback_txt

        img = extrair_imagem_rss(entry, tema, idx_entry=i)
        noticias_finais.append({
            "titulo": entry.get('title', ''),
            "link":   entry.get('link', ''),
            "imagem": img,
            "resumo": resumo_limpo,
        })

    return noticias_finais if noticias_finais else None

# =============================================================================
# --- 10. TEMPLATE DO E-MAIL ---
# =============================================================================
def gerar_html_final(nome, dados, painel):
    cor_turquesa    = "0a5c5a"
    cor_creme       = "fdfbf7"
    cor_fundo_escuro = "084c4a"

    html = f"""
    <html><body style="margin:0; padding:0; background-color:#e5e3de; font-family:'Lora', 'Times New Roman', serif;">
        <div style="max-width:600px; margin:20px auto; background-color:#{cor_creme}; border-radius:8px; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">

            <div style="background-color:transparent; color:#{cor_turquesa}; padding:30px 20px 20px; text-align:center; border-bottom:2px solid #{cor_turquesa};">
                <h1 style="margin:0; font-family:'Playfair Display', Georgia, serif; font-size:32px; text-transform:uppercase; letter-spacing: 2px;">ALL NEWS JOURNAL</h1>
                <p style="margin:10px 0 0; font-size:12px; color:#777; font-style:italic;">Edição Premium • {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>

            {painel}

            <div style="padding:30px 25px;">
                <p style="color:#2c2c2c; font-size:16px; text-align:center; margin-bottom:40px; font-style:italic;">Bom dia, <b>{nome}</b>. Aqui está a sua curadoria de hoje.</p>
    """

    for tema, items in dados.items():
        if not items:
            continue

        html += f"""
        <div style="margin:40px 0 25px; border-bottom:2px solid #{cor_turquesa};">
            <span style="background-color:#{cor_turquesa}; color:#ffffff; padding:6px 14px; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; border-radius:4px 4px 0 0; display:inline-block;">{tema}</span>
        </div>"""

        for n in items:
            html += f"""
            <div style="margin-bottom:35px; border-bottom:1px solid #e5e3de; padding-bottom:25px;">
                <a href="{n['link']}">
                    <img src="{n['imagem']}" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border-bottom:4px solid #{cor_turquesa}; display:block;">
                </a>
                <div style="padding-top:15px;">
                    <a href="{n['link']}" style="text-decoration:none; color:#111111;">
                        <h3 style="margin:0 0 12px; font-size:22px; font-family:'Playfair Display', Georgia, serif; line-height:1.3;">{n['titulo']}</h3>
                    </a>
                    <p style="margin:0; font-size:15px; color:#444444; line-height:1.6;">{n['resumo']}</p>
                    <div style="margin-top:15px;">
                        <a href="{n['link']}" style="font-size:13px; color:#{cor_turquesa}; font-weight:bold; text-decoration:none; text-transform:uppercase; letter-spacing:0.5px;">Ler matéria completa &rarr;</a>
                    </div>
                </div>
            </div>"""

    html += f"""
            </div>
            <div style="text-align:center; padding:30px; background-color:#{cor_fundo_escuro}; color:#{cor_creme}; font-size:12px; font-family:'Lora', 'Times New Roman', serif;">
                <p style="margin:0;">&copy; 2026 All News Journal Group. Conteúdo Premium.</p>
                <p style="margin:10px 0 0; font-size:10px; opacity:0.7;">Você está recebendo este e-mail porque se inscreveu no nosso portal.</p>
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
        msg['Subject'] = f"📰 All News Journal - {datetime.now().strftime('%d/%m')}"
        msg['From']    = EMAIL_SENDER
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
    print("🚀 Iniciando Motor (v10.0 - Ordem Personalizada + Filtros Reforçados)...")

    # 1. Valida o ambiente antes de qualquer coisa
    if not validar_ambiente():
        return

    # 2. Conecta ao banco (agora retorna 3 abas)
    sheet_usuarios, sheet_historico, sheet_logs = conectar_banco()
    if not sheet_usuarios:
        return

    # 3. Carrega histórico de notícias já enviadas
    historico_hashes = carregar_historico(sheet_historico)
    print(f"   🗂️ {len(historico_hashes)} notícias no histórico (anti-duplicata).")

    # 4. Lê usuários
    usuarios = sheet_usuarios.get_all_records()
    print(f"   📋 {len(usuarios)} usuários encontrados.")

    # 5. Descobre quais temas são necessários (considera valores "Sim" e numéricos de ordem)
    temas_demandados = set()
    for usr in usuarios:
        for tema in RSS_FEEDS.keys():
            val = str(usr.get(tema, '')).strip().lower()
            if val == "sim" or val.isdigit():
                temas_demandados.add(tema)

    # 6. Processa e armazena em cache global
    CACHE_GLOBAL = {}
    todas_noticias_novas = []
    painel = obter_indicadores()

    for tema in temas_demandados:
        conteudo = processar_tema(tema, historico_hashes)
        if conteudo:
            CACHE_GLOBAL[tema] = conteudo
            todas_noticias_novas.extend(conteudo)
            print(f"      ✅ {tema}: {len(conteudo)} notícias prontas.")
            print("      💤 Pausa tática (10s)...")
            time.sleep(10)

    # 7. Salva novas notícias no histórico (anti-duplicata para próximas execuções)
    if todas_noticias_novas:
        salvar_no_historico(sheet_historico, todas_noticias_novas)
        print(f"   💾 {len(todas_noticias_novas)} notícias salvas no histórico.")

    # 8. Distribui para cada usuário e registra log
    print("🚚 Iniciando distribuição...")
    enviados, falhas = 0, 0

    for usr in usuarios:
        nome  = usr.get('Nome')
        email = usr.get('Email')
        if not nome or not email:
            continue

        # Monta o pacote respeitando a ordem personalizada do leitor
        # O valor na coluna pode ser um número (1, 2, 3...) indicando prioridade,
        # ou "Sim" (sem ordenação), ou "Não" (não recebe).
        temas_com_ordem = []
        for tema in RSS_FEEDS.keys():
            val = str(usr.get(tema, '')).strip()
            if val.lower() == "não" or val == "":
                continue
            if tema not in CACHE_GLOBAL:
                continue
            # Se for número, usa como chave de ordenação; "Sim" vai ao final
            ordem = int(val) if val.isdigit() else 999
            temas_com_ordem.append((ordem, tema))

        # Ordena pelos números definidos pelo leitor; empates mantêm ordem padrão do RSS_FEEDS
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
