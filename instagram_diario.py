"""
instagram_diario.py — Carrossel e Reel diários do All News Journal (v17.0)

Módulo INDEPENDENTE do instagram_poster.py (não o importa nem altera).
Lê o snapshot da edição em edicoes/AAAA-MM-DD.json (gerado pelo
site_publisher via main.py) — nunca reprocessa feeds nem chama a API,
exceto como último recurso se não houver snapshot algum.

Uso:
    python instagram_diario.py --modo carrossel
    python instagram_diario.py --modo reel
    python instagram_diario.py --modo carrossel --dry-run   # gera, NÃO posta
"""
import os
import sys
import json
import base64
import textwrap
import argparse
import subprocess
from io import BytesIO
from datetime import datetime
from pathlib import Path

from config import (
    ORDEM_CADERNOS, HASHTAGS_TEMA,
    EDICOES_DIR, SITE_URL,
    INSTAGRAM_HANDLE, INSTAGRAM_CARROSSEL_MODO,
    REEL_SEGUNDOS_POR_SLIDE, REEL_FADE_SEGUNDOS,
    NUMERAIS_CADERNO,
)

# =============================================================================
# --- VARIÁVEIS DE AMBIENTE ---
# =============================================================================
INSTAGRAM_USER    = os.environ.get("INSTAGRAM_USER", "")
INSTAGRAM_PASS    = os.environ.get("INSTAGRAM_PASS", "")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() == "true"
# Sessão do instagrapi (dump_settings) em base64 — mesma convenção do projeto.
INSTAGRAM_SESSION = os.environ.get("INSTAGRAM_SESSION", "").strip()

# Modo de entrega (mesma convenção do instagram_poster.py):
#   "email" (padrão) → envia a mídia + legenda por email para postagem manual
#   "post"           → publica direto via instagrapi
# `or "..."` cobre o caso da Variable existir vazia no GitHub Actions.
INSTAGRAM_DELIVERY = (os.environ.get("INSTAGRAM_DELIVERY", "") or "email").strip().lower()
INSTAGRAM_EMAIL_TO = (os.environ.get("INSTAGRAM_EMAIL_TO", "") or "gustavojustusnunes@gmail.com").strip()

CARROSSEL_DIR = Path(os.environ.get("ANJ_CARROSSEL_DIR", "/tmp/anj_carrossel"))
REEL_DIR      = Path(os.environ.get("ANJ_REEL_DIR", "/tmp/anj_reel"))
FONTS_DIR     = Path(__file__).parent / "fonts"
SESSION_FILE  = Path("session.json")

FORMATO_CARROSSEL = (1080, 1350)   # retrato 4:5
FORMATO_REEL      = (1080, 1920)   # vertical 9:16
MAX_SLIDES        = 10             # limite do Instagram

# =============================================================================
# --- DEPENDÊNCIAS OPCIONAIS ---
# =============================================================================
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠️ Pillow não instalado. Mídia não será gerada.")

try:
    import requests
    REQ_OK = True
except ImportError:
    REQ_OK = False

try:
    from instagrapi import Client as InstaClient
    INSTA_OK = True
except ImportError:
    INSTA_OK = False
    print("⚠️ instagrapi não instalado. Posts não serão publicados.")

# =============================================================================
# --- IDENTIDADE VISUAL ---
# =============================================================================
TURQUESA      = (10, 92, 90)     # #0a5c5a
TURQUESA_DARK = (8, 76, 74)      # #084c4a
CREME         = (253, 251, 247)  # #fdfbf7
OURO          = (201, 168, 76)   # #c9a84c
OURO_CLARO    = (214, 184, 102)

NOME_EXIBICAO = {
    "Politica": "POLÍTICA",
    "IA": "INTELIGÊNCIA ARTIFICIAL",
    "Ciencia": "CIÊNCIA",
}

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]


# =============================================================================
# --- FONTES (cascata: TTF empacotado → sistema → default) ---
# =============================================================================
def carregar_fonte(nome, tamanho, peso=None):
    """nome: 'playfair' | 'lora'. peso: eixo de variação (400/500/700/800).
    As TTFs em fonts/ são variáveis e cobrem todos os pesos da marca."""
    arquivos = {"playfair": "PlayfairDisplay.ttf", "lora": "Lora.ttf"}
    caminho = FONTS_DIR / arquivos.get(nome, "Lora.ttf")
    if caminho.exists():
        try:
            f = ImageFont.truetype(str(caminho), tamanho)
            if peso is not None:
                try:
                    f.set_variation_by_axes([peso])
                except Exception:
                    pass
            return f
        except Exception:
            pass
    # Fallback do sistema
    for fb in [
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]:
        if os.path.exists(fb):
            try:
                return ImageFont.truetype(fb, tamanho)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=tamanho)
    except Exception:
        return ImageFont.load_default()


def _playfair(tamanho, peso=800):
    return carregar_fonte("playfair", tamanho, peso)


def _lora(tamanho, peso=500):
    return carregar_fonte("lora", tamanho, peso)


def _texto_espacado(draw, xy, texto, font, fill, tracking=0):
    """Texto com espaçamento entre letras (tracking). Retorna largura total."""
    x, y = xy
    larguras = [draw.textlength(ch, font=font) for ch in texto]
    for ch, w in zip(texto, larguras):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return sum(larguras) + tracking * max(0, len(texto) - 1)


def _largura_espacado(draw, texto, font, tracking=0):
    larguras = [draw.textlength(ch, font=font) for ch in texto]
    return sum(larguras) + tracking * max(0, len(texto) - 1)


# =============================================================================
# --- CARREGAR EDIÇÃO DO DIA ---
# =============================================================================
def carregar_edicao_do_dia():
    """Lê o snapshot de hoje; senão o mais recente; senão reprocessa feeds."""
    ed_dir = Path(EDICOES_DIR)
    hoje = datetime.now().strftime("%Y-%m-%d")

    candidato = ed_dir / f"{hoje}.json"
    if not candidato.exists():
        antigos = sorted(ed_dir.glob("????-??-??.json"), reverse=True)
        candidato = antigos[0] if antigos else None
        if candidato:
            print(f"   ℹ️  Snapshot de hoje ausente — usando o mais recente: {candidato.name}")

    if candidato and candidato.exists():
        try:
            edicao = json.loads(candidato.read_text(encoding="utf-8"))
            print(f"   📂 Edição carregada: {candidato.name} ({len(edicao.get('cadernos', {}))} cadernos)")
            return edicao
        except Exception as e:
            print(f"   ⚠️ Snapshot ilegível ({e}) — caindo no fallback de feeds.")

    # Último recurso: reprocessa os feeds (custa API — evitar)
    print("   ⚠️ Nenhum snapshot disponível — reprocessando feeds (último recurso)…")
    try:
        from feeds import processar_tema
        agora = datetime.now()
        cadernos = {}
        for tema in ORDEM_CADERNOS:
            try:
                r = processar_tema(tema, set())
                if r:
                    cadernos[tema] = r
            except Exception as e:
                print(f"   ⚠️ {tema}: {e}")
        if not cadernos:
            return None
        manchete = cadernos[next(iter(cadernos))][0].get("titulo", "")
        return {
            "data":         agora.strftime("%Y-%m-%d"),
            "data_extenso": f"{DIAS[agora.weekday()]}, {agora.day} de {MESES[agora.month - 1]} de {agora.year}",
            "editorial":    "",
            "manchete":     manchete,
            "cadernos":     cadernos,
        }
    except Exception as e:
        print(f"   ❌ Fallback de feeds falhou: {e}")
        return None


def selecionar_conteudo(edicao, modo=None):
    """Retorna (caderno_do_dia | None, [(tema, noticia), …]).
    rotativo: até 4 notícias do caderno do dia (pula p/ próximo se vazio).
    panorama: 1 notícia principal por caderno presente."""
    modo = (modo or INSTAGRAM_CARROSSEL_MODO).lower()
    cadernos = edicao.get("cadernos", {})

    if modo == "rotativo":
        dia = datetime.now().timetuple().tm_yday
        for desloc in range(len(ORDEM_CADERNOS)):
            tema = ORDEM_CADERNOS[(dia - 1 + desloc) % len(ORDEM_CADERNOS)]
            if cadernos.get(tema):
                itens = [(tema, n) for n in cadernos[tema][:4]]
                print(f"   🗓️  Caderno do dia: {tema} ({len(itens)} notícia(s))")
                return tema, itens
        return None, []

    # panorama
    itens = [(tema, cadernos[tema][0]) for tema in ORDEM_CADERNOS if cadernos.get(tema)]
    print(f"   🗞️  Panorama: {len(itens)} caderno(s) presentes")
    return None, itens[:MAX_SLIDES - 2]  # capa + CTA ocupam 2 vagas


# =============================================================================
# --- MOTOR DE SLIDES (compartilhado: carrossel 4:5 e reel 9:16) ---
# =============================================================================
def _baixar_imagem(url, timeout=12):
    if not REQ_OK or not url or not str(url).startswith("http"):
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"   ⚠️ Falha ao baixar imagem ({e}).")
    return None


def _cover(img, w, h):
    """Preenche (w×h) mantendo proporção e recortando do centro (CSS cover)."""
    sr, dr = img.width / img.height, w / h
    if sr > dr:
        nw, nh = int(h * sr), h
    else:
        nw, nh = w, int(w / sr)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _gradiente_turquesa(canvas, W, H):
    """Overlay turquesa de baixo→cima para legibilidade do texto."""
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    base = tuple(int(c * 0.55) for c in TURQUESA_DARK)
    for y in range(H):
        t = y / H
        alpha = int(255 * (0.10 + 0.88 * (t ** 1.6)))
        gd.line([(0, y), (W, y)], fill=(*base, alpha))
    topo = int(H * 0.18)
    for y in range(topo):
        a = int(140 * (1 - y / topo))
        gd.line([(0, y), (W, y)], fill=(*TURQUESA_DARK, a))
    return Image.alpha_composite(canvas.convert("RGBA"), grad).convert("RGB")


def _moldura(draw, W, H):
    """Borda dupla dourada fina da marca."""
    m = 34
    draw.rectangle([m, m, W - m, H - m], outline=OURO, width=2)
    draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=OURO_CLARO, width=1)


def _masthead(draw, W, px, data_str=""):
    _texto_espacado(draw, (px, 64), "ALL NEWS JOURNAL", _lora(25, 600), CREME, tracking=6)
    draw.line([(px, 104), (px + 168, 104)], fill=OURO, width=2)
    if data_str:
        f = _lora(21, 500)
        dw = draw.textlength(data_str, font=f)
        draw.text((W - px - dw, 66), data_str, font=f, fill=CREME)


def _rotulo_caderno(tema):
    nome = NOME_EXIBICAO.get(tema, tema.upper())
    num = NUMERAIS_CADERNO.get(tema, "")
    return f"{num} · {nome}" if num else nome


def slide_capa(W, H, data_extenso, caderno=None):
    """Capa: fundo turquesa, masthead grande centralizado, data, caderno do dia."""
    canvas = Image.new("RGB", (W, H), TURQUESA)
    draw = ImageDraw.Draw(canvas)
    _moldura(draw, W, H)

    cy = H // 2

    # Filete + rótulo superior
    f_sup = _lora(22, 600)
    sup = "EDIÇÃO DIÁRIA"
    w_sup = _largura_espacado(draw, sup, f_sup, 8)
    _texto_espacado(draw, ((W - w_sup) // 2, cy - 240), sup, f_sup, OURO_CLARO, tracking=8)

    # Masthead em 2 linhas Playfair
    f_mast = _playfair(110, 800)
    for i, linha in enumerate(["ALL NEWS", "JOURNAL"]):
        wl = draw.textlength(linha, font=f_mast)
        draw.text(((W - wl) // 2, cy - 160 + i * 122), linha, font=f_mast, fill=CREME)

    # Filete dourado central
    draw.line([(W // 2 - 90, cy + 110), (W // 2 + 90, cy + 110)], fill=OURO, width=2)

    # Data por extenso
    f_data = _lora(30, 500)
    wd = draw.textlength(data_extenso, font=f_data)
    draw.text(((W - wd) // 2, cy + 140), data_extenso, font=f_data, fill=CREME)

    # Caderno do dia (modo rotativo)
    if caderno:
        selo = _rotulo_caderno(caderno)
        f_selo = _lora(26, 700)
        ws = _largura_espacado(draw, selo, f_selo, 4)
        _texto_espacado(draw, ((W - ws) // 2, cy + 210), selo, f_selo, OURO_CLARO, tracking=4)

    # Rodapé
    f_r = _lora(20, 500)
    wr = _largura_espacado(draw, INSTAGRAM_HANDLE.upper(), f_r, 3)
    _texto_espacado(draw, ((W - wr) // 2, H - 92), INSTAGRAM_HANDLE.upper(), f_r, OURO_CLARO, tracking=3)
    return canvas


def slide_noticia(W, H, tema, noticia):
    """Notícia: foto cover + gradiente + rótulo + título Playfair + resumo Lora."""
    foto = _baixar_imagem(noticia.get("imagem", ""))
    canvas = (_cover(foto, W, H) if foto else Image.new("RGB", (W, H), TURQUESA_DARK))
    canvas = _gradiente_turquesa(canvas, W, H)
    draw = ImageDraw.Draw(canvas)
    _moldura(draw, W, H)

    px = 70
    _masthead(draw, W, px)

    # Resumo (2–3 linhas Lora) — calculado primeiro para posicionar o título
    resumo = (noticia.get("resumo") or "").strip()
    if len(resumo) > 200:
        corte = resumo[:200].rsplit(" ", 1)[0]
        resumo = corte + "…"
    linhas_resumo = textwrap.wrap(resumo, width=52)[:3] if resumo else []
    f_resumo, lh_resumo = _lora(28, 500), 38

    # Título adaptativo (máx. ~4 linhas, reticências se exceder)
    titulo = (noticia.get("titulo") or "").strip()
    linhas_t = textwrap.wrap(titulo, width=18)
    if len(linhas_t) <= 3:
        f_t, lh_t = _playfair(72, 800), 82
    else:
        f_t, lh_t = _playfair(58, 800), 68
        linhas_t = textwrap.wrap(titulo, width=22)
        if len(linhas_t) > 4:
            linhas_t = linhas_t[:4]
            linhas_t[-1] = linhas_t[-1].rstrip(".,;") + "…"

    y_rodape  = H - 88
    y_resumo  = y_rodape - 40 - (lh_resumo * len(linhas_resumo) if linhas_resumo else 0)
    y_titulo  = y_resumo - 24 - lh_t * len(linhas_t)

    # Rótulo do caderno acima do título
    selo = _rotulo_caderno(tema)
    draw.line([(px, y_titulo - 40), (px + 54, y_titulo - 40)], fill=OURO, width=3)
    _texto_espacado(draw, (px, y_titulo - 30), selo, _lora(24, 700), OURO_CLARO, tracking=4)

    y = y_titulo
    for ln in linhas_t:
        draw.text((px, y), ln, font=f_t, fill=CREME)
        y += lh_t

    y = y_resumo
    for ln in linhas_resumo:
        draw.text((px, y), ln, font=f_resumo, fill=(235, 232, 226))
        y += lh_resumo

    # Rodapé discreto
    draw.line([(px, y_rodape - 16), (W - px, y_rodape - 16)], fill=OURO, width=1)
    _texto_espacado(draw, (px, y_rodape), INSTAGRAM_HANDLE.upper(), _lora(20, 500), OURO_CLARO, tracking=3)
    return canvas


def slide_cta(W, H):
    """CTA final: fundo creme, monograma ANJ, convite para assinar."""
    canvas = Image.new("RGB", (W, H), CREME)
    draw = ImageDraw.Draw(canvas)
    m = 34
    draw.rectangle([m, m, W - m, H - m], outline=OURO, width=2)
    draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=OURO_CLARO, width=1)

    cy = H // 2

    # Monograma
    f_mono = _playfair(170, 800)
    wm = draw.textlength("ANJ", font=f_mono)
    draw.text(((W - wm) // 2, cy - 330), "ANJ", font=f_mono, fill=TURQUESA)
    draw.line([(W // 2 - 80, cy - 120), (W // 2 + 80, cy - 120)], fill=OURO, width=2)

    # Texto do convite
    f_conv = _playfair(46, 700)
    for i, linha in enumerate(["Edição completa", "toda manhã", "no seu e-mail."]):
        wl = draw.textlength(linha, font=f_conv)
        draw.text(((W - wl) // 2, cy - 60 + i * 60), linha, font=f_conv, fill=TURQUESA_DARK)

    f_sub = _lora(28, 500)
    sub = "Inscreva-se no link da bio — é gratuito."
    ws = draw.textlength(sub, font=f_sub)
    draw.text(((W - ws) // 2, cy + 150), sub, font=f_sub, fill=(90, 90, 88))

    # Domínio
    dominio = SITE_URL.replace("https://", "").replace("http://", "").rstrip("/")
    f_dom = _lora(26, 600)
    wd = _largura_espacado(draw, dominio, f_dom, 2)
    _texto_espacado(draw, ((W - wd) // 2, cy + 230), dominio, f_dom, OURO, tracking=2)

    # Rodapé
    f_r = _lora(20, 500)
    wr = _largura_espacado(draw, INSTAGRAM_HANDLE.upper(), f_r, 3)
    _texto_espacado(draw, ((W - wr) // 2, H - 92), INSTAGRAM_HANDLE.upper(), f_r, TURQUESA, tracking=3)
    return canvas


# =============================================================================
# --- CARROSSEL ---
# =============================================================================
def gerar_carrossel(edicao):
    """Gera os JPGs do carrossel em CARROSSEL_DIR. Retorna (paths, legenda)."""
    W, H = FORMATO_CARROSSEL
    CARROSSEL_DIR.mkdir(parents=True, exist_ok=True)
    for antigo in CARROSSEL_DIR.glob("*.jpg"):
        antigo.unlink()

    caderno, itens = selecionar_conteudo(edicao)
    if not itens:
        print("   ❌ Nenhuma notícia para o carrossel.")
        return [], ""

    paths = []

    capa = slide_capa(W, H, edicao.get("data_extenso", ""), caderno=caderno)
    p = CARROSSEL_DIR / "01.jpg"
    capa.save(str(p), "JPEG", quality=92)
    paths.append(p)
    print(f"   🖼️  Capa: {p}")

    for i, (tema, noticia) in enumerate(itens, start=2):
        if len(paths) >= MAX_SLIDES - 1:   # reserva a última vaga p/ CTA
            break
        img = slide_noticia(W, H, tema, noticia)
        p = CARROSSEL_DIR / f"{i:02d}.jpg"
        img.save(str(p), "JPEG", quality=92)
        paths.append(p)
        print(f"   🖼️  Slide {i:02d} [{tema}]: {noticia.get('titulo', '')[:50]}…")

    cta = slide_cta(W, H)
    p = CARROSSEL_DIR / f"{len(paths) + 1:02d}.jpg"
    cta.save(str(p), "JPEG", quality=92)
    paths.append(p)
    print(f"   🖼️  CTA: {p}")

    legenda = gerar_legenda(edicao, caderno, itens)
    return paths, legenda


def gerar_legenda(edicao, caderno, itens):
    if caderno:
        titulo_dia = f"📰 {_rotulo_caderno(caderno)} — edição de hoje"
        tags = HASHTAGS_TEMA.get(caderno, "#noticias #brasil")
    else:
        titulo_dia = "📰 O panorama de hoje, caderno a caderno"
        tags = "#noticias #atualidades #jornal #brasil #curadoria"

    manchetes = "\n".join(f"• {n.get('titulo', '')}" for _, n in itens)
    dominio = SITE_URL.replace("https://", "").rstrip("/")
    return (
        f"{titulo_dia}\n\n"
        f"{manchetes}\n\n"
        f"— — —\n"
        f"📩 Edição completa toda manhã no seu e-mail — assine no link da bio.\n"
        f"{dominio}\n\n"
        f"{tags}\n"
        f"{INSTAGRAM_HANDLE}"
    )


# =============================================================================
# --- REEL (ffmpeg) ---
# =============================================================================
def gerar_frames_reel(edicao):
    """Gera os PNGs 1080×1920 do Reel. Retorna (frames, legenda)."""
    W, H = FORMATO_REEL
    frames_dir = REEL_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for antigo in frames_dir.glob("*.png"):
        antigo.unlink()

    caderno, itens = selecionar_conteudo(edicao)
    if not itens:
        print("   ❌ Nenhuma notícia para o reel.")
        return [], ""

    frames = []
    for i, (tema, noticia) in enumerate(itens, start=1):
        img = slide_noticia(W, H, tema, noticia)
        p = frames_dir / f"f{i:02d}.png"
        img.save(str(p), "PNG")
        frames.append(p)
        print(f"   🎞️  Quadro {i:02d} [{tema}]: {noticia.get('titulo', '')[:50]}…")

    cta = slide_cta(W, H)
    p = frames_dir / f"f{len(frames):02d}.png"
    cta.save(str(p), "PNG")
    frames.append(p)

    legenda = gerar_legenda(edicao, caderno, itens)
    return frames, legenda


def montar_reel(frames, data_iso):
    """Monta o MP4 com ffmpeg: fade in/out por quadro + áudio silencioso AAC."""
    dur, fade = REEL_SEGUNDOS_POR_SLIDE, REEL_FADE_SEGUNDOS
    seg_dir = REEL_DIR / "segs"
    seg_dir.mkdir(parents=True, exist_ok=True)
    for antigo in seg_dir.glob("*"):
        antigo.unlink()

    # 1) Um segmento mp4 por quadro, com fade in/out
    segs = []
    for i, png in enumerate(frames):
        seg = seg_dir / f"seg{i:02d}.mp4"
        st_out = max(0.0, dur - fade)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(png), "-t", str(dur),
            "-vf", f"fade=t=in:st=0:d={fade},fade=t=out:st={st_out}:d={fade},format=yuv420p",
            "-r", "30", "-c:v", "libx264", str(seg),
        ], check=True)
        segs.append(seg)

    # 2) Concatena os segmentos
    lista = seg_dir / "lista.txt"
    lista.write_text("\n".join(f"file '{s.name}'" for s in segs), encoding="utf-8")
    video_mudo = seg_dir / "video_mudo.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lista),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video_mudo),
    ], check=True, cwd=str(seg_dir))

    # 3) Faixa de áudio silenciosa AAC (Instagram exige áudio em Reels).
    #    Música protegida é PROIBIDA; trilha futura deve ser royalty-free
    #    em assets/audio/ (lida só se existir).
    saida = REEL_DIR / f"reel_{data_iso}.mp4"
    trilha = Path("assets/audio/trilha.mp3")
    if trilha.exists():
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_mudo), "-i", str(trilha),
            "-shortest", "-c:v", "copy", "-c:a", "aac", str(saida),
        ], check=True)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_mudo),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest", "-c:v", "copy", "-c:a", "aac", str(saida),
        ], check=True)

    print(f"   🎬 Reel montado: {saida}")
    return saida


# =============================================================================
# --- ENTREGA POR EMAIL (via Resend) — avaliação e postagem manual ---
# =============================================================================
def enviar_midia_por_email(arquivos, legenda, assunto):
    """Envia a mídia gerada (anexos) + legenda pronta por email via Resend,
    para o Gustavo avaliar e postar manualmente até confiar na automação."""
    if not REQ_OK:
        print("   ❌ requests indisponível — não dá para enviar email.")
        return False
    try:
        from config import RESEND_API_KEY, RESEND_FROM
    except Exception:
        RESEND_API_KEY, RESEND_FROM = "", ""
    if not RESEND_API_KEY:
        print("   ❌ RESEND_API_KEY não definido — não dá para enviar a mídia por email.")
        return False

    def _esc(t):
        return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                 .replace("\n", "<br>"))

    anexos = []
    for arq in arquivos:
        arq = Path(arq)
        try:
            anexos.append({
                "filename": arq.name,
                "content":  base64.b64encode(arq.read_bytes()).decode(),
            })
        except Exception as e:
            print(f"   ⚠️ Falha ao anexar {arq.name}: {e}")
    if not anexos:
        print("   ❌ Nenhum anexo válido — email não enviado.")
        return False

    html = (
        "<div style='max-width:640px;margin:0 auto;font-family:Arial,sans-serif;'>"
        f"<h2 style='font-family:Georgia,serif;color:#0a5c5a;'>{assunto}</h2>"
        "<p style='font-size:14px;color:#444;'>A mídia está <b>anexada</b> a este email. "
        f"Baixe os arquivos, copie a legenda abaixo e poste no <b>{INSTAGRAM_HANDLE}</b>.</p>"
        "<div style='white-space:pre-wrap;font-size:14px;color:#222;"
        "border-left:3px solid #c9a84c;padding:10px 14px;background:#faf8f4;'>"
        f"{_esc(legenda)}</div>"
        "</div>"
    )

    payload = {
        "from":        RESEND_FROM,
        "to":          [INSTAGRAM_EMAIL_TO],
        "subject":     assunto,
        "html":        html,
        "attachments": anexos,
    }
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                     "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        if 200 <= r.status_code < 300:
            print(f"   ✅ Email com {len(anexos)} anexo(s) enviado para {INSTAGRAM_EMAIL_TO}.")
            return True
        print(f"   ❌ Resend recusou (HTTP {r.status_code}): {r.text[:200]}")
        return False
    except Exception as e:
        print(f"   ❌ Falha ao enviar email: {e}")
        return False


# =============================================================================
# --- LOGIN / POSTAGEM ---
# =============================================================================
def _materializar_sessao_do_secret():
    if SESSION_FILE.exists() or not INSTAGRAM_SESSION:
        return
    try:
        SESSION_FILE.write_bytes(base64.b64decode(INSTAGRAM_SESSION))
        print("   🔑 Sessão restaurada a partir do secret INSTAGRAM_SESSION.")
    except Exception as e:
        print(f"   ⚠️ Não foi possível decodificar INSTAGRAM_SESSION: {e}")


def login_instagram():
    """Autentica UMA vez e retorna o client (ou None). Reaproveita sessão."""
    if not INSTA_OK:
        print("   ❌ instagrapi não disponível.")
        return None
    if not INSTAGRAM_USER or not INSTAGRAM_PASS:
        print("   ❌ INSTAGRAM_USER ou INSTAGRAM_PASS não definidos.")
        return None

    try:
        from instagrapi.exceptions import ChallengeRequired, LoginRequired, PleaseWaitFewMinutes
    except ImportError:
        ChallengeRequired = LoginRequired = PleaseWaitFewMinutes = Exception

    _materializar_sessao_do_secret()

    cl = InstaClient()
    cl.delay_range = [2, 5]
    try:
        if SESSION_FILE.exists():
            cl.load_settings(str(SESSION_FILE))
            cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
            try:
                cl.get_timeline_feed()
                print("   ✅ Sessão Instagram válida (reaproveitada).")
            except LoginRequired:
                print("   ⚠️ Sessão expirada — refazendo login com o mesmo device.")
                uuids = cl.get_settings().get("uuids", {})
                cl = InstaClient(); cl.delay_range = [2, 5]
                cl.set_uuids(uuids)
                cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
        else:
            cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
            print("   ✅ Login completo realizado.")
        cl.dump_settings(str(SESSION_FILE))
        return cl
    except ChallengeRequired:
        print("   ❌ Instagram pediu verificação (challenge). Gere a sessão "
              "localmente e atualize o secret INSTAGRAM_SESSION.")
        return None
    except PleaseWaitFewMinutes as e:
        print(f"   ❌ Instagram pediu para aguardar: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Erro no login: {e}")
        return None


# =============================================================================
# --- MAIN ---
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Carrossel e Reel diários do ANJ")
    parser.add_argument("--modo", choices=["carrossel", "reel"], required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="Gera a mídia mas NÃO posta")
    args = parser.parse_args()

    print(f"📸 All News Journal — Instagram Diário v17.0 (modo: {args.modo})")
    print("─" * 55)

    if not PIL_OK:
        print("   ❌ Pillow não instalado: pip install -r requirements-instagram.txt")
        sys.exit(1)

    edicao = carregar_edicao_do_dia()
    if not edicao:
        print("   ❌ Nenhuma edição disponível. Abortando.")
        sys.exit(1)

    if args.dry_run:
        print("   🧪 Modo --dry-run: gera mídia, não entrega.")
    elif not INSTAGRAM_ENABLED:
        print("   ℹ️  INSTAGRAM_ENABLED=false — gerando mídia sem entregar.")
    elif INSTAGRAM_DELIVERY == "post":
        print("   📤 Entrega: postagem direta via instagrapi.")
    else:
        print(f"   ✉️  Entrega: por email para {INSTAGRAM_EMAIL_TO} (postagem manual).")

    if args.modo == "carrossel":
        paths, legenda = gerar_carrossel(edicao)
        if not paths:
            sys.exit(1)
        print(f"\n   📋 Legenda:\n{legenda}\n")
        assunto = "📸 Carrossel de hoje — All News Journal"

        if args.dry_run or not INSTAGRAM_ENABLED:
            print(f"   💾 {len(paths)} slide(s) em {CARROSSEL_DIR}")
        elif INSTAGRAM_DELIVERY == "post":
            cl = login_instagram()
            if cl:
                try:
                    cl.album_upload([Path(p) for p in paths], legenda)
                    print(f"   ✅ Carrossel publicado ({len(paths)} slides)!")
                except Exception as e:
                    print(f"   ❌ Erro ao publicar carrossel: {e}")
                    sys.exit(1)
            else:
                print("   ⚠️ Login falhou — enviando por email como fallback.")
                enviar_midia_por_email(paths, legenda, assunto)
        else:
            enviar_midia_por_email(paths, legenda, assunto)

    else:  # reel
        frames, legenda = gerar_frames_reel(edicao)
        if not frames:
            sys.exit(1)
        try:
            mp4 = montar_reel(frames, edicao.get("data", datetime.now().strftime("%Y-%m-%d")))
        except FileNotFoundError:
            print("   ❌ ffmpeg não encontrado no sistema."); sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"   ❌ ffmpeg falhou: {e}"); sys.exit(1)
        print(f"\n   📋 Legenda:\n{legenda}\n")
        assunto = "🎬 Reel de hoje — All News Journal"

        if args.dry_run or not INSTAGRAM_ENABLED:
            print(f"   💾 Reel em {mp4}")
        elif INSTAGRAM_DELIVERY == "post":
            cl = login_instagram()
            if cl:
                try:
                    cl.clip_upload(Path(mp4), legenda)
                    print("   ✅ Reel publicado!")
                except Exception as e:
                    print(f"   ❌ Erro ao publicar reel: {e}")
                    sys.exit(1)
            else:
                print("   ⚠️ Login falhou — enviando por email como fallback.")
                enviar_midia_por_email([mp4], legenda, assunto)
        else:
            enviar_midia_por_email([mp4], legenda, assunto)

    print("\n✅ Concluído.")


if __name__ == "__main__":
    main()
