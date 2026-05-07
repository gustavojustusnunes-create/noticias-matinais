"""
All News Journal - Instagram Poster
Coleta a notícia mais relevante de cada caderno, gera imagem 1080x1080
e posta no Instagram via instagrapi.

Requer: pip install -r requirements-instagram.txt
Env vars: ANTHROPIC_API_KEY, INSTAGRAM_USER, INSTAGRAM_PASS, INSTAGRAM_ENABLED
"""

import os
import sys
import textwrap
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from config import (
    ORDEM_CADERNOS,
    RSS_FEEDS,
    ICONES_TEMA,
    CORES_TEMA,
    FILTROS_TEMA,
    INSTRUCAO_TEMA,
    HASHTAGS,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BRT = timezone(timedelta(hours=-3))
OUTPUT_DIR = Path("/tmp/instagram_posts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SESSION_FILE = BASE_DIR / "session.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("instagram")

# ---------------------------------------------------------------------------
# Coleta da notícia mais relevante de um caderno
# ---------------------------------------------------------------------------

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def should_filter(title: str, summary: str, tema: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(w in text for w in FILTROS_TEMA.get(tema, []))


def fetch_best_article(tema: str) -> dict | None:
    """Retorna o artigo mais recente e não-filtrado do tema."""
    urls = RSS_FEEDS.get(tema, [])
    cutoff = datetime.now(BRT) - timedelta(hours=48)

    for url in urls:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            source = feed.feed.get("title", url)
            for entry in feed.entries:
                title = clean_html(entry.get("title", ""))
                if not title:
                    continue
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                if should_filter(title, summary, tema):
                    continue
                # Data
                pub_date = None
                for attr in ("published_parsed", "updated_parsed"):
                    parsed = getattr(entry, attr, None)
                    if parsed:
                        from time import mktime
                        pub_date = datetime.fromtimestamp(mktime(parsed), tz=BRT)
                        break
                if pub_date and pub_date < cutoff:
                    continue
                return {
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": source,
                    "date": pub_date.strftime("%d/%m/%Y") if pub_date else datetime.now(BRT).strftime("%d/%m/%Y"),
                }
        except Exception as e:
            log.warning("Erro ao buscar feed %s: %s", url, e)
    return None

# ---------------------------------------------------------------------------
# Gerar resumo de 85-105 palavras com Claude
# ---------------------------------------------------------------------------

def generate_caption_summary(article: dict, tema: str, client: anthropic.Anthropic) -> str:
    instrucao = INSTRUCAO_TEMA.get(tema, "")
    has_summary = bool(article.get("summary", "").strip())

    base_text = article["summary"][:800] if has_summary else ""
    prompt = (
        f"Escreva um resumo de exatamente 85 a 105 palavras em portugues brasileiro "
        f"sobre esta noticia. Seja claro, direto e informativo.\n\n"
        f"INSTRUCOES EDITORIAIS:\n{instrucao}\n\n"
        f"Titulo: {article['title']}\n"
        + (f"Contexto: {base_text}" if base_text else "")
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        log.error("Erro na API Anthropic: %s", e)
        return article.get("summary", article["title"])[:400]

# ---------------------------------------------------------------------------
# Geração da imagem 1080x1080 px com Pillow
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_gradient(draw: ImageDraw.Draw, width: int, height: int, color_hex: str):
    """Gradiente vertical: cor do tema no topo, versão mais escura no rodapé."""
    r, g, b = hex_to_rgb(color_hex)
    for y in range(height):
        factor = 1.0 - (y / height) * 0.55  # escurece até 55% no rodapé
        cr = int(r * factor)
        cg = int(g * factor)
        cb = int(b * factor)
        draw.line([(0, y), (width, y)], fill=(cr, cg, cb))


def try_load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Tenta carregar uma fonte serif; usa padrão como fallback."""
    serif_paths = [
        # Linux (GitHub Actions)
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        # Windows
        "C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/timesbd.ttf" if bold else "C:/Windows/Fonts/times.ttf",
        # macOS
        "/Library/Fonts/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ]
    for path in serif_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 3) -> list[str]:
    """Quebra texto em linhas respeitando a largura máxima."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    # Truncar com reticências se necessário
    if len(lines) == max_lines and len(text.split()) > sum(len(l.split()) for l in lines):
        last = lines[-1]
        while True:
            bbox = draw.textbbox((0, 0), last + "…", font=font)
            if bbox[2] - bbox[0] <= max_width or len(last) == 0:
                break
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "…"
    return lines


def generate_image(tema: str, titulo: str, output_path: Path) -> Path:
    """Gera imagem 1080x1080 para o tema dado."""
    W, H = 1080, 1080
    cor = CORES_TEMA.get(tema, "457b9d")
    icone = ICONES_TEMA.get(tema, "📰")
    data_str = datetime.now(BRT).strftime("%d/%m/%Y")

    img = Image.new("RGB", (W, H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo gradiente
    make_gradient(draw, W, H, cor)

    # Overlay escuro no rodapé para o texto ficar legível
    overlay = Image.new("RGBA", (W, 160), (0, 0, 0, 160))
    img.paste(Image.new("RGB", (W, 160), (0, 0, 0)), (0, H - 160), overlay)

    # Fontes
    font_title_small = try_load_font(38, bold=True)
    font_caderno = try_load_font(32, bold=True)
    font_headline = try_load_font(44, bold=False)
    font_footer = try_load_font(22, bold=False)

    WHITE = (255, 255, 255)
    WHITE_70 = (255, 255, 255, 178)

    # "ALL NEWS JOURNAL" no topo
    journal_text = "ALL NEWS JOURNAL"
    bbox = draw.textbbox((0, 0), journal_text, font=font_title_small)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 60), journal_text, font=font_title_small, fill=WHITE)

    # Linha decorativa abaixo do título
    draw.rectangle([(W // 2 - 60, 115), (W // 2 + 60, 118)], fill=WHITE)

    # Nome do caderno em caps
    caderno_text = tema.upper()
    bbox = draw.textbbox((0, 0), caderno_text, font=font_caderno)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 420), caderno_text, font=font_caderno, fill=WHITE)

    # Ícone como texto acima do nome do caderno
    # Pillow não renderiza emoji bem em todos os sistemas — usa texto do caderno com um separador
    icone_placeholder = f"[ {tema} ]"
    bbox = draw.textbbox((0, 0), icone_placeholder, font=font_caderno)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 340), icone_placeholder, font=font_caderno, fill=WHITE)

    # Linha separadora
    draw.rectangle([(80, 490), (W - 80, 493)], fill=(255, 255, 255, 120))

    # Manchete (até 3 linhas, largura máxima 920px)
    lines = wrap_text(draw, titulo, font_headline, max_width=920, max_lines=3)
    total_h = len(lines) * 56
    y_start = 530
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y_start), line, font=font_headline, fill=WHITE)
        y_start += 56

    # Rodapé: data + handle
    footer_text = f"{data_str}  •  @allnews_journal"
    bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - 110), footer_text, font=font_footer, fill=(230, 230, 230))

    img.save(str(output_path), "JPEG", quality=92)
    log.info("Imagem gerada: %s", output_path)
    return output_path

# ---------------------------------------------------------------------------
# Montar legenda do Instagram
# ---------------------------------------------------------------------------

def build_caption(tema: str, titulo: str, resumo: str) -> str:
    icone = ICONES_TEMA.get(tema, "📰")
    tags = HASHTAGS.get(tema, "")
    return (
        f"{icone} {tema.upper()}\n\n"
        f"{titulo}\n\n"
        f"{resumo}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 Edição completa todas as manhãs no e-mail.\n"
        f"Inscreva-se no link da bio.\n\n"
        f"{tags}\n"
        f"@allnews_journal"
    )

# ---------------------------------------------------------------------------
# Postar no Instagram
# ---------------------------------------------------------------------------

def post_to_instagram(image_path: Path, caption: str) -> bool:
    """Posta a imagem no Instagram via instagrapi. Retorna True se OK."""
    try:
        from instagrapi import Client
        from instagrapi.exceptions import (
            ChallengeRequired,
            LoginRequired,
            PleaseWaitFewMinutes,
        )
    except ImportError:
        log.error("instagrapi não instalado. Use: pip install -r requirements-instagram.txt")
        return False

    user = os.getenv("INSTAGRAM_USER", "")
    password = os.getenv("INSTAGRAM_PASS", "")

    if not user or not password:
        log.error("INSTAGRAM_USER / INSTAGRAM_PASS não configurados.")
        return False

    cl = Client()
    cl.delay_range = [2, 5]

    # Reusar sessão salva para evitar challenges
    if SESSION_FILE.exists():
        try:
            cl.load_settings(str(SESSION_FILE))
            cl.login(user, password)
            cl.get_timeline_feed()
            log.info("Sessão Instagram restaurada com sucesso.")
        except LoginRequired:
            log.warning("Sessão expirada — fazendo login completo.")
            cl = Client()
            cl.delay_range = [2, 5]
            cl.login(user, password)
            cl.dump_settings(str(SESSION_FILE))
    else:
        try:
            cl.login(user, password)
            cl.dump_settings(str(SESSION_FILE))
            log.info("Login Instagram realizado. Sessão salva.")
        except ChallengeRequired:
            log.error("Instagram solicitou challenge (verificação). Faça login manual uma vez e tente novamente.")
            return False
        except PleaseWaitFewMinutes as e:
            log.error("Instagram pediu para aguardar: %s", e)
            return False

    try:
        media = cl.photo_upload(str(image_path), caption=caption)
        log.info("Post publicado! Media ID: %s", media.pk)
        return True
    except Exception as e:
        log.error("Erro ao publicar post: %s", e)
        return False

# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("ALL NEWS JOURNAL - Instagram Poster")
    log.info("Data: %s", datetime.now(BRT).strftime("%d/%m/%Y %H:%M"))
    log.info("=" * 60)

    instagram_enabled = os.getenv("INSTAGRAM_ENABLED", "false").lower() == "true"
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    client = None
    if api_key and not api_key.startswith("sk-ant-xxx"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            log.info("API Anthropic OK")
        except Exception as e:
            log.warning("Erro ao inicializar Anthropic: %s", e)

    resultados = []

    for tema in ORDEM_CADERNOS:
        log.info("\n--- Processando caderno: %s %s ---", ICONES_TEMA[tema], tema)

        article = fetch_best_article(tema)
        if not article:
            log.warning("Nenhuma notícia encontrada para: %s", tema)
            continue

        log.info("Notícia: %s", article["title"][:70])

        # Gerar resumo via IA
        if client:
            resumo = generate_caption_summary(article, tema, client)
        else:
            resumo = article.get("summary", article["title"])[:400]

        # Gerar imagem
        output_path = OUTPUT_DIR / f"{tema.lower()}.jpg"
        generate_image(tema, article["title"], output_path)

        # Montar legenda
        caption = build_caption(tema, article["title"], resumo)

        if instagram_enabled:
            log.info("Postando no Instagram...")
            success = post_to_instagram(output_path, caption)
            status = "postado" if success else "ERRO ao postar"
        else:
            log.info("INSTAGRAM_ENABLED=false — salvando localmente.")
            log.info("Imagem salva em: %s", output_path)
            log.info("Legenda:\n%s", caption)
            status = f"salvo em {output_path}"

        resultados.append({"tema": tema, "titulo": article["title"][:60], "status": status})

    log.info("\n" + "=" * 60)
    log.info("RESUMO FINAL")
    log.info("=" * 60)
    for r in resultados:
        log.info("  %s %s: %s", ICONES_TEMA[r["tema"]], r["tema"], r["status"])
    log.info("=" * 60)


if __name__ == "__main__":
    main()
