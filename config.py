"""
All News Journal - Configuração central
Compartilhada entre main.py, app.py e instagram_poster.py
"""

# Ordem editorial dos cadernos
ORDEM_CADERNOS = ["Mundo", "Economia", "Politica", "IA", "Wellness", "Ciencia", "Cinema", "Fofoca"]

RSS_FEEDS = {
    "Mundo": [
        "https://g1.globo.com/rss/g1/mundo/",
        "https://www.bbc.com/portuguese/index.xml",
        "https://rss.uol.com.br/feed/noticias/internacional.xml",
        "https://www.dw.com/pt-br/rss/rss/rmundo/s-31600",
        "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
    ],
    "Economia": [
        "https://g1.globo.com/rss/g1/economia/",
        "https://www.infomoney.com.br/feed/",
        "https://pox.globo.com/rss/valor/noticia/feed.xml",
        "https://exame.com/rss/",
        "https://www.moneytimes.com.br/feed/",
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
        "https://www.nationalgeographicbrasil.com/ciencia/rss",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://super.abril.com.br/feed/",
    ],
    "Cinema": [
        "https://omelete.com.br/rss/",
        "https://www.adorocinema.com/rss/",
        "https://variety.com/v/film/feed/",
        "https://deadline.com/category/film/feed/",
        "https://collider.com/feed/",
    ],
    "Fofoca": [
        "https://purepeople.com.br/rss.xml",
        "https://www.caras.com.br/rss/",
        "https://tmz.com/rss.xml",
        "https://pagesix.com/feed/",
        "https://www.dailymail.co.uk/tvshowbiz/index.rss",
    ],
}

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

# Cor hex SEM o # (usado para gerar gradientes nas imagens Instagram)
CORES_TEMA = {
    "Mundo":    "457b9d",
    "Economia": "2a9d8f",
    "Politica": "e63946",
    "IA":       "5b2c91",
    "Wellness": "f4a261",
    "Ciencia":  "2b9348",
    "Cinema":   "c77dff",
    "Fofoca":   "e76f51",
}

FILTROS_TEMA = {
    "Mundo": [
        "horoscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "% off", "em oferta", "promocao",
    ],
    "Economia": [
        "horoscopo", "moda", "futebol", "bbb", "celebridade", "novela",
        "% off", "em oferta", "promocao",
    ],
    "Politica": [
        "horoscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "% off", "em oferta", "promocao",
    ],
    "IA": [
        "horoscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "morre", "falece", "aniversario",
        "bitcoin", "ethereum", "nft", "blockchain", "criptomoeda",
        "% off", "em oferta", "promocao", "desconto",
        "10 dicas", "5 truques", "guia completo de",
    ],
    "Wellness": [
        "politica", "conflito", "guerra", "eleicao",
        "% off", "em oferta", "promocao",
        "horoscopo", "bbb", "big brother", "novela",
    ],
    "Ciencia": [
        "horoscopo", "moda", "futebol", "bbb", "big brother",
        "celebridade", "novela", "% off", "em oferta", "promocao",
    ],
    "Cinema": [
        "horoscopo", "futebol", "bbb", "big brother",
        "% off", "em oferta", "promocao", "politica", "conflito",
    ],
    "Fofoca": [
        "% off", "em oferta", "promocao",
        "futebol", "politica", "economia",
    ],
}

INSTRUCAO_TEMA = {
    "Mundo": (
        "Inclua: paises envolvidos, contexto geopolitico, consequencias praticas "
        "e qualquer declaracao relevante de lideres. Escreva em portugues brasileiro "
        "claro, sem jargao diplomatico desnecessario."
    ),
    "Economia": (
        "Inclua: variacao percentual quando disponivel, impacto para o consumidor "
        "ou investidor brasileiro, e contexto macroeconomico. Escreva de forma clara "
        "e objetiva, sem sensacionalismo."
    ),
    "Politica": (
        "Foque na acao politica concreta, quem propoe, quem se opoe e qual o impacto "
        "para o cidadao comum. Escreva de forma neutra, sem opiniao ou adjetivos valorativos."
    ),
    "IA": (
        "Inclua: empresa/laboratorio envolvido (OpenAI, Anthropic, Google DeepMind, "
        "Meta AI, xAI, Mistral, etc.), o nome exato do modelo ou produto quando "
        "mencionado, dados tecnicos relevantes (parametros, benchmarks, contexto, "
        "modalidades) e o impacto pratico para usuarios ou para o mercado de IA. "
        "Se a noticia for sobre regulacao ou etica, explique a tensao central em "
        "linguagem clara, sem jargao juridico. Evite hype — escreva como reporter "
        "de tecnologia experiente, nao como entusiasta."
    ),
    "Wellness": (
        "REGRA CRITICA DE IDIOMA: o texto base pode estar em ingles. "
        "Independentemente disso, o resumo final DEVE ser escrito EXCLUSIVAMENTE "
        "em Portugues Brasileiro fluente — jamais use palavras em ingles no corpo "
        "do texto.\n"
        "FOCO: cultura de saude, performance e longevidade. Cobre corrida, "
        "ciclismo, triatlo, musculacao, mobilidade, nutricao esportiva, sono, "
        "recuperacao e mindset atletico. Inclua dados praticos sempre que o "
        "texto base os fornecer (series, pace por km, zonas de FC, macros, VO2). "
        "Evite tom de consultorio medico, evite linguagem de revista de dieta, "
        "evite sensacionalismo de saude."
    ),
    "Ciencia": (
        "Inclua: instituicao de pesquisa, metodologia resumida e implicacoes praticas "
        "da descoberta. Escreva em portugues claro, sem jargao excessivo, tornando "
        "a ciencia acessivel ao publico geral."
    ),
    "Cinema": (
        "Inclua: titulo original e em portugues (se diferente), streaming ou estreia "
        "nos cinemas, genero, e por que isso importa para o espectador. Escreva com "
        "entusiasmo moderado, sem spoilers."
    ),
    "Fofoca": (
        "REGRA CRITICA DE IDIOMA: o texto base pode estar em ingles. "
        "Independentemente disso, o resumo final DEVE ser escrito EXCLUSIVAMENTE "
        "em Portugues Brasileiro. Foco em cultura pop INTERNACIONAL: Hollywood, "
        "K-pop, realeza britanica, eventos virais globais. Escreva de forma leve "
        "e bem-humorada, sem julgamentos morais."
    ),
}

FALLBACK_IMAGES = {
    "Mundo":    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&h=300&fit=crop",
    "Economia": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=300&fit=crop",
    "Politica": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=600&h=300&fit=crop",
    "IA":       "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&h=300&fit=crop",
    "Wellness": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&h=300&fit=crop",
    "Ciencia":  "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=600&h=300&fit=crop",
    "Cinema":   "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&h=300&fit=crop",
    "Fofoca":   "https://images.unsplash.com/photo-1586769852044-692d6e3703f0?w=600&h=300&fit=crop",
}

HASHTAGS = {
    "Mundo":    "#noticias #mundo #geopolitica #internacional #atualidades #news",
    "Economia": "#economia #mercado #investimentos #bolsa #financas #bovespa",
    "Politica": "#politica #brasil #congresso #governo #democracia #stf",
    "IA":       "#ia #inteligenciaartificial #ai #chatgpt #claude #tecnologia",
    "Wellness": "#wellness #corrida #ciclismo #treino #saude #endurance",
    "Ciencia":  "#ciencia #pesquisa #descoberta #saude #espaco #science",
    "Cinema":   "#cinema #filmes #series #streaming #netflix #cultura",
    "Fofoca":   "#celebridades #hollywood #famosos #popculture #entretenimento",
}
