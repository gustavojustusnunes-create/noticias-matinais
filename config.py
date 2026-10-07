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
GEMINI_API_KEY   = (os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")).strip()
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
# --- ORDEM EDITORIAL DOS CADERNOS (OFICIAIS v18.0) ---
# =============================================================================
ORDEM_CADERNOS = [
    "Macroeconomia & Mercados",
    "Geopolítica & Assuntos Globais",
    "Estratégia Corporativa & M&A",
    "Fronteira Tecnológica & IA",
    "Ciência & Inovação",
]

# =============================================================================
# --- FEEDS RSS PRIMÁRIOS (PADRÃO REUTERS & THE ECONOMIST) ---
# =============================================================================
RSS_FEEDS = {
    "Macroeconomia & Mercados": [
        "https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/",
        "https://valor.globo.com/rss/",
        "https://www.infomoney.com.br/feed/",
        "https://exame.com/invest/feed/",
        "https://g1.globo.com/rss/g1/economia/",
    ],
    "Geopolítica & Assuntos Globais": [
        "https://www.bbc.com/portuguese/index.xml",
        "https://www.dw.com/pt-br/rss/rss/rmundo/s-31600",
        "https://g1.globo.com/rss/g1/mundo/",
        "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
        "https://feeds.folha.uol.com.br/mundo/rss091.xml",
    ],
    "Estratégia Corporativa & M&A": [
        "https://exame.com/negocios/feed/",
        "https://valor.globo.com/empresas/rss/",
        "https://www.infomoney.com.br/mercados/feed/",
        "https://pipelinevalor.globo.com/feed/",
        "https://fusoesaquisicoes.com/feed/",
    ],
    "Fronteira Tecnológica & IA": [
        "https://olhardigital.com.br/editorias/inteligencia-artificial/feed/",
        "https://canaltech.com.br/inteligencia-artificial/rss/",
        "https://g1.globo.com/rss/g1/tecnologia/",
        "https://rss.uol.com.br/feed/tilt.xml",
        "https://www.tecmundo.com.br/rss",
    ],
    "Ciência & Inovação": [
        "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
        "https://agencia.fapesp.br/rss",
        "https://canaltech.com.br/ciencia/rss/",
        "https://g1.globo.com/rss/g1/ciencia-e-saude/",
        "https://www.nationalgeographicbrasil.com/ciencia/rss",
    ],
}

# =============================================================================
# --- FILTROS DE CONTEÚDO ---
# =============================================================================
# =============================================================================
# --- FILTROS DE CONTEÚDO ---
# =============================================================================
FILTRO_GLOBAL = [
    "vídeo", "veja vídeo", "veja o momento", "veja momento", 
    "imagens mostram", "assista", "drone", "flagra", "câmera de segurança",
    "galeria de fotos", "veja fotos",
]

FILTROS_TEMA = {
    "Macroeconomia & Mercados": [
        "horóscopo", "moda", "futebol", "brasileirão", "campeonato",
        "onde assistir", "onde-assistir", "ao vivo", "ao-vivo",
        "gol", "escalação", "clube", "torcedor",
        "lollapalooza", "festival", "show", "ingresso",
        "previsão do tempo", "clima", "chuva",
        "bbb", "big brother", "prêmio do bbb", "reality",
        "tênis", "fonseca", "alcaraz", "sinner", "nadal",
        "lotofácil", "mega-sena", "mega sena", "quina", "lotomania",
        "timemania", "dupla sena", "resultado sorteado",
        "prêmio da loteria", "números sorteados",
        "fofoca", "celebridade", "namoro", "casamento",
        "aposta", "bet", "cassino",
    ],

    "Geopolítica & Assuntos Globais": [
        "horóscopo", "moda", "futebol", "carnaval", "celebridade",
        "reality show", "bbb", "loteria", "sorteio",
        "crime comum", "acidente de trânsito", "briga de bar",
        "fofoca", "viralizou", "influenciador",
    ],

    "Estratégia Corporativa & M&A": [
        "horóscopo", "moda", "futebol", "bbb", "reality",
        "vida pessoal", "namoro", "casamento", "separação",
        "crime comum", "acidente", "promoção de supermercado",
        "cupom de desconto", "queima de estoque",
    ],

    "Fronteira Tecnológica & IA": [
        "horóscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "morre", "falece", "aniversário",
        "bitcoin", "ethereum", "nft", "blockchain", "criptomoeda",
        "% off", "em oferta", "promoção", "desconto",
        "10 dicas", "5 truques", "guia completo de",
        "aposta", "bet", "cassino",
    ],

    "Ciência & Inovação": [
        "horóscopo", "astrologia", "signo", "tarô",
        "mão de obra", "mercado de trabalho", "concurso público",
        "dieta milagrosa", "cura caseira", "emagrecer",
        "fofoca", "celebridade",
    ],
}

# =============================================================================
# --- INSTRUÇÕES POR CADERNO (PADRÃO THE ECONOMIST / REUTERS) ---
# =============================================================================
INSTRUCAO_TEMA = {
    "Macroeconomia & Mercados": "Foco: Política monetária, juros, câmbio, curvas de rendimento, fluxos de capital global, liquidez e balanços sistêmicos.",
    "Geopolítica & Assuntos Globais": "Foco: Relações internacionais, diplomacia, disputas comerciais, soberania, segurança nacional e acordos multilaterais.",
    "Estratégia Corporativa & M&A": "Foco: Fusões, aquisições, governança, alocação de capital corporativo, reestruturações e teses de investimento.",
    "Fronteira Tecnológica & IA": "Foco: Modelos de fronteira, semicondutores, capacidade computacional, Capex de infraestrutura e regulação de IA.",
    "Ciência & Inovação": "Foco: Materiais avançados, biotecnologia, transição energética, quebra de paradigmas técnicos e viabilidade comercial.",
}

# =============================================================================
# --- IMAGENS DE FALLBACK (BIBLIOTECA INTERNA) ---
FALLBACK_IMAGES = {
    "Macroeconomia & Mercados": [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?w=600&h=1066&fit=crop"
    ],
    "Geopolítica & Assuntos Globais": [
        "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1494522855154-9297ac14b55f?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1526660690293-bcd32dc3b562?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=600&h=1066&fit=crop"
    ],
    "Estratégia Corporativa & M&A": [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&h=1066&fit=crop"
    ],
    "Fronteira Tecnológica & IA": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1655393001768-d946c98d6915?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1684369175836-829141042cb1?w=600&h=1066&fit=crop"
    ],
    "Ciência & Inovação": [
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1581093458791-9f3c3900df4b?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=600&h=1066&fit=crop",
        "https://images.unsplash.com/photo-1564325724739-bae0bd08762c?w=600&h=1066&fit=crop"
    ],
}

# =============================================================================
# --- IDENTIDADE VISUAL ---
# =============================================================================
ICONES_TEMA = {
    "Macroeconomia & Mercados":    "📊",
    "Geopolítica & Assuntos Globais": "🌐",
    "Estratégia Corporativa & M&A": "🏛️",
    "Fronteira Tecnológica & IA":    "⚡",
    "Ciência & Inovação":          "🔬",
}

CORES_TEMA = {
    "Macroeconomia & Mercados":    "1a6b3a",
    "Geopolítica & Assuntos Globais": "1e3a5f",
    "Estratégia Corporativa & M&A": "8b5a2b",
    "Fronteira Tecnológica & IA":    "4f46e5",
    "Ciência & Inovação":          "006064",
}

# Hashtags para posts Instagram por caderno oficial
HASHTAGS_TEMA = {
    "Macroeconomia & Mercados":    "#macroeconomia #mercados #politicaMonetaria #investimentos #financas #economia",
    "Geopolítica & Assuntos Globais": "#geopolitica #relacoesInternacionais #comercioGlobal #diplomacia #seguranca",
    "Estratégia Corporativa & M&A": "#corporativo #fusoeAquisicoes #governanca #investimento #negocios",
    "Fronteira Tecnológica & IA":    "#ia #inteligenciaArtificial #semicondutores #deeptech #tecnologia",
    "Ciência & Inovação":          "#ciencia #inovacao #biotecnologia #transicaoEnergetica #pesquisa",
}

# Compatibilidade suave com colunas legadas da planilha Google Sheets
MAPEAMENTO_LEGADO = {
    "Economia": "Macroeconomia & Mercados",
    "Mercado": "Macroeconomia & Mercados",
    "Macroeconomia": "Macroeconomia & Mercados",
    "Mundo": "Geopolítica & Assuntos Globais",
    "Politica": "Geopolítica & Assuntos Globais",
    "Política": "Geopolítica & Assuntos Globais",
    "Geopolitica": "Geopolítica & Assuntos Globais",
    "IA": "Fronteira Tecnológica & IA",
    "Tech": "Fronteira Tecnológica & IA",
    "Ciencia": "Ciência & Inovação",
    "Ciência": "Ciência & Inovação",
    "Macroeconomia & Mercados": "Macroeconomia & Mercados",
    "Geopolítica & Assuntos Globais": "Geopolítica & Assuntos Globais",
    "Estratégia Corporativa & M&A": "Estratégia Corporativa & M&A",
    "Fronteira Tecnológica & IA": "Fronteira Tecnológica & IA",
    "Ciência & Inovação": "Ciência & Inovação",
}

# =============================================================================
# --- PUBLICAÇÃO / SITE (v18.0) ---
# =============================================================================
EDICOES_DIR = "edicoes"
SITE_URL    = "https://allnewsjournal.uk"

# =============================================================================
# --- INSTAGRAM: CARROSSEL + REEL (v18.0) ---
# =============================================================================
INSTAGRAM_HANDLE         = "@all.news.journal"
INSTAGRAM_CARROSSEL_MODO = "rotativo"
REEL_SEGUNDOS_POR_SLIDE  = 3
REEL_FADE_SEGUNDOS       = 0.4

# Numerais romanos oficiais por caderno
NUMERAIS_CADERNO = {
    "Macroeconomia & Mercados":    "I",
    "Geopolítica & Assuntos Globais": "II",
    "Estratégia Corporativa & M&A": "III",
    "Fronteira Tecnológica & IA":    "IV",
    "Ciência & Inovação":          "V",
}

# =============================================================================
# --- PROMPTS EDITORIAIS NORMATIVOS (NÓ 2: THE ECONOMIST / CRITIC) ---
# =============================================================================
SYSTEM_PROMPT_WRITER = """
Você é um correspondente sênior e analista executivo do All News Journal. Sua função é redigir a resenha analítica oficial da matéria original em estilo incisivo e executivo (inspirado no padrão The Economist).

ENTRADA:
Título, categoria e corpo da matéria original.

DIRETRIZES DE ESCRITA E TOM DE VOZ:
- TOM: Sóbrio, incisivo, perspicaz e livre de clichês jornalísticos ou chavões de IA.
- PROIBIÇÃO ABSOLUTA: NUNCA gere frases como "estabelecem uma nova dinâmica competitiva", "impactos substanciais na cadeia operacional", "acompanhado de perto por analistas". Cada frase deve ter conteúdo informativo real.
- LIMPEZA TOTAL: Remova imediatamente créditos de imagens (ex: "Foto: Getty"), legendas, nomes de agências (Reuters, BBC, G1) e caracteres truncados.

ESTRUTURA OBRIGATÓRIA DA RESENHA (ENTRE 60 E 90 PALAVRAS NO TOTAL):
1. O FATO: 1 frase direta com o sujeito da ação, dados quantitativos e o evento central sem rodeios.
2. CONTEXTO & MECÂNICA: 1 ou 2 frases explicando as forças estruturais por trás do fato (pressão de custos, dinâmica regulatória, incentivos geopolíticos).
3. O DESDOBRAMENTO CRÍTICO (SO WHAT?): 1 frase apontando quem ganha, quem perde e qual o risco imediato a ser monitorado.
PONTUAÇÃO FINAL: O texto DEVE obrigatoriamente terminar com ponto final (.) e ter sentido completo.

TRATAMENTO DE EXCEÇÃO:
Se o texto-fonte não tiver informações concretas suficientes para preencher os três passos com dados factuais, retorne o campo "status": "DISCARD" em vez de tentar inventar ou usar texto genérico.

SAÍDA ESTRITAMENTE EM FORMATO JSON:
Se a matéria possuir dados factuais suficientes:
{
  "status": "OK",
  "titulo_limpo": "Título analítico de até 12 palavras em tom institucional",
  "resumo_texto": "Texto da resenha contendo rigorosamente entre 60 e 90 palavras estruturado nos três passos.",
  "contagem_palavras": 75
}

Se o texto-fonte for raso ou insuficiente:
{
  "status": "DISCARD",
  "motivo": "Ausência de informações concretas suficientes para preencher os três passos com dados factuais"
}
"""

SYSTEM_PROMPT_CRITIC = """
Você é o Quality Gate do All News Journal. Audite a resenha contra as diretrizes normativas da publicação (Padrão The Economist):

REGRAS DE VALIDAÇÃO:
1. Contagem: O campo "resumo_texto" tem rigorosamente entre 60 e 90 palavras?
2. Integridade: A frase final termina com ponto final (.) e encerra o desdobramento crítico sem corte abrupto?
3. Limpeza & Ausência de Chavões: Ausência de créditos de foto ("Getty", "BBC", "Foto") e ausência de clichês proibidos ("dinâmica competitiva", "cadeia operacional", "acompanhado de perto por analistas").
4. Estrutura Analítica (3 Passos): O texto contém O Fato (com dados quantitativos), Contexto & Mecânica (forças estruturais) e Desdobramento Crítico (quem ganha/perde e risco)?

RESPOSTA OBRIGATÓRIA (JSON):
{
  "aprovado": true,
  "word_count": 75,
  "motivo_rejeicao": "",
  "instrucao_reescrita": ""
}
Se reprovado, retorne "aprovado": false e aponte o erro em "instrucao_reescrita" para regeneração imediata.
"""

