"""
finance_feeds.py — Coleta RSS e resumo via IA (Gemini) para o All News Finance
Focado em economia, mercado financeiro, empresas e macroeconomia.
"""
import re
import feedparser
from datetime import datetime

from claude_api import chamar_claude_api
from sheets_db import gerar_hash

ORDEM_CADERNOS_FINANCE = [
    "Mercado & Bolsa",
    "Empresas & Negócios",
    "Macroeconomia",
    "Cripto & FinTechs",
]

FEEDS_FINANCE = {
    "Mercado & Bolsa": [
        ("InfoMoney Mercados", "https://www.infomoney.com.br/mercados/feed/"),
        ("Money Times", "https://www.moneytimes.com.br/feed/"),
        ("E-Investidor", "https://einvestidor.estadao.com.br/feed/"),
    ],
    "Empresas & Negócios": [
        ("InfoMoney Negócios", "https://www.infomoney.com.br/negocios/feed/"),
        ("Exame Negócios", "https://exame.com/negocios/feed/"),
        ("Money Times Empresas", "https://www.moneytimes.com.br/empresas/feed/"),
    ],
    "Macroeconomia": [
        ("InfoMoney Economia", "https://www.infomoney.com.br/economia/feed/"),
        ("Exame Economia", "https://exame.com/economia/feed/"),
        ("CNN Brasil Economia", "https://www.cnnbrasil.com.br/economia/feed/"),
    ],
    "Cripto & FinTechs": [
        ("InfoMoney Cripto", "https://www.infomoney.com.br/onde-investir/criptoativos/feed/"),
        ("Money Times Cripto", "https://www.moneytimes.com.br/criptomoedas/feed/"),
    ],
}


def extrair_texto_rss(entry):
    """Extrai texto do summary ou content do item RSS."""
    if "content" in entry and entry.content:
        raw = entry.content[0].value
    elif "summary" in entry:
        raw = entry.summary
    elif "description" in entry:
        raw = entry.description
    else:
        return ""
    texto = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(texto.split())[:1200]


def extrair_imagem_rss(entry):
    """Tenta extrair a imagem de destaque do item RSS."""
    if "media_content" in entry and entry.media_content:
        for media in entry.media_content:
            if media.get("medium") == "image" or "image" in media.get("type", ""):
                return media.get("url")
    if "enclosures" in entry and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href")
    texto = ""
    if "content" in entry and entry.content:
        texto = entry.content[0].value
    elif "summary" in entry:
        texto = entry.summary
    m = re.search(r'<img[^>]+src=["\'](http[^"\']+)["\']', texto, re.I)
    if m:
        return m.group(1)
    return None


def resumir_noticia_finance(titulo, texto_bruto):
    """Chama a API do Gemini para produzir resumo financeiro elegante de 65-105 palavras."""
    prompt = f"""Você é editor-chefe do All News Finance, um jornal diário de economia e mercado financeiro para investidores e executivos.

TAREFA: Escreva um resumo analítico e direto da notícia abaixo.

TÍTULO: {titulo}
TEXTO ORIGINAL: {texto_bruto}

REGRAS ESTREITAS DE JORNALISMO FINANCEIRO:
1. COMPRIMENTO: O resumo DEVE ter entre 150 e 250 palavras.
2. CONTEÚDO: Vá direto ao ponto com fatos, números, porcentagens, tickers ou impactos financeiros. NUNCA faça mistério ("veja 5 motivos...", "descubra por que..."). Forneça contexto, os antecedentes e uma breve análise do impacto no cenário atual.
3. Se a notícia for apenas caça-clique/clickbait ou não trouxer informação real, responda APENAS a palavra: SKIP
4. TOM: Português brasileiro formal, culto, objetivo e analítico.
5. PROIBIDO: Emojis, bullet points, asteriscos ou formatação markdown. Escreva em 1 ou 2 parágrafos corridos de texto puro.
6. NUNCA use as palavras "promessa", "revolucionário" ou exageros de marketing sem dados."""

    resumo = chamar_claude_api(prompt, max_tokens=600)
    if not resumo:
        print("         ⏭️ Pulado: Resumo nulo")
        return None
    
    if "SKIP" in resumo.upper():
        print(f"         ⏭️ Pulado: Modelo respondeu SKIP. Resposta: {resumo[:100]}...")
        return None
        
    num_palavras = len(resumo.split())
    if num_palavras < 40:
        print(f"         ⏭️ Pulado: Resumo muito curto ({num_palavras} palavras). Resposta: {resumo[:100]}...")
        return None
        
    return resumo.strip()


def coletar_noticias_finance(max_por_caderno=4):
    """
    Percorre os feeds financeiros, coleta e resume as notícias das 4 seções fixas.
    Retorna dicionário {secao: [lista_de_noticias]}.
    """
    print("\n📈 Iniciando curadoria do All News Finance...")
    edicao = {secao: [] for secao in ORDEM_CADERNOS_FINANCE}
    hashes_vistos = set()

    # Imagem genérica para mercado financeiro/bolsa
    IMAGEM_GENERICA = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&q=80&w=800"

    for secao in ORDEM_CADERNOS_FINANCE:
        feeds = FEEDS_FINANCE.get(secao, [])
        print(f"\n   📑 Seção: {secao}")
        coletadas = 0

        for nome_feed, url_feed in feeds:
            if coletadas >= max_por_caderno:
                break
            try:
                feed = feedparser.parse(url_feed)
                for entry in feed.entries:
                    if coletadas >= max_por_caderno:
                        break
                    titulo = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()
                    if not titulo or not link:
                        continue
                    
                    h = gerar_hash(titulo, link)
                    if h in hashes_vistos:
                        continue
                    hashes_vistos.add(h)

                    # Filtra títulos claramente publicitários/clickbait
                    if any(t in titulo.lower() for t in ["cupom", "oferta exclusiva", "confira os motivos", "cinco motivos", "5 motivos", "veja por que"]):
                        continue

                    texto = extrair_texto_rss(entry)
                    if len(texto) < 100:
                        continue

                    print(f"      📝 Resumindo ({nome_feed}): {titulo[:60]}...")
                    resumo = resumir_noticia_finance(titulo, texto)
                    if not resumo:
                        print("         ⏭️ Pulado (SKIP ou curto)")
                        continue

                    imagem = extrair_imagem_rss(entry)
                    if not imagem:
                        imagem = IMAGEM_GENERICA

                    edicao[secao].append({
                        "titulo": titulo,
                        "link": link,
                        "resumo": resumo,
                        "imagem": imagem,
                        "fonte": nome_feed,
                        "data": datetime.now().strftime("%Y-%m-%d"),
                    })
                    coletadas += 1
            except Exception as e:
                print(f"      ⚠️ Erro ao processar feed {nome_feed}: {e}")

    # Log de contagem
    total = sum(len(n) for n in edicao.values())
    print(f"\n✅ Curadoria do All News Finance finalizada! {total} notícias selecionadas.")
    return edicao
