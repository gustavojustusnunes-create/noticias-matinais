"""
feeds.py — Coleta, filtro e processamento de feeds RSS do All News Journal
Inclui: busca de imagem, filtros de conteúdo, deduplicação e pipeline completo por tema.
"""
import re

import feedparser
import requests

from config import (
    RSS_FEEDS, FILTROS_TEMA, INSTRUCAO_TEMA,
    FALLBACK_IMAGES, FALLBACK_ESPORTES_GENERIC,
    SPORT_ROTATIONS, SPORT_KEYWORDS,
    PALAVRAS_FUTEBOL, PALAVRAS_ESPORTES_PRIORITY,
    FEEDS_INGLES,
)
from claude_api import (
    chamar_claude_api, chamar_claude_haiku,
    extrair_contexto_base, limpar_resumo,
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
        if tema == "Esportes":
            titulo    = entry.get("title", "").lower()
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
# --- FILTROS E DEDUPLICAÇÃO ---
# =============================================================================
def aplicar_filtros(entry, tema):
    """Filtra artigos por palavras-chave no título, link e corpo do artigo."""
    palavras = FILTROS_TEMA.get(tema, [])
    if not palavras:
        return True
    titulo = entry.get("title", "").lower()
    link   = entry.get("link",  "").lower()
    corpo  = extrair_contexto_base(entry, max_chars=400).lower()
    return not any(p in titulo or p in link or p in corpo for p in palavras)


def e_futebol(entry):
    texto = (entry.get("title", "") + " " + entry.get("link", "")).lower()
    return any(p in texto for p in PALAVRAS_FUTEBOL)


def e_esporte_prioritario(entry):
    texto = (entry.get("title", "") + " " + entry.get("link", "")).lower()
    return any(p in texto for p in PALAVRAS_ESPORTES_PRIORITY)


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
def coletar_entries_esportes():
    """Coleta entries de todos os feeds de Esportes, rastreando status."""
    todas, vistos = [], set()
    for url in RSS_FEEDS["Esportes"]:
        try:
            feed = feedparser.parse(url)
            count = 0
            for e in feed.entries:
                link = e.get("link", "")
                if link not in vistos:
                    vistos.add(link)
                    e._fonte_url = url
                    todas.append(e)
                    count += 1
            FEEDS_STATUS[url] = f"ok ({count} entries)"
        except Exception as ex:
            FEEDS_STATUS[url] = f"falha: {ex}"
            print(f"      ⚠️ Esportes ({url}): {ex}")
    return todas


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


# =============================================================================
# --- PIPELINE PRINCIPAL ---
# =============================================================================
def processar_tema(tema, historico_hashes):
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

    TEMAS_MULTI_FONTE = {"Esportes", "Cinema", "Fitness", "Ciencia", "Motos", "Fofoca"}

    # ── Coleta ──────────────────────────────────────────────────────────────
    if tema == "Esportes":
        valid_entries = coletar_entries_esportes()
    elif tema in TEMAS_MULTI_FONTE:
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
        print(
            f"      🏎️  F1/NBA={sum(1 for e in candidatas if e_esporte_prioritario(e))} "
            f"| Outros={sum(1 for e in candidatas if not e_futebol(e) and not e_esporte_prioritario(e))} "
            f"| Fut={sum(1 for e in candidatas if e_futebol(e))}"
        )

    # ── Ranking de relevância ────────────────────────────────────────────────
    candidatas = rankear_por_relevancia(candidatas, tema)

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

    instrucao = INSTRUCAO_TEMA.get(tema, "Inclua dados, números e contexto relevantes.")

    # ── Gera uma notícia por vez (sem batch) ─────────────────────────────────
    noticias_finais = []

    for i, entry in enumerate(noticias_filtradas):
        # ── Tradução de título ────────────────────────────────────────────────
        titulo_original = entry.get("title", "")
        e_ingles = _e_feed_ingles(entry)

        # Fitness: usa também detecção vocabular como fallback da URL
        if not e_ingles and tema == "Fitness":
            e_ingles = _titulo_parece_ingles(titulo_original)

        if e_ingles:
            titulo_traduzido = _traduzir_titulo(titulo_original)
            entry.title = titulo_traduzido
            entry._titulo_original_en = titulo_original
        else:
            titulo_traduzido = titulo_original

        titulo_entry = titulo_traduzido

        # ── Contexto base ─────────────────────────────────────────────────────
        contexto = extrair_contexto_base(entry, max_chars=800)

        aviso_ingles = ""
        if e_ingles:
            aviso_ingles = (
                f"ATENÇÃO: O texto base abaixo pode estar em INGLÊS. "
                f"O resumo DEVE ser 100% em Português Brasileiro.\n"
                f"Título original em inglês: {titulo_original}\n"
            )

        if contexto and contexto.lower() != titulo_entry.lower():
            input_individual = (
                f"Título: {titulo_entry}\n"
                f"{aviso_ingles}"
                f"Texto Base: {contexto}"
            )
        else:
            input_individual = f"Título: {titulo_entry}\n{aviso_ingles}"

        # ── Prompt individual ─────────────────────────────────────────────────
        prompt = (
            f"Você é um repórter sênior do All News Journal, jornal digital premium brasileiro.\n"
            f"Escreva UM resumo jornalístico COMPLETO e AUTOSSUFICIENTE para o caderno de {tema}.\n\n"
            f"O leitor NÃO vai clicar em nenhum link — o resumo é a notícia inteira.\n\n"
            f"═══════════════════════════════════════\n"
            f"DIRETRIZES EDITORIAIS — {tema.upper()}\n"
            f"═══════════════════════════════════════\n"
            f"{instrucao}\n\n"
            f"═══════════════════════════════════════\n"
            f"REGRAS ABSOLUTAS DE FORMATO\n"
            f"═══════════════════════════════════════\n"
            f"1. TAMANHO: 85 a 105 palavras. Abaixo de 70 = REPROVADO.\n"
            f"2. CONCLUSÃO: NUNCA termine com '…' ou '...'. Última frase fechada com ponto final.\n"
            f"3. IDIOMA: Sempre em Português Brasileiro fluente. Mesmo que o texto base esteja em inglês.\n"
            f"4. TOM: Direto, ativo, jornalístico. Sem jargões. Sem linguagem de teaser.\n"
            f"5. PROIBIDO: 'o artigo fala', 'a notícia informa', 'segundo a publicação', 'vale destacar'.\n"
            f"6. PROIBIDO: numeração, markdown (asteriscos, negrito, bullets).\n"
            f"7. INÍCIO: Comece sempre pelo fato principal com dados concretos.\n"
            f"Retorne APENAS o parágrafo de resumo, sem qualquer marcação.\n\n"
            f"═══════════════════════════════════════\n"
            f"MANCHETE E CONTEXTO\n"
            f"═══════════════════════════════════════\n"
            f"{input_individual}"
        )

        resp_ia = chamar_claude_api(prompt)
        resumo_limpo = limpar_resumo(resp_ia) if resp_ia else ""

        # SKIP semântico
        if resumo_limpo.strip().upper() == "SKIP":
            print(f"      🚫 SKIP [{tema}]: {titulo_entry[:60]}")
            continue

        # ── Fallback 1: Claude reescreve contexto base ────────────────────────
        if not resumo_limpo:
            contexto_base = extrair_contexto_base(entry, max_chars=800)
            if contexto_base and len(contexto_base.split()) >= 20:
                idioma_hint = (
                    "O texto base pode estar em inglês. "
                    "O resumo DEVE ser escrito em Português Brasileiro fluente."
                ) if e_ingles else ""
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
            ) if e_ingles else ""
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

        # ── Fallback 3 (último recurso): contexto base limpo ─────────────────
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
