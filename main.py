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
    # Ordem padrão do sistema (usada como fallback quando o leitor não definiu ordem própria)
    "Mundo":    ["https://g1.globo.com/rss/g1/mundo/"],
    "Mercado":  ["https://www.infomoney.com.br/feed/", "https://rss.uol.com.br/feed/economia.xml"],
    "Politica": ["https://g1.globo.com/rss/g1/politica/"],
    "Tech":     ["https://rss.tecmundo.com.br/feed"],
    "Esportes": [
        # Múltiplas fontes para cobertura ampla além do futebol
        "https://ge.globo.com/rss/ge/",                          # GE Globo geral
        "https://sportv.globo.com/rss/sportv/",                  # SporTV (F1, tênis, NBA etc)
        "https://www.uol.com.br/esporte/rss.xml",                # UOL Esporte
        "https://www.espn.com.br/rss/",                          # ESPN Brasil
    ],
    "Ciencia":  ["https://gizmodo.uol.com.br/category/ciencia/feed/"],
    "Motos":    ["https://www.motociclismoonline.com.br/feed/"],
    "Fofoca":   ["https://revistaquem.globo.com/rss/quem/"],
}

# Filtros de palavras indesejadas por tema
# Verificados no título E no link da notícia (case-insensitive)
FILTROS_TEMA = {
    "Mundo":    [],
    "Mercado":  ["horóscopo", "moda", "futebol", "brasileirão", "campeonato",
                 "onde assistir", "onde-assistir", "jogo", "gol", "escalação",
                 "partida", "clube", "torcedor", "lollapalooza", "festival",
                 "show", "ingresso", "previsão do tempo", "clima", "chuva",
                 "tênis", "fonseca", "alcaraz", "sinner", "nadal"],
    "Politica": [],
    "Tech":     ["aposta", "palpite", "futebol", "bônus", "cassino", "bet",
                 "guia-de-compras", "em-oferta", "promoção", "desconto"],
    "Esportes": [
        # Páginas de placar/logística
        "ao-vivo", "ao vivo", "/jogo/", "onde-assistir", "ingressos",
        "escalação", "prováveis-times",
        # Futebol regional/amador (para limitar e dar espaço a outros esportes)
        "/base/", "sub-13", "sub-15", "sub-17", "sub-20",
        "campeonato-piauiense", "campeonato-alagoano", "campeonato-paraibano",
        "campeonato-potiguar", "campeonato-cearense", "campeonato-maranhense",
        "segunda-divisao", "terceira-divisao", "serie-d", "serie-c",
        "copa-do-brasil-sub", "paulista-sub", "carioca-sub",
    ],
    "Ciencia":  [],
    "Motos":    [],
    "Fofoca":   [],
}

# Palavras-chave de futebol para controle de proporção no caderno Esportes
PALAVRAS_FUTEBOL = [
    "futebol", "brasileirão", "série a", "serie-a", "libertadores",
    "copa do brasil", "palmeiras", "flamengo", "corinthians", "são paulo",
    "santos", "grêmio", "internacional", "atlético", "cruzeiro", "vasco",
    "botafogo", "fluminense", "fortaleza", "bahia", "gol", "técnico",
    "treinador", "zagueiro", "atacante", "meia", "goleiro", "volante"
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
def extrair_imagem_rss(entry, tema):
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    image_url = None

    if 'media_content' in entry:
        for m in entry.media_content:
            if 'url' in m and any(ext in m['url'].lower() for ext in extensoes):
                image_url = m['url']
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
    Remove lixo comum de feeds RSS antes de processar:
    - Tags HTML
    - Rodapés do tipo 'The post X appeared first on Y.'
    - Créditos de imagem (Reuters, AFP, etc.) no início
    - Entidades HTML (&amp; &#8220; etc.)
    - Espaços duplicados
    """
    # Remove tags HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    # Remove rodapé do InfoMoney e similares
    texto = re.sub(r'The post .+? appeared first on .+?\.', '', texto, flags=re.DOTALL)
    texto = re.sub(r'appeared first on .+', '', texto)
    # Remove créditos de foto no início (ex: "Reuters/John Doe " ou "AFP ")
    texto = re.sub(r'^(Reuters|AFP|AP|EFE|G1|Globo|GE)[^\n]{0,60}\n', '', texto)
    # Decodifica entidades HTML comuns
    texto = texto.replace('&#8220;', '"').replace('&#8221;', '"')
    texto = texto.replace('&#8216;', "'").replace('&#8217;', "'")
    texto = texto.replace('&amp;', '&').replace('&quot;', '"')
    texto = texto.replace('&nbsp;', ' ')
    # Remove espaços/quebras duplicados
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def resumo_fallback(entry):
    """
    Fallback: extrai resumo direto do RSS quando a IA não está disponível.
    Limpa lixo, limita a 60 palavras.
    """
    texto = ""
    if 'summary' in entry:
        texto = entry.summary
    elif 'content' in entry and entry.content:
        texto = entry.content[0].value

    texto = limpar_texto_rss(texto)

    palavras = texto.split()
    if len(palavras) > 60:
        texto = " ".join(palavras[:60]) + "..."

    return texto if texto else "Acesse o link abaixo para ler a matéria completa."

# =============================================================================
# --- 9. PROCESSAMENTO DE TEMA ---
# =============================================================================
def aplicar_filtros(entry, tema):
    """Filtro genérico por tema. Verifica título e link contra lista de palavras proibidas."""
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

def titulos_similares(t1, t2):
    """
    Detecta notícias quase-duplicadas comparando palavras em comum.
    Se >60% das palavras do título menor estiverem no maior, considera similar.
    """
    p1 = set(re.findall(r'\w{4,}', t1.lower()))
    p2 = set(re.findall(r'\w{4,}', t2.lower()))
    if not p1 or not p2:
        return False
    intersecao = p1 & p2
    menor = min(len(p1), len(p2))
    return len(intersecao) / menor >= 0.60

def filtro_semantico_mercado(titulos_candidatos):
    """
    (NOVO) Usa Gemini para classificar quais títulos são genuinamente
    de economia/mercado financeiro. Descarta os que não forem.
    Retorna lista de índices aprovados (0-based).
    """
    if not titulos_candidatos or not GEMINI_KEY:
        return list(range(len(titulos_candidatos)))

    lista_txt = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titulos_candidatos))
    prompt = f"""Você é um editor de economia. Avalie cada manchete abaixo e diga se é genuinamente sobre economia, finanças, mercado financeiro, negócios ou política econômica.

Responda APENAS com os números das manchetes aprovadas, separados por vírgula. Sem explicações.
Exemplo de resposta: 1, 3, 4

Manchetes:
{lista_txt}"""

    resp = chamar_gemini_api(prompt)
    if not resp:
        return list(range(len(titulos_candidatos)))

    try:
        aprovados = [int(x.strip()) - 1 for x in resp.split(',') if x.strip().isdigit()]
        return [i for i in aprovados if 0 <= i < len(titulos_candidatos)]
    except Exception:
        return list(range(len(titulos_candidatos)))

def coletar_entries_esportes():
    """
    (NOVO) Coleta de múltiplas fontes e garante diversidade:
    máximo 2 notícias de futebol nas 4 selecionadas.
    """
    todas_entries = []
    vistos_urls = set()

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

def processar_tema(tema, historico_hashes):
    """
    Coleta, filtra e resume notícias do tema.
    Inclui: limpeza de lixo RSS, filtro semântico (Mercado),
    controle de diversidade (Esportes), deduplicação por similaridade.
    """
    print(f"      ...Processando {tema}...")

    # --- Coleta ---
    if tema == "Esportes":
        valid_entries = coletar_entries_esportes()
    else:
        urls = RSS_FEEDS.get(tema, [])
        valid_entries = []
        for url in urls:
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

    # --- Filtros de conteúdo + duplicata por hash ---
    candidatas = []
    for entry in valid_entries:
        if not aplicar_filtros(entry, tema):
            continue
        h = gerar_hash(entry.get('title', ''), entry.get('link', ''))
        if h in historico_hashes:
            print(f"      ↩️ Duplicata ignorada: {entry.get('title', '')[:50]}...")
            continue
        candidatas.append(entry)
        if len(candidatas) >= 20:  # pool generoso para filtros posteriores
            break

    if not candidatas:
        print(f"⚠️ '{tema}' sem notícias novas após filtros básicos.")
        return None

    # --- Filtro semântico para Mercado ---
    if tema == "Mercado":
        titulos_pool = [e.get('title', '') for e in candidatas[:10]]
        indices_ok = filtro_semantico_mercado(titulos_pool)
        candidatas = [candidatas[i] for i in indices_ok if i < len(candidatas)]
        print(f"      🔍 Filtro semântico Mercado: {len(indices_ok)}/10 aprovadas.")

    # --- Controle de diversidade para Esportes (máx 2 futebol em 4) ---
    if tema == "Esportes":
        selecionadas, qtd_futebol = [], 0
        for entry in candidatas:
            if e_futebol(entry):
                if qtd_futebol < 2:
                    selecionadas.append(entry)
                    qtd_futebol += 1
            else:
                selecionadas.append(entry)
            if len(selecionadas) >= 4:
                break
        candidatas = selecionadas
        print(f"      ⚽ Esportes: {qtd_futebol} futebol + {len(candidatas)-qtd_futebol} outros.")

    # --- Deduplicação por similaridade de título (evita mesma notícia de 2 fontes) ---
    noticias_filtradas = []
    for entry in candidatas:
        titulo_novo = entry.get('title', '')
        similar = any(titulos_similares(titulo_novo, e.get('title', '')) for e in noticias_filtradas)
        if not similar:
            noticias_filtradas.append(entry)
        if len(noticias_filtradas) >= 4:
            break

    if not noticias_filtradas:
        print(f"⚠️ '{tema}' sem notícias após deduplicação.")
        return None

    # --- Prepara input para a IA (com limpeza de lixo RSS) ---
    input_txt = ""
    for i, e in enumerate(noticias_filtradas):
        titulo  = e.get('title', '')
        summary = limpar_texto_rss(e.get('summary', '') or '')
        summary_trunc = ' '.join(summary.split()[:80])  # limita contexto
        input_txt += f"Notícia {i+1}: {titulo}\nContexto: {summary_trunc}\nLink: {e.get('link','')}\n\n"

    prompt = f"""
    Você é um jornalista experiente escrevendo para um jornal digital premium brasileiro.
    Analise estas {len(noticias_filtradas)} manchetes do caderno de {tema}.

    Para CADA manchete, escreva um parágrafo de resumo com as seguintes regras OBRIGATÓRIAS:

    REGRAS DE ESTILO (siga à risca):
    1. Tom direto e natural — escreva como se estivesse contando a notícia para um amigo culto, de forma objetiva.
    2. PROIBIDO usar qualquer dessas expressões: "o artigo fala", "a notícia informa", "o texto explora",
       "a matéria aborda", "o post detalha", "o que se espera", "a notícia detalha", "a notícia destaca".
    3. PROIBIDO numerar os resumos. Não escreva "Notícia 1:", "**Notícia 2:**", "1.", "2." ou qualquer variação.
    4. PROIBIDO usar markdown — sem asteriscos, sem negrito, sem títulos, sem bullet points.
    5. Comece sempre pelo fato principal em si, depois adicione contexto (máximo 65 palavras por resumo).
    6. Use linguagem clara, sem jargão. Seja preciso e humano. Escreva sempre na voz ativa.

    Separe cada resumo com o marcador exato "|||" (três barras verticais). Nada mais além dos resumos.

    Manchetes:
    {input_txt}
    """

    resp_ia = chamar_gemini_api(prompt)

    def limpar_resumo(texto):
        texto = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', texto)
        texto = re.sub(r'^[\*\s]*Not[íi]cia\s*\d+[\:\.\s\*]*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^\d+[\.\)]\s*', '', texto)
        # Remove rodapé RSS que possa ter escapado
        texto = re.sub(r'The post .+? appeared first on .+?\.?$', '', texto, flags=re.DOTALL)
        return texto.strip()

    noticias_finais = []
    resumos = [r.strip() for r in resp_ia.split('|||') if r.strip()] if resp_ia else []
    if not resp_ia:
        print(f"      ⚠️ IA indisponível para '{tema}'. Usando fallback RSS.")

    for i, entry in enumerate(noticias_filtradas):
        resumo = limpar_resumo(resumos[i]) if resp_ia and i < len(resumos) else resumo_fallback(entry)
        img    = extrair_imagem_rss(entry, tema)
        noticias_finais.append({
            "titulo": entry.get('title', ''),
            "link":   entry.get('link', ''),
            "imagem": img,
            "resumo": resumo,
        })

    return noticias_finais

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
