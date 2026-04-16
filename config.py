"""
config.py — Constantes e configurações do All News Journal
Centraliza feeds RSS, filtros, instruções de tema, imagens e cores.
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

# =============================================================================
# --- FEEDS RSS ---
# =============================================================================
RSS_FEEDS = {
    "Mundo":    ["https://g1.globo.com/rss/g1/mundo/"],
    "Mercado":  [
        "https://www.infomoney.com.br/feed/",
        "https://rss.uol.com.br/feed/economia.xml",
        "https://economia.uol.com.br/rss.xml",
        "https://valor.globo.com/rss/",
        "https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/",
        "https://exame.com/invest/feed/",
    ],
    "Politica": ["https://g1.globo.com/rss/g1/politica/"],
    "Tech":     [
        "https://feeds.feedburner.com/TechCrunch/",
        "https://www.theverge.com/rss/index.xml",
        "https://olhardigital.com.br/feed/",
        "https://tecnoblog.net/feed/",
        "https://canaltech.com.br/rss/",
        "https://rss.tecmundo.com.br/feed",
    ],
    "Esportes": [
        "https://pt.motorsport.com/rss/f1/news/",
        "https://www.theplayoffs.com.br/feed/",
        "https://www.espn.com.br/rss/",
        "https://sportv.globo.com/rss/sportv/",
        "https://www.uol.com.br/esporte/rss.xml",
        "https://ge.globo.com/rss/feed.xml",
        "https://www.lance.com.br/feed/",
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
        "https://www.womenshealthmag.com/rss/all.xml/",
        "https://boaforma.abril.com.br/feed/",
        "https://vivabem.uol.com.br/rss.xml",
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
        "https://motoo.uol.com.br/rss.xml",
        "https://www.motoo.com.br/feed/",
        "https://motoblog.uol.com.br/feed/",
        "https://www.motonline.com.br/feed/",
        "https://www.duasrodas.com/feed/",
        "https://www.motor1.com/rss/category/motos/",
        "https://www.icarros.com.br/noticias/motos/rss.xml",
        "https://revistaautoesporte.globo.com/rss/",
    ],
    "Fofoca":   [
        "https://hugogloss.uol.com.br/feed/",
        "https://revistaquem.globo.com/rss/quem/",
        "https://people.com/feed/",
        "https://variety.com/feed/",
        "https://ew.com/feed/",
    ],
}

# Feeds cujo conteúdo está em inglês (requerem tradução automática)
FEEDS_INGLES = {
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.runnersworld.com/rss/all.xml/",
    "https://www.menshealth.com/rss/all.xml/",
    "https://www.womenshealthmag.com/rss/all.xml/",
    "https://www.bicycling.com/rss/all.xml/",
    "https://people.com/feed/",
    "https://variety.com/feed/",
    "https://ew.com/feed/",
}

# =============================================================================
# --- FILTROS DE CONTEÚDO ---
# =============================================================================
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
        "palpite", "palpites", "apostas", "aposta", "odds", "odd:", "prognóstico", "prognósticos",
        "melhores apostas", "mercado de apostas", "bet", "betting", "bets",
        "over/under", "handicap", "casa de aposta", "casas de aposta",
        "jogo do bicho", "loteria", "lotérica",
        "esportiva bet", "superbet", "betano", "sportingbet",
        "pixbet", "brazino", "estrela bet",
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

    "Fofoca":   [
        # Realities e subcelebridades de reality
        "ex-bbb", "ex bbb", "bbb ", "big brother",
        "fazenda ", "a fazenda", "reality show",
        # Gêneros musicais de nicho brasileiro sem relevância global
        "sertanejo", "pagodeiro", "funkeiro", "funk",
        "mc ", "mc.", "dj ",
        # Política (não pertence ao caderno)
        "governo federal", "presidente lula", "bolsonaro",
        "congresso nacional", "eleições", "partido político",
        # Subcelebridades brasileiras sem projeção internacional
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
        # Ex-BBB e ex-reality sem carreira sólida
        "jade picon", "larissa manoela", "maísa",
        "juliette", "gil do vigor", "arthur aguiar",
        "davi brito", "matteus", "beatriz reis", "lucas souza",
        # Apresentadores/comentaristas locais
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
    "nba":   [
        "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=600&h=300&fit=crop",
        "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=600&h=300&fit=crop",
    ],
    "f1":    [
        "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&h=300&fit=crop",
        "https://images.unsplash.com/photo-1541447271487-09612b3f49f7?w=600&h=300&fit=crop",
    ],
    "mma":   [
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=300&fit=crop",
        "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&h=300&fit=crop",
    ],
    "tenis": [
        "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?w=600&h=300&fit=crop",
        "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=600&h=300&fit=crop",
    ],
}

SPORT_KEYWORDS = {
    "nba":   ["nba", "basquete", "basquetebol", "lakers", "warriors", "celtics",
              "lebron", "curry"],
    "f1":    ["f1", "formula", "grand prix", "gp de", "verstappen", "hamilton",
              "ferrari", "leclerc"],
    "mma":   ["mma", "ufc", "evloev", "volkanovski", "poatan", "adesanya"],
    "tenis": ["tênis", "tennis", "fonseca", "alcaraz", "sinner", "open"],
}

# =============================================================================
# --- IDENTIDADE VISUAL ---
# =============================================================================
ICONES_TEMA = {
    "Mundo":    "🌎",
    "Mercado":  "📈",
    "Politica": "🏛️",
    "Tech":     "💻",
    "Esportes": "🏎️",
    "Cinema":   "🎬",
    "Fitness":  "🏃",
    "Ciencia":  "🔬",
    "Motos":    "🏍️",
    "Fofoca":   "⭐",
}

CORES_TEMA = {
    "Mundo":    "2c3e50",
    "Mercado":  "1a6b3a",
    "Politica": "7b0000",
    "Tech":     "1565c0",
    "Esportes": "b71c1c",
    "Cinema":   "4a0080",
    "Fitness":  "e65100",
    "Ciencia":  "006064",
    "Motos":    "37474f",
    "Fofoca":   "6a1b9a",
}

# Hashtags para posts Instagram por tema
HASHTAGS_TEMA = {
    "Mundo":    "#noticias #mundo #geopolitica #internacional #atualidades",
    "Mercado":  "#mercado #economia #investimentos #bolsa #financas",
    "Politica": "#politica #brasil #congresso #governo #democracia",
    "Tech":     "#tecnologia #tech #inovacao #ia #futuro",
    "Esportes": "#esportes #f1 #nba #mma #tenis",
    "Cinema":   "#cinema #filmes #series #streaming #cultura",
    "Fitness":  "#fitness #treino #saude #corrida #bemestar",
    "Ciencia":  "#ciencia #pesquisa #descoberta #saude #futuro",
    "Motos":    "#motos #motociclismo #duasrodas #moto #pilotagem",
    "Fofoca":   "#celebridades #hollywood #famosos #entretenimento #popculture",
}

# =============================================================================
# --- PALAVRAS-CHAVE ESPORTES ---
# =============================================================================
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
