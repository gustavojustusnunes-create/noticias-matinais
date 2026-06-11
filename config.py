"""
config.py — Constantes e configurações do All News Journal v15.2
Centraliza feeds RSS, filtros, instruções de tema, imagens e cores.

Cadernos ativos (v15.2): Mundo, Economia, Politica, IA, Wellness, Ciencia, Cinema, Fofoca
Removidos: Tech, Esportes, Motos
Renomeados: Mercado → Economia | Fitness → Wellness
"""
import os

# =============================================================================
# --- VARIÁVEIS DE AMBIENTE ---
# =============================================================================
CLAUDE_KEY       = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_KEY", "")).strip()
GCP_JSON         = os.environ.get("GCP_JSON")
EMAIL_SENDER     = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD   = os.environ.get("EMAIL_PASS") or os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM       = os.environ.get("EMAIL_FROM", EMAIL_SENDER)
SMTP_HOST        = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.environ.get("SMTP_PORT", "587"))
URL_CANCELAMENTO = os.environ.get("URL_CANCELAMENTO", "https://allnewsjournal.streamlit.app/?acao=cancelar")
GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID") or os.environ.get("GOOGLE_SHEET_ID", "")
INSTAGRAM_USER   = os.environ.get("INSTAGRAM_USER", "")
INSTAGRAM_PASS   = os.environ.get("INSTAGRAM_PASS", "")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() == "true"

# ── Resend (provedor primário de email) ─────────────────────────
# Quando RESEND_API_KEY está definido, o envio passa pelo Resend
# (resend.com). Caso contrário, cai no SMTP do Gmail (legado).
# RESEND_FROM aceita o formato "Nome <email@dominio.com>".
# Fallback "onboarding@resend.dev" funciona sem domínio próprio
# verificado, mas só envia para o email do dono da conta Resend.
RESEND_API_KEY   = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM      = os.environ.get(
    "RESEND_FROM",
    "All News Journal <onboarding@resend.dev>",
).strip()

# ── URL pública da logo (header do email) ───────────────────────
# Hospedada no próprio repo via GitHub raw URL — gratuita,
# versionada e aceita por Gmail/Outlook/etc. Se um dia trocar a
# imagem, é só substituir o arquivo assets/anj-logo.png e dar push.
LOGO_URL = os.environ.get(
    "LOGO_URL",
    "https://raw.githubusercontent.com/gustavojustusnunes-create/noticias-matinais/main/assets/anj-logo.png",
).strip()

# Caminho LOCAL da logo — usado para EMBUTIR a imagem inline no email (cid).
# Como o repositório é privado, a LOGO_URL (raw.githubusercontent) dá 404 para
# o Gmail; embutir o arquivo resolve de vez, independente de hospedagem.
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "anj-logo.png")
# Content-ID usado no <img src="cid:..."> e no anexo inline do Resend.
LOGO_CID = "anjlogo"

# =============================================================================
# --- ORDEM EDITORIAL DOS CADERNOS ---
# =============================================================================
ORDEM_CADERNOS = ["Mundo", "Economia", "Politica", "IA", "Wellness", "Ciencia", "Cinema", "Fofoca"]

# =============================================================================
# --- FEEDS RSS ---
# =============================================================================
RSS_FEEDS = {
    "Mundo": [
        "https://g1.globo.com/rss/g1/mundo/",
        "https://www.bbc.com/portuguese/index.xml",
        "https://rss.uol.com.br/feed/noticias/internacional.xml",
        "https://www.dw.com/pt-br/rss/rss/rmundo/s-31600",
        "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
    ],
    "Economia": [
        "https://www.infomoney.com.br/feed/",
        "https://rss.uol.com.br/feed/economia.xml",
        "https://economia.uol.com.br/rss.xml",
        "https://valor.globo.com/rss/",
        "https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/",
        "https://exame.com/invest/feed/",
    ],
    "Politica": [
        "https://g1.globo.com/rss/g1/politica/",
        "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "https://rss.uol.com.br/feed/noticias/politica.xml",
        "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",
    ],
    "IA": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://feeds.feedburner.com/blogspot/gJZg",
        "https://openai.com/blog/rss.xml",
        "https://www.anthropic.com/news/rss.xml",
        "https://olhardigital.com.br/editorias/inteligencia-artificial/feed/",
        "https://canaltech.com.br/inteligencia-artificial/rss/",
    ],
    "Wellness": [
        "https://ge.globo.com/rss/eu-atleta/",
        "https://www.runnersworld.com.br/feed/",
        "https://sportv.globo.com/rss/sportv/categoria/bem-estar-e-fitness/",
        "https://boaforma.abril.com.br/feed/",
        "https://vivabem.uol.com.br/rss.xml",
        "https://www.runnersworld.com/rss/all.xml/",
        "https://www.bicycling.com/rss/all.xml/",
        "https://www.menshealth.com/rss/all.xml/",
        "https://www.womenshealthmag.com/rss/all.xml/",
        "https://www.outsideonline.com/rss/all/",
        "https://www.triathlete.com/feed/",
    ],
    "Ciencia": [
        "https://g1.globo.com/rss/g1/ciencia-e-saude/",
        "https://gizmodo.uol.com.br/feed/",
        "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
        "https://www.tecmundo.com.br/ciencia/rss",
        "https://www.nationalgeographicbrasil.com/ciencia/rss",
        "https://super.abril.com.br/feed/",
    ],
    "Cinema": [
        "https://www.omelete.com.br/rss/",
        "https://www.cinepop.com.br/feed",
        "https://www.papodecinema.com.br/feed/",
        "https://www.adorocinema.com/rss/",
        "https://variety.com/v/film/feed/",
        "https://deadline.com/category/film/feed/",
    ],
    "Fofoca": [
        "https://hugogloss.uol.com.br/feed/",
        "https://revistaquem.globo.com/rss/quem/",
        "https://people.com/feed/",
        "https://variety.com/feed/",
        "https://ew.com/feed/",
        "https://pagesix.com/feed/",
        "https://www.dailymail.co.uk/tvshowbiz/index.rss",
    ],
}

# Feeds cujo conteúdo está em inglês (requerem tradução automática)
FEEDS_INGLES = {
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://feeds.feedburner.com/blogspot/gJZg",
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/news/rss.xml",
    "https://www.runnersworld.com/rss/all.xml/",
    "https://www.menshealth.com/rss/all.xml/",
    "https://www.womenshealthmag.com/rss/all.xml/",
    "https://www.bicycling.com/rss/all.xml/",
    "https://www.outsideonline.com/rss/all/",
    "https://www.triathlete.com/feed/",
    "https://people.com/feed/",
    "https://variety.com/feed/",
    "https://variety.com/v/film/feed/",
    "https://deadline.com/category/film/feed/",
    "https://ew.com/feed/",
    "https://pagesix.com/feed/",
    "https://www.dailymail.co.uk/tvshowbiz/index.rss",
}

# =============================================================================
# --- FILTROS DE CONTEÚDO ---
# =============================================================================
FILTROS_TEMA = {
    "Mundo": [],

    "Economia": [
        "horóscopo", "moda", "futebol", "brasileirão", "campeonato",
        "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
        "gol", "escalação", "clube", "torcedor",
        "lollapalooza", "festival", "show", "ingresso",
        "previsão do tempo", "clima", "chuva",
        "bbb", "big brother", "prêmio do bbb", "reality",
        "tênis", "fonseca", "alcaraz", "sinner", "nadal",
        "israel:", "irã:", "civil morto", "guerra de fronteira",
        "bombardeio", "teerã", "netanyahu", "míssil",
        "lotofácil", "mega-sena", "mega sena", "quina", "lotomania",
        "timemania", "dupla sena", "resultado sorteado",
        "prêmio da loteria", "números sorteados",
        "lula", "bolsonaro", "lulismo", "bolsonarismo",
        "stf", "congresso", "senado", "câmara dos deputados",
        "eleições", "eleição municipal", "eleição presidencial", "eleitoral",
        "haddad", "palocci", "petista", "pt ", " pt,", " pt.", "psdb", "pl ", " pl,",
        "partido ", "partidos ", "voto ", "candidato", "deputado", "senador",
        "ministério da", "ministro da", "secretaria de", "governador",
        "prefeito", "vereador", "política interna", "reforma ministerial",
        "impeachment", "pec ", "proposta de emenda", "orçamento secreto",
        "orçamento federal", "ldo ", " ppa ", "reforma tributária",
        "cpi ", "comissão parlamentar",
        "governo federal", "governo lula", "governo bolsonaro",
        "presidente da república", "presidência da república",
        "arthur lira", "rodrigo pacheco", "ciro gomes",
        "flávio dino", "gilmar mendes", "alexandre de moraes",
        "tse afirma", "tse confirma", "tse decide", "tse determina",
        "stj decide", "stf decide", "supremo decide",
        "supremo julga", "moraes determina",
        "operação policial", "preso", "prisão", "mandado de busca",
        "inquérito", "investigação policial", "delegacia",
    ],

    "Politica": [],

    "IA": [
        "horóscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "morre", "falece", "aniversário",
        "bitcoin", "ethereum", "nft", "blockchain", "criptomoeda",
        "% off", "em oferta", "promoção", "desconto",
        "10 dicas", "5 truques", "guia completo de",
        "aposta", "bet", "cassino",
    ],

    "Wellness": [
        "aposta", "bet", "cassino", "moda",
        "maquiagem", "cabelo", "unhas", "beleza", "tatuagem",
        "câncer", "tumor", "cirurgia", "hospital", "médico recomenda",
        "remédio", "medicamento", "vacina", "dengue", "vírus",
        "doença", "diagnóstico", "sintomas", "tratamento clínico",
        "famoso", "celebridade", "ator", "atriz", "novela",
        "bbb", "big brother", "reality",
        "resfriado", "alergia", "gripe",
        "erros na cozinha", "receita de", "culinária",
        "velhice", "envelhecimento", "idoso", "terceira idade",
        "política", "conflito", "guerra", "eleição",
    ],

    "Ciencia": [
        "mão de obra", "mercado de trabalho", "emprego",
        "carreira", "concurso público", "salário",
    ],

    "Cinema": [
        "aposta", "bet", "cassino", "futebol", "esporte",
        "aniversário", "tatuagem", "look", "moda", "relacionamento",
        "casamento", "separação", "gravidez", "filhos",
        "morte de", "falecimento", "luto", "velório",
        "lamenta morte", "celebra aniversário", "faz anos",
    ],

    "Fofoca": [
        "ex-bbb", "ex bbb", "bbb ", "big brother",
        "fazenda ", "a fazenda", "reality show",
        "sertanejo", "pagodeiro", "funkeiro", "funk",
        "mc ", "mc.", "dj ",
        "governo federal", "presidente lula", "bolsonaro",
        "congresso nacional", "eleições", "partido político",
        "carlinhos maia", "virgínia", "virginia fonseca",
        "zé felipe", "ze felipe", "whindersson",
        "simaria", "simone mendes", "marília mendonça",
        "ana castela", "maiara", "maraisa",
        "robinho", "tremembé", "thiago brennand", "suzane richthofen",
        "mc guimê", "mc guime", "mc daniel", "mc kevin", "pocah",
        "jojo todynho", "jojo toddynho", "gkay", "gracyanne barbosa", "deolane",
        "biel ", "naldo benny",
        "leo santana", "safadão", "safadao",
        "gusttavo lima", "leonardo (cantor)", "leonardo cantor",
        "jade picon", "larissa manoela", "maísa",
        "juliette", "gil do vigor", "arthur aguiar",
        "davi brito", "matteus", "beatriz reis", "lucas souza",
        "denílson", "galvão bueno", "datena", "ratinho",
        "faustão", "silvio santos", "patrícia abravanel", "celso portiolli",
        "ícaro silva", "joão vicente de castro",
    ],
}

# =============================================================================
# --- INSTRUÇÕES POR TEMA (PROMPT IA) ---
# =============================================================================
INSTRUCAO_TEMA = {
    "Mundo": (
        "Inclua o contexto geopolítico completo: países envolvidos, atores principais, "
        "linha do tempo do evento e as possíveis consequências regionais e globais."
    ),
    "Economia": (
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
    "IA": (
        "Inclua: empresa/laboratório envolvido (OpenAI, Anthropic, Google DeepMind, "
        "Meta AI, xAI, Mistral, etc.), o nome exato do modelo ou produto quando "
        "mencionado, dados técnicos relevantes (parâmetros, benchmarks, contexto, "
        "modalidades) e o impacto prático para usuários ou para o mercado de IA. "
        "Se a notícia for sobre regulação ou ética, explique a tensão central em "
        "linguagem clara, sem jargão jurídico. Evite hype — escreva como repórter "
        "de tecnologia experiente, não como entusiasta."
    ),
    "Wellness": (
        "REGRA CRÍTICA DE IDIOMA: O texto base pode estar em inglês. "
        "Independentemente disso, o resumo final DEVE ser escrito EXCLUSIVAMENTE "
        "em Português Brasileiro fluente e natural — jamais use palavras em inglês "
        "no corpo do texto.\n"
        "FOCO: cultura de saúde, performance e longevidade. Cobre corrida, "
        "ciclismo, triatlo, musculação, mobilidade, nutrição esportiva, sono, "
        "recuperação e mindset atlético. Inclua dados práticos "
        "(séries, pace por km, zonas de FC, macros, VO2) sempre que o "
        "texto base os fornecer. Evite tom de consultório médico, evite linguagem "
        "de revista de dieta, evite sensacionalismo de saúde."
    ),
    "Ciencia": (
        "Inclua: instituição/pesquisadores envolvidos, metodologia resumida, "
        "principais números e descobertas e o que muda no entendimento científico "
        "ou na prática clínica com esse resultado."
    ),
    "Cinema": (
        "Inclua: gênero, elenco principal, diretor, sinopse objetiva (sem spoilers), "
        "avaliações de crítica (Rotten Tomatoes, IMDb) quando disponíveis, streaming "
        "ou estreia nos cinemas, e por que o filme ou série vale atenção do leitor."
    ),
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

# =============================================================================
# --- IMAGENS DE FALLBACK ---
# =============================================================================
FALLBACK_IMAGES = {
    "Mundo":    "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=300&fit=crop",
    "Economia": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
    "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
    "IA":       "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&h=300&fit=crop",
    "Wellness": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "Ciencia":  "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=300&fit=crop",
    "Cinema":   "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600&h=300&fit=crop",
    "Fofoca":   "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=300&fit=crop",
}

# =============================================================================
# --- IDENTIDADE VISUAL ---
# =============================================================================
ICONES_TEMA = {
    "Mundo":    "🌎",
    "Economia": "📈",
    "Politica": "🏛️",
    "IA":       "🤖",
    "Wellness": "🏃",
    "Ciencia":  "🔬",
    "Cinema":   "🎬",
    "Fofoca":   "⭐",
}

CORES_TEMA = {
    "Mundo":    "2c3e50",
    "Economia": "1a6b3a",
    "Politica": "7b0000",
    "IA":       "5b2c91",
    "Wellness": "e65100",
    "Ciencia":  "006064",
    "Cinema":   "4a0080",
    "Fofoca":   "6a1b9a",
}

# Hashtags para posts Instagram por tema
HASHTAGS_TEMA = {
    "Mundo":    "#noticias #mundo #geopolitica #internacional #atualidades #news",
    "Economia": "#economia #mercado #investimentos #bolsa #financas #bovespa",
    "Politica": "#politica #brasil #congresso #governo #democracia #stf",
    "IA":       "#ia #inteligenciaartificial #ai #chatgpt #claude #tecnologia",
    "Wellness": "#wellness #corrida #ciclismo #treino #saude #endurance",
    "Ciencia":  "#ciencia #pesquisa #descoberta #saude #espaco #science",
    "Cinema":   "#cinema #filmes #series #streaming #netflix #cultura",
    "Fofoca":   "#celebridades #hollywood #famosos #popculture #entretenimento",
}

# Compatibilidade com colunas antigas do Google Sheets (renomeadas em v15.2)
# Gustavo: quando puder, renomeie as colunas na planilha:
#   "Mercado" → "Economia"  |  "Fitness" → "Wellness"
# E adicione a coluna "IA". Remova "Tech", "Esportes", "Motos".
MAPEAMENTO_LEGADO = {
    "Mercado": "Economia",
    "Fitness": "Wellness",
}

# =============================================================================
# --- PUBLICAÇÃO / SITE (v17.0) ---
# =============================================================================
EDICOES_DIR = "edicoes"
# Domínio público do jornal (allnewsjournal.streamlit.app NÃO existe;
# a URL real do Streamlit tem hash — o leitor vê só o domínio próprio).
SITE_URL    = "https://allnewsjournal.uk"

# =============================================================================
# --- INSTAGRAM: CARROSSEL + REEL (v17.0) ---
# =============================================================================
# Handle real da conta (mudou de @allnews_journal em jun/2026).
INSTAGRAM_HANDLE         = "@all.news.journal"
INSTAGRAM_CARROSSEL_MODO = "rotativo"   # "rotativo" | "panorama"
REEL_SEGUNDOS_POR_SLIDE  = 3
REEL_FADE_SEGUNDOS       = 0.4

# Numerais romanos por caderno (rótulo dos cards)
NUMERAIS_CADERNO = {
    "Mundo": "I", "Economia": "II", "Politica": "III", "IA": "IV",
    "Wellness": "V", "Ciencia": "VI", "Cinema": "VII", "Fofoca": "VIII",
}
