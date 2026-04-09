"""
instagram_poster.py — Automação de posts no Instagram do All News Journal
Gera imagens 1080x1080 com Pillow e posta via instagrapi.
Pode ser chamado independentemente pelo GitHub Actions (instagram.yml).
"""
import os
import sys
import time
import textwrap
from datetime import datetime
from pathlib import Path

# =============================================================================
# --- VARIÁVEIS DE AMBIENTE ---
# =============================================================================
INSTAGRAM_USER    = os.environ.get("INSTAGRAM_USER", "")
INSTAGRAM_PASS    = os.environ.get("INSTAGRAM_PASS", "")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() == "true"
CLAUDE_KEY        = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_KEY", "")).strip()

# Pasta de saída para as imagens geradas
OUTPUT_DIR = Path(os.environ.get("INSTAGRAM_OUTPUT_DIR", "/tmp/instagram_posts"))

# =============================================================================
# --- DEPENDÊNCIAS OPCIONAIS ---
# =============================================================================
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠️ Pillow não instalado. Imagens não serão geradas.")

try:
    from instagrapi import Client as InstaClient
    INSTA_OK = True
except ImportError:
    INSTA_OK = False
    print("⚠️ instagrapi não instalado. Posts não serão publicados.")

# =============================================================================
# --- CONSTANTES ---
# =============================================================================
from config import CORES_TEMA, ICONES_TEMA, HASHTAGS_TEMA


def _hex_to_rgb(hex_color: str) -> tuple:
    """Converte cor hex (sem #) para tupla RGB."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _cor_texto_contraste(cor_fundo_rgb: tuple) -> tuple:
    """Retorna branco ou preto dependendo do brilho do fundo."""
    r, g, b = cor_fundo_rgb
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (255, 255, 255) if luminancia < 128 else (20, 20, 20)


def _buscar_fonte(tamanho: int, negrito: bool = False):
    """Tenta encontrar uma fonte TTF no sistema. Usa PIL default se não achar."""
    candidatas = []
    if negrito:
        candidatas = [
            "C:/Windows/Fonts/georgiab.ttf",   # Georgia Bold (Windows)
            "C:/Windows/Fonts/timesbd.ttf",    # Times New Roman Bold
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ]
    else:
        candidatas = [
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        ]
    for caminho in candidatas:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except Exception:
                continue
    # Fallback: fonte padrão do PIL (sem arquivo TTF)
    try:
        return ImageFont.load_default(size=tamanho)
    except Exception:
        return ImageFont.load_default()


# =============================================================================
# --- GERAÇÃO DA IMAGEM ---
# =============================================================================
def gerar_imagem_post(tema: str, titulo: str, data_str: str) -> Path | None:
    """
    Gera imagem 1080x1080 para post no Instagram.
    Retorna o caminho do arquivo salvo, ou None em caso de erro.
    """
    if not PIL_OK:
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cor_hex = CORES_TEMA.get(tema, "0a5c5a")
    icone   = ICONES_TEMA.get(tema, "📰")
    cor_rgb = _hex_to_rgb(cor_hex)
    cor_clara = tuple(min(255, int(c * 1.35)) for c in cor_rgb)
    cor_texto = _cor_texto_contraste(cor_rgb)

    img  = Image.new("RGB", (1080, 1080), color=cor_rgb)
    draw = ImageDraw.Draw(img)

    # ── Gradiente sutil (simulado com retângulos com opacidade) ──────────────
    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for i in range(540):
        alpha = int(40 * (i / 540))
        draw_ov.line([(0, i), (1080, i)], fill=(*cor_clara, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Faixa superior escura ────────────────────────────────────────────────
    faixa_cor = tuple(max(0, int(c * 0.6)) for c in cor_rgb)
    draw.rectangle([(0, 0), (1080, 120)], fill=faixa_cor)

    # ── Logo "ALL NEWS JOURNAL" ──────────────────────────────────────────────
    fonte_logo = _buscar_fonte(38, negrito=True)
    draw.text((54, 38), "ALL NEWS JOURNAL", font=fonte_logo, fill=(255, 255, 255))

    # ── Ícone + Nome do caderno ──────────────────────────────────────────────
    fonte_caderno = _buscar_fonte(52, negrito=True)
    caderno_txt   = f"{icone}  {tema.upper()}"
    draw.text((54, 160), caderno_txt, font=fonte_caderno, fill=cor_texto)

    # ── Linha divisória ──────────────────────────────────────────────────────
    draw.rectangle([(54, 240), (1026, 246)], fill=(*_cor_texto_contraste(cor_rgb), 80))

    # ── Título da notícia (quebra de linha automática) ───────────────────────
    fonte_titulo  = _buscar_fonte(58, negrito=True)
    fonte_titulo2 = _buscar_fonte(48, negrito=True)
    linhas = textwrap.wrap(titulo, width=24)
    if len(linhas) > 4:
        linhas = linhas[:4]
        linhas[-1] = linhas[-1][:20] + "…"

    y_titulo = 290
    fonte_usar = fonte_titulo if len(linhas) <= 3 else fonte_titulo2
    for linha in linhas:
        draw.text((54, y_titulo), linha, font=fonte_usar, fill=cor_texto)
        y_titulo += 85

    # ── Rodapé ───────────────────────────────────────────────────────────────
    draw.rectangle([(0, 980), (1080, 1080)], fill=faixa_cor)
    fonte_rodape = _buscar_fonte(30)
    draw.text((54, 1012), f"@allnewsjournal  ·  {data_str}", font=fonte_rodape, fill=(220, 220, 220))

    # ── Salva ─────────────────────────────────────────────────────────────────
    nome_arquivo = OUTPUT_DIR / f"{tema.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(str(nome_arquivo), "JPEG", quality=92)
    print(f"   🖼️  Imagem gerada: {nome_arquivo}")
    return nome_arquivo


# =============================================================================
# --- GERAÇÃO DA LEGENDA ---
# =============================================================================
def gerar_legenda(tema: str, titulo: str, resumo: str) -> str:
    """Monta a legenda completa para o post no Instagram."""
    icone   = ICONES_TEMA.get(tema, "📰")
    hashtags = HASHTAGS_TEMA.get(tema, "#noticias #brasil")
    legenda = (
        f"{icone} {tema.upper()}\n\n"
        f"{titulo}\n\n"
        f"{resumo}\n\n"
        f"—\n"
        f"{hashtags}\n"
        f"📰 Link na bio | @allnewsjournal"
    )
    return legenda


# =============================================================================
# --- PUBLICAÇÃO NO INSTAGRAM ---
# =============================================================================
def postar_instagram(caminho_imagem: Path, legenda: str) -> bool:
    """
    Faz upload da imagem com legenda no Instagram.
    Retorna True em caso de sucesso, False caso contrário.
    """
    if not INSTA_OK:
        print("   ❌ instagrapi não disponível.")
        return False

    if not INSTAGRAM_USER or not INSTAGRAM_PASS:
        print("   ❌ INSTAGRAM_USER ou INSTAGRAM_PASS não definidos.")
        return False

    try:
        cl = InstaClient()
        cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
        print("   ✅ Login Instagram OK.")

        cl.photo_upload(str(caminho_imagem), legenda)
        print("   ✅ Post publicado com sucesso!")
        return True

    except Exception as e:
        err = str(e).lower()
        if "challenge" in err or "2fa" in err or "two_factor" in err:
            print(f"   ⚠️ Autenticação em duas etapas necessária: {e}")
        elif "rate" in err or "spam" in err:
            print(f"   ⚠️ Rate limit detectado: {e}")
        else:
            print(f"   ❌ Erro ao postar: {e}")
        return False


# =============================================================================
# --- COLETA DE NOTÍCIAS DO CACHE / GOOGLE SHEETS ---
# =============================================================================
def obter_noticias_para_instagram():
    """
    Tenta coletar as notícias do dia via processamento direto dos feeds.
    Retorna dict: {tema: {"titulo": ..., "resumo": ...}}
    """
    from sheets_db import conectar_banco, carregar_historico
    from feeds import processar_tema

    sheet_usuarios, sheet_historico, _ = conectar_banco()
    if not sheet_historico:
        print("   ❌ Não foi possível conectar ao banco.")
        return {}

    historico_hashes = carregar_historico(sheet_historico)
    noticias = {}

    from config import RSS_FEEDS
    for tema in RSS_FEEDS:
        try:
            resultado = processar_tema(tema, historico_hashes)
            if resultado:
                primeira = resultado[0]
                noticias[tema] = {
                    "titulo": primeira.get("titulo", ""),
                    "resumo": primeira.get("resumo", ""),
                }
                print(f"   📂 {tema}: notícia obtida.")
        except Exception as e:
            print(f"   ⚠️ {tema}: {e}")

    return noticias


# =============================================================================
# --- MAIN ---
# =============================================================================
def main():
    print("📸 All News Journal — Instagram Poster")
    print("─" * 50)

    if not INSTAGRAM_ENABLED:
        print("   ℹ️  INSTAGRAM_ENABLED=false — execução cancelada.")
        print("   ℹ️  Para ativar, defina INSTAGRAM_ENABLED=true nas variáveis de ambiente.")
        return

    if not PIL_OK:
        print("   ❌ Pillow não instalado. Execute: pip install Pillow>=10.0.0")
        sys.exit(1)

    hoje_str = datetime.now().strftime("%d/%m/%Y")
    noticias = obter_noticias_para_instagram()

    if not noticias:
        print("   ❌ Nenhuma notícia disponível para postar.")
        return

    postados = 0
    max_posts = 10

    for tema, dados in noticias.items():
        if postados >= max_posts:
            print(f"   ℹ️  Limite de {max_posts} posts atingido.")
            break

        titulo = dados.get("titulo", "")
        resumo = dados.get("resumo", "")

        if not titulo:
            continue

        print(f"\n   📰 Preparando post: {tema} — {titulo[:50]}…")

        # Gera imagem
        caminho = gerar_imagem_post(tema, titulo, hoje_str)
        if not caminho:
            print(f"   ⚠️ Imagem não gerada para {tema}.")
            continue

        # Gera legenda
        legenda = gerar_legenda(tema, titulo, resumo)

        # Posta (ou salva localmente se o post falhar)
        if INSTAGRAM_ENABLED and INSTAGRAM_USER:
            ok = postar_instagram(caminho, legenda)
            if ok:
                postados += 1
                if postados < max_posts:
                    espera = 150  # 2,5 minutos entre posts
                    print(f"   ⏳ Aguardando {espera}s antes do próximo post…")
                    time.sleep(espera)
            else:
                print(f"   💾 Imagem salva em: {caminho}")
        else:
            print(f"   💾 Imagem salva em: {caminho}")
            postados += 1

    print(f"\n✅ Instagram Poster concluído — {postados} post(s) processado(s).")
    print(f"   📁 Imagens em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
