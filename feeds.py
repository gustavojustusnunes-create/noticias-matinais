"""
feeds.py — Coleta, filtro e processamento de feeds RSS do All News Journal
Inclui: busca de imagem, filtros de conteúdo, deduplicação e pipeline completo por tema.
"""
import re
import time

import feedparser
import requests

from config import (
    RSS_FEEDS, FILTROS_TEMA, INSTRUCAO_TEMA,
    FALLBACK_IMAGES, FILTRO_GLOBAL,
)
from claude_api import (
    chamar_claude_api, chamar_claude_haiku,
    extrair_contexto_base, limpar_resumo, remover_titulo_duplicado
)
from sheets_db import gerar_hash

# Dicionário global de status dos feeds (populado durante a coleta)
FEEDS_STATUS = {}


# =============================================================================
# --- BUSCA DE IMAGEM ---
# =============================================================================
def buscar_og_image(url_artigo, timeout=10):
    """Tenta extrair og:image / twitter:image da página do artigo."""
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
            # og:image:secure_url (CDNs como Valor/Bloomberg expõem só esta)
            r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']',
            # og:image padrão
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            # twitter:image
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
            # og:image:url
            r'<meta[^>]+property=["\']og:image:url["\'][^>]+content=["\']([^"\']+)["\']',
            # link rel="image_src" (portais mais antigos)
            r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']image_src["\']',
        ]
        for padrao in padroes:
            m = re.search(padrao, html, re.IGNORECASE)
            if m:
                url = m.group(1).strip().replace("&amp;", "&").replace("&#38;", "&")
                if url.startswith("http") and len(url) > 15:
                    return url

        extensoes = (".jpg", ".jpeg", ".png", ".webp")

        # Fallback preferencial: <img> com width >= 600 dentro de <article> ou <main>
        for bloco_padrao in (r"<article[^>]*>(.*?)</article>", r"<main[^>]*>(.*?)</main>"):
            bloco_m = re.search(bloco_padrao, html, re.IGNORECASE | re.DOTALL)
            if bloco_m:
                bloco = bloco_m.group(1)
                for m in re.findall(
                    r'<img[^>]+(?:src=["\']([^"\']+)["\'][^>]*width=["\'](\d+)["\']'
                    r'|width=["\'](\d+)["\'][^>]*src=["\']([^"\']+)["\'])',
                    bloco, re.IGNORECASE
                ):
                    src   = m[0] or m[3]
                    width = int(m[1] or m[2] or 0)
                    if (
                        width >= 600
                        and any(ext in src.lower() for ext in extensoes)
                        and src.startswith("http")
                        and "pixel" not in src
                        and "logo"  not in src.lower()
                        and "icon"  not in src.lower()
                    ):
                        return src

        # Fallback geral: primeira imagem grande na página
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


def extrair_imagem_rss(entry, tema, idx_entry=0):
    """
    Extrai imagem da notícia com hierarquia:
    og:image > media_content > enclosures > links > scraping HTML > fallback temático
    """
    extensoes = (".jpg", ".jpeg", ".png", ".webp")
    image_url = None

    image_url = buscar_og_image(entry.get("link", ""))

    if not image_url:
        for m in entry.get("media_content", []):
            if "url" in m and any(ext in m["url"].lower() for ext in extensoes):
                image_url = m["url"]
                break

    if not image_url:
        for enc in entry.get("enclosures", []):
            url_enc = enc.get("url", "")
            if any(ext in url_enc.lower() for ext in extensoes):
                image_url = url_enc
                break

    if not image_url:
        for l in entry.get("links", []):
            href = l.get("href", "")
            if l.get("type", "").startswith("image/") and any(ext in href.lower() for ext in extensoes):
                image_url = href
                break

    if not image_url:
        txt = "".join(c.value for c in entry.get("content", []))
        txt += entry.get("summary", "")
        for url in re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', txt):
            if (any(ext in url.lower() for ext in extensoes)
                    and "pixel" not in url and "doubleclick" not in url):
                image_url = url
                break

    if not image_url:
        image_url = FALLBACK_IMAGES.get(
            tema,
            "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
        )

    return image_url


# =============================================================================
# --- FILTROS E DEDUPLICAÇÃO ---
# =============================================================================
def aplicar_filtros(entry, tema):
    """Filtra artigos por palavras-chave no título, link e corpo do artigo."""
    from config import FILTRO_GLOBAL
    palavras_tema = FILTROS_TEMA.get(tema, [])
    palavras = FILTRO_GLOBAL + palavras_tema
    titulo = entry.get("title", "").lower()
    link   = entry.get("link",  "").lower()
    corpo  = extrair_contexto_base(entry, max_chars=400).lower()
    
    if _titulo_parece_ingles(titulo):
        return False
        
    return not any(p in titulo or p in link or p in corpo for p in palavras)



def titulos_similares(t1, t2):
    """Verifica se dois títulos cobrem o mesmo evento (similaridade ≥ 50%)."""
    p1 = set(re.findall(r"\w{4,}", t1.lower()))
    p2 = set(re.findall(r"\w{4,}", t2.lower()))
    if not p1 or not p2:
        return False
    return len(p1 & p2) / min(len(p1), len(p2)) >= 0.50


# =============================================================================
# --- COLETA DE FEEDS ---
# =============================================================================

def coletar_entries_multi(tema):
    """Coleta entries de múltiplos feeds para um tema, rastreando status."""
    valid_entries, vistos = [], set()
    for url in RSS_FEEDS.get(tema, []):
        try:
            feed = feedparser.parse(url)
            count = 0
            for e in feed.entries:
                link = e.get("link", "")
                if link not in vistos:
                    vistos.add(link)
                    e._fonte_url = url
                    valid_entries.append(e)
                    count += 1
            FEEDS_STATUS[url] = f"ok ({count} entries)"
        except Exception as ex:
            FEEDS_STATUS[url] = f"falha: {ex}"
            print(f"      ⚠️ {tema} ({url}): {ex}")
    return valid_entries


def coletar_entries_unico(tema):
    """Coleta entries do primeiro feed funcional para um tema."""
    for url in RSS_FEEDS.get(tema, []):
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for e in feed.entries:
                    e._fonte_url = url
                FEEDS_STATUS[url] = f"ok ({len(feed.entries)} entries)"
                return list(feed.entries)
            else:
                FEEDS_STATUS[url] = "ok (0 entries)"
        except Exception as ex:
            FEEDS_STATUS[url] = f"falha: {ex}"
            print(f"      ⚠️ {url}: {ex}")
    return []


# =============================================================================
# --- TRADUÇÃO DE TÍTULO (BLOCO 2) ---
# =============================================================================
def _e_feed_ingles(entry):
    """Verifica se a entry veio de um feed em inglês."""
    fonte = getattr(entry, "_fonte_url", "") or ""
    return fonte in FEEDS_INGLES


def _traduzir_titulo(titulo):
    """Traduz título inglês → PT-BR usando Claude Haiku."""
    prompt = (
        f"Traduza este título de artigo de inglês para português brasileiro, "
        f"mantendo o tom jornalístico e direto. "
        f"Retorne APENAS o título traduzido, sem aspas, sem explicação:\n\n{titulo}"
    )
    traduzido = chamar_claude_haiku(prompt, max_tokens=150)
    if traduzido and 5 < len(traduzido) < 250:
        return traduzido
    return titulo  # fallback: retorna original sem prefixo


_VOCAB_INGLES = [
    "the ", "how to", "why ", "what ", "best ", "your ", "you ",
    "with ", "this ", "that ", " and ", " for ", " are ", " was ",
    "running", "workout", "training", "marathon", "i ran",
    "tried ", "defense", "faster", "better", "recovery",
    "should ", "guide to", "relief", "prevention", "benefits of",
    "celebrity", "award", "season", "episode", "premiere",
]


def _titulo_parece_ingles(titulo: str) -> bool:
    """Detecta heuristicamente se um título está em inglês via vocabulário."""
    t = titulo.lower()
    return sum(1 for p in _VOCAB_INGLES if p in t) >= 2


# =============================================================================
# --- RANKING DE RELEVÂNCIA (BLOCO 7A) ---
# =============================================================================
def rankear_por_relevancia(candidatas, tema):
    """
    Usa Claude Haiku para ordenar candidatas do mais ao menos relevante.
    Aplicado apenas quando há mais de 6 candidatas.
    """
    if len(candidatas) <= 6:
        return candidatas

    titulos_numerados = "\n".join(
        f"{i+1}. {e.get('title', '')}" for i, e in enumerate(candidatas[:12])
    )
    prompt = (
        f"Dado estes {min(len(candidatas), 12)} títulos de notícias do caderno {tema}, "
        f"ordene do mais relevante ao menos relevante para o leitor brasileiro. "
        f"Retorne APENAS os números na ordem separados por vírgula (ex: 3,1,5,2,4,6).\n\n"
        f"{titulos_numerados}"
    )
    resposta = chamar_claude_haiku(prompt, max_tokens=100)
    if not resposta:
        return candidatas

    try:
        indices = [int(x.strip()) - 1 for x in resposta.split(",") if x.strip().isdigit()]
        reordenadas = []
        usados = set()
        for idx in indices:
            if 0 <= idx < len(candidatas) and idx not in usados:
                reordenadas.append(candidatas[idx])
                usados.add(idx)
        # Adiciona as que ficaram de fora (se houver)
        for i, e in enumerate(candidatas):
            if i not in usados:
                reordenadas.append(e)
        print(f"      📊 Ranking IA aplicado para {tema}.")
        return reordenadas
    except Exception:
        return candidatas


def limpar_titulo_entry(titulo: str) -> str:
    """Detecta e remove duplicação no próprio título do feed RSS."""
    if not titulo: return ""
    titulo = titulo.strip()
    meio = len(titulo) // 2
    for split_idx in range(meio - 15, meio + 15):
        if split_idx <= 0 or split_idx >= len(titulo): continue
        m1 = titulo[:split_idx].strip()
        m2 = titulo[split_idx:].strip()
        m1_clean = re.sub(r'[^\w\s]', '', m1).lower()
        m2_clean = re.sub(r'[^\w\s]', '', m2).lower()
        if m1_clean and m1_clean == m2_clean:
            return m1
    return titulo

# =============================================================================
# --- PIPELINE PRINCIPAL ---
# =============================================================================
def processar_tema(tema, historico_hashes, titulos_selecionados=None):
    """
    Pipeline completo para um tema:
    1. Coleta multi-fonte ou fonte única
    2. Filtra por palavras-chave + hash anti-duplicata
    3. Deduplica por similaridade de título
    4. Ranking de relevância (se > 6 candidatas)
    5. Traduz títulos de feeds em inglês
    6. Monta prompt com TÍTULO + CONTEXTO BASE
    7. Chama Claude com fallbacks em cascata
    """
    print(f"   📂 Processando: {tema}")

    TEMAS_MULTI_FONTE = {"IA", "Wellness", "Cinema", "Ciencia", "Fofoca"}

    # ── Coleta ──────────────────────────────────────────────────────────────
    if tema in TEMAS_MULTI_FONTE:
        valid_entries = coletar_entries_multi(tema)
        print(f"      📡 {len(valid_entries)} entradas coletadas.")
    else:
        valid_entries = coletar_entries_unico(tema)

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

    # ── Ranking de relevância ────────────────────────────────────────────────
    candidatas = rankear_por_relevancia(candidatas, tema)

    # ── Deduplicação por similaridade de título ──────────────────────────────
    if titulos_selecionados is None:
        titulos_selecionados = []

    noticias_filtradas = []
    for entry in candidatas:
        t = limpar_titulo_entry(entry.get("title", ""))
        entry["title"] = t
        if any(titulos_similares(t, e.get("title", "")) for e in noticias_filtradas):
            continue
        if any(titulos_similares(t, ts) for ts in titulos_selecionados):
            continue
        noticias_filtradas.append(entry)
        if len(noticias_filtradas) >= 4:
            break

    if not noticias_filtradas:
        print(f"      ⚠️ '{tema}' vazio após deduplicação.")
        return None

    instrucao = INSTRUCAO_TEMA.get(tema, "Inclua dados, números e contexto relevantes.")

    # ── Gera uma notícia por vez (sem batch) ─────────────────────────────────
    noticias_finais = []
    imagens_usadas  = set()

    for i, entry in enumerate(noticias_filtradas):
        titulo_entry = entry.get("title", "")

        # ── Contexto base ─────────────────────────────────────────────────────
        contexto = extrair_contexto_base(entry, max_chars=800)

        if contexto and contexto.lower() != titulo_entry.lower():
            input_individual = (
                f"Título: {titulo_entry}\n"
                f"Texto Base: {contexto}"
            )
        else:
            input_individual = f"Título: {titulo_entry}\n"

        # ── Prompt individual ─────────────────────────────────────────────────
        regras_absolutas = (
            f"═══════════════════════════════════════\n"
            f"REGRAS ABSOLUTAS DE FORMATO\n"
            f"═══════════════════════════════════════\n"
            f"1. TAMANHO: 150 a 250 palavras. Seja profundo e explicativo. Construa uma notícia completa com contexto, antecedentes e análise dos impactos, sem encheção de linguiça.\n"
            f"2. PROFUNDIDADE: Se a notícia não tiver profundidade jornalística (ex: apenas listar elenco de filme, ou repetir o título duas vezes), retorne EXATAMENTE: SKIP\n"
            f"3. CORTES BRUSCOS: O texto DEVE ser uma notícia completa com raciocínio finalizado. NUNCA termine de forma abrupta. Última frase fechada com ponto final.\n"
            f"4. IDIOMA E TOM: Sempre em Português Brasileiro fluente. Direto, ativo, jornalístico. Sem jargões.\n"
            f"5. CRÉDITOS: REMOVA qualquer crédito de fotógrafo, agência ou jornal (ex: ESTADÃO CONTEÚDO).\n"
            f"6. CTAs E PERGUNTAS: NUNCA faça perguntas. NUNCA termine com perguntas (ex: 'O que a ciência diz?'). NUNCA inclua frases como 'Tem alguma sugestão?'.\n"
            f"7. EMOJIS: O texto deve ser 100% formal. É ABSOLUTAMENTE PROIBIDO o uso de qualquer emoji.\n"
            f"8. TÍTULO: NÃO REPITA o título no corpo do resumo. Vá direto ao assunto.\n"
            f"9. NEWSLETTERS: NUNCA cite a existência de newsletters do site fonte (ex: 'Você receberá nossa newsletter em breve.').\n"
            f"10. PROIBIDO: 'o artigo fala', 'segundo a publicação', numeração, markdown.\n"
            f"11. CLICKBAIT: Se o título prometer uma lista (ex: '5 motivos', '3 coisas') ou fizer mistério, mas o texto não tiver o conteúdo real, retorne EXATAMENTE: SKIP\n"
            f"12. SKIP: Se a notícia NÃO pertence ao caderno {tema} ou é muito fraca, retorne EXATAMENTE: SKIP\n\n"
            f"Retorne APENAS o resumo (ou SKIP). Nada mais.\n"
        )

        prompt = (
            f"Você é um repórter sênior do All News Journal, jornal digital premium brasileiro.\n"
            f"Escreva UM resumo jornalístico COMPLETO e AUTOSSUFICIENTE para o caderno de {tema}.\n\n"
            f"O leitor NÃO vai clicar em nenhum link — o resumo é a notícia inteira.\n\n"
            f"═══════════════════════════════════════\n"
            f"DIRETRIZES EDITORIAIS — {tema.upper()}\n"
            f"═══════════════════════════════════════\n"
            f"{instrucao}\n\n"
            f"{regras_absolutas}\n"
            f"═══════════════════════════════════════\n"
            f"MANCHETE E CONTEXTO\n"
            f"═══════════════════════════════════════\n"
            f"{input_individual}"
        )

        resp_ia = chamar_claude_api(prompt)
        resumo_limpo = limpar_resumo(resp_ia) if resp_ia else ""

        # Pequena pausa para evitar rate-limit entre notícias
        if i < len(noticias_filtradas) - 1:
            time.sleep(1)

        # SKIP semântico
        if resumo_limpo.strip().upper() == "SKIP":
            print(f"      🚫 SKIP [{tema}]: {titulo_entry[:60]}")
            continue

        # ── Fallback 1: Claude reescreve contexto base ────────────────────────
        if not resumo_limpo:
            contexto_base = extrair_contexto_base(entry, max_chars=800)
            if contexto_base and len(contexto_base.split()) >= 20:
                prompt_rewrite = (
                    f"Você é um jornalista sênior. Reescreva o texto abaixo como uma "
                    f"notícia completa em Português Brasileiro.\n\n"
                    f"{regras_absolutas}\n"
                    f"Título: {titulo_entry}\n\nTexto base:\n{contexto_base}"
                )
                reescrito = chamar_claude_api(prompt_rewrite, max_tokens=512)
                if reescrito and len(reescrito.split()) >= 20:
                    resumo_limpo = limpar_resumo(reescrito)

        # ── Fallback 2: Claude gera a partir do título apenas ─────────────────
        if not resumo_limpo:
            prompt_mini = (
                f"Você é um jornalista sênior. Com base APENAS no título abaixo, "
                f"escreva um parágrafo jornalístico de 3 frases (80 a 95 palavras) "
                f"em Português Brasileiro. Escreva como fato estabelecido — sem "
                f"'provavelmente', 'deve' ou linguagem especulativa. "
                f"NUNCA termine com '...' ou '…'. Ponto final obrigatório na última frase.\n"
                f"Retorne APENAS o parágrafo.\n\n"
                f"Título: {titulo_entry}"
            )
            mini = chamar_claude_api(prompt_mini, max_tokens=512)
            if mini and len(mini.split()) >= 20:
                resumo_limpo = limpar_resumo(mini)

        # ── Fallback 3 (último recurso): contexto base limpo ─────────────────
        if not resumo_limpo:
            ctx = extrair_contexto_base(entry, max_chars=600)
            resumo_limpo = ctx if len(ctx.split()) >= 10 else titulo_entry

        img = extrair_imagem_rss(entry, tema, idx_entry=i)
        # Evita imagem duplicada dentro do mesmo caderno
        if img in imagens_usadas:
            fallback = FALLBACK_IMAGES.get(
                tema,
                "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=300&fit=crop"
            )
            img = f"{fallback}&sig={i}"
        imagens_usadas.add(img)

        # Garante que a IA não repetiu o título no começo do texto
        if resumo_limpo:
            resumo_limpo = limpar_resumo(resumo_limpo)
            resumo_limpo = remover_titulo_duplicado(titulo_entry, resumo_limpo)

        noticias_finais.append({
            "titulo": titulo_entry,
            "link":   entry.get("link", ""),
            "imagem": img,
            "resumo": resumo_limpo,
        })
        titulos_selecionados.append(titulo_entry)

    return noticias_finais if noticias_finais else None
