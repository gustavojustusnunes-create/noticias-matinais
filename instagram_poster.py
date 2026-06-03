"""
instagram_poster.py — Automação de posts no Instagram do All News Journal (v16.0)
Gera cards editoriais 1080x1350 (foto da notícia ao fundo + identidade do jornal)
e posta via instagrapi. Chamado pelo GitHub Actions (instagram.yml).

Novidades v16.0:
• Foto real da notícia ao fundo (mesma 'imagem' usada no e-mail)
• Degradê turquesa + moldura dourada + manchete Playfair creme
• Selo do caderno com numeração romana (I·MUNDO … VIII·FOFOCA)
• Legenda com a NOTÍCIA COMPLETA na descrição
• 1 post por caderno (até 8/dia), formato retrato 1080x1350
"""
import os
import sys
import time
import base64
import textwrap
from io import BytesIO
from datetime import datetime
from pathlib import Path

# =============================================================================
# --- VARIÁVEIS DE AMBIENTE ---
# =============================================================================
INSTAGRAM_USER    = os.environ.get("INSTAGRAM_USER", "")
INSTAGRAM_PASS    = os.environ.get("INSTAGRAM_PASS", "")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() == "true"
# Sessão do instagrapi (dump_settings) em base64 — gerada localmente e colada
# como secret no GitHub. Evita login completo (e challenge) no IP do Actions.
INSTAGRAM_SESSION = os.environ.get("INSTAGRAM_SESSION", "").strip()
CLAUDE_KEY        = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_KEY", "")).strip()

OUTPUT_DIR = Path(os.environ.get("INSTAGRAM_OUTPUT_DIR", "/tmp/instagram_posts"))
FONTS_DIR  = Path(__file__).parent / "fonts"

# Limite e espaçamento dos posts
MAX_POSTS_DIA   = 8     # 1 por caderno
ESPERA_ENTRE    = 180   # 3 min entre posts (anti-bloqueio)
FORMATO         = (1080, 1350)  # retrato

# =============================================================================
# --- DEPENDÊNCIAS OPCIONAIS ---
# =============================================================================
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠️ Pillow não instalado. Imagens não serão geradas.")

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
# --- IDENTIDADE VISUAL DA MARCA ---
# =============================================================================
TURQUESA      = (10, 92, 90)     # #0a5c5a
TURQUESA_DARK = (8, 60, 58)      # #083c3a
CREME         = (253, 251, 247)  # #fdfbf7
OURO          = (201, 168, 76)   # #c9a84c
OURO_CLARO    = (214, 184, 102)

# Numeração editorial (igual ao card "Oito Cadernos")
NUM_CADERNO = {
    "Mundo": "I", "Economia": "II", "Politica": "III", "IA": "IV",
    "Wellness": "V", "Ciencia": "VI", "Cinema": "VII", "Fofoca": "VIII",
}
NOME_EXIBICAO = {
    "Politica": "POLÍTICA",
    "IA": "INTELIGÊNCIA ARTIFICIAL",
    "Ciencia": "CIÊNCIA",
}
ICONES_TEMA = {
    "Mundo": "🌎", "Economia": "📈", "Politica": "🏛️", "IA": "🤖",
    "Wellness": "🏃", "Ciencia": "🔬", "Cinema": "🎬", "Fofoca": "⭐",
}
HASHTAGS_TEMA = {
    "Mundo":    "#noticias #mundo #geopolitica #internacional #atualidades",
    "Economia": "#economia #mercado #investimentos #bolsa #financas",
    "Politica": "#politica #brasil #congresso #governo #democracia",
    "IA":       "#ia #inteligenciaartificial #ai #tecnologia #inovacao",
    "Wellness": "#wellness #corrida #treino #saude #performance",
    "Ciencia":  "#ciencia #pesquisa #descoberta #conhecimento #science",
    "Cinema":   "#cinema #filmes #series #streaming #cultura",
    "Fofoca":   "#celebridades #hollywood #famosos #popculture #entretenimento",
}

MESES_ABREV = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# =============================================================================
# --- FONTES (Playfair Display + Lora; fallback no sistema) ---
# =============================================================================
def _font(arquivo_marca, tamanho, weight=None, serif_fallbacks=None):
    """Carrega fonte da pasta fonts/; se não houver, cai em fontes do sistema."""
    caminho = FONTS_DIR / arquivo_marca
    if caminho.exists():
        try:
            f = ImageFont.truetype(str(caminho), tamanho)
            if weight is not None:
                try:
                    f.set_variation_by_axes([weight])
                except Exception:
                    pass
            return f
        except Exception:
            pass
    # Fallback do sistema
    fallbacks = serif_fallbacks or [
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]
    for fb in fallbacks:
        if os.path.exists(fb):
            try:
                return ImageFont.truetype(fb, tamanho)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=tamanho)
    except Exception:
        return ImageFont.load_default()

def _playfair(tamanho, weight=800):
    return _font("PlayfairDisplay.ttf", tamanho, weight=weight)

def _lora(tamanho, weight=500):
    return _font("Lora.ttf", tamanho, weight=weight)

def _texto_espacado(draw, xy, texto, font, fill, tracking=0):
    """Desenha texto com espaçamento entre letras (tracking). Retorna largura total."""
    x, y = xy
    larguras = [draw.textlength(ch, font=font) for ch in texto]
    for ch, w in zip(texto, larguras):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return sum(larguras) + tracking * max(0, len(texto) - 1)

# =============================================================================
# --- IMAGEM DE FUNDO ---
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
    """Preenche (w x h) mantendo proporção (estilo CSS background-size: cover)."""
    sr, dr = img.width / img.height, w / h
    if sr > dr:
        nw, nh = int(h * sr), h
    else:
        nw, nh = w, int(w / sr)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))

# =============================================================================
# --- GERAÇÃO DO CARD EDITORIAL ---
# =============================================================================
def gerar_imagem_post(tema, titulo, data_str, imagem_url=None):
    """Gera o card editorial 1080x1350. Retorna o Path do .jpg ou None."""
    if not PIL_OK:
        return None
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    W, H = FORMATO

    # 1) Fundo: foto real da notícia (ou turquesa sólido se falhar)
    foto = _baixar_imagem(imagem_url)
    canvas = (_cover(foto, W, H) if foto else Image.new("RGB", (W, H), TURQUESA_DARK)).convert("RGB")

    # 2) Degradê turquesa (leve no topo, forte na base)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    base_rgb = tuple(int(c * 0.55) for c in TURQUESA_DARK)
    for y in range(H):
        t = y / H
        alpha = int(255 * (0.12 + 0.86 * (t ** 1.6)))
        gd.line([(0, y), (W, y)], fill=(*base_rgb, alpha))
    topo = int(H * 0.20)
    for y in range(topo):
        a = int(150 * (1 - y / topo))
        gd.line([(0, y), (W, y)], fill=(*TURQUESA_DARK, a))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # 3) Moldura dourada dupla
    m = 34
    draw.rectangle([m, m, W - m, H - m], outline=OURO, width=2)
    draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=OURO_CLARO, width=1)

    px = 70  # margem interna do texto

    # 4) Cabeçalho: masthead + data
    _texto_espacado(draw, (px, 64), "ALL NEWS JOURNAL", _lora(25, 600), CREME, tracking=6)
    draw.line([(px, 104), (px + 168, 104)], fill=OURO, width=2)
    f_data = _lora(21, 500)
    dw = draw.textlength(data_str, font=f_data)
    draw.text((W - px - dw, 66), data_str, font=f_data, fill=CREME)

    # 5) Manchete (Playfair creme) — tamanho adaptativo
    linhas = textwrap.wrap(titulo, width=16)
    if len(linhas) <= 3:
        f_titulo, lh = _playfair(78), 88
    elif len(linhas) == 4:
        f_titulo, lh = _playfair(64), 74
    else:
        f_titulo = _playfair(54)
        linhas = textwrap.wrap(titulo, width=20)[:5]
        lh = 64
    altura_manchete = lh * len(linhas)
    y_rodape = H - 88
    y_titulo = (y_rodape - 80) - altura_manchete

    # selo do caderno acima da manchete
    nome = NOME_EXIBICAO.get(tema, tema.upper())
    num  = NUM_CADERNO.get(tema, "")
    selo = f"{num} · {nome}" if num else nome
    draw.line([(px, y_titulo - 40), (px + 54, y_titulo - 40)], fill=OURO, width=3)
    _texto_espacado(draw, (px, y_titulo - 30), selo, _lora(24, 700), OURO_CLARO, tracking=4)

    y = y_titulo
    for ln in linhas:
        draw.text((px, y), ln, font=f_titulo, fill=CREME)
        y += lh

    # 6) Rodapé
    draw.line([(px, y_rodape - 18), (W - px, y_rodape - 18)], fill=OURO, width=1)
    _texto_espacado(draw, (px, y_rodape), "@ALLNEWS_JOURNAL", _lora(22, 500), OURO_CLARO, tracking=3)
    direita = "CURADORIA PREMIUM"
    f_r = _lora(20, 500)
    larg = sum(draw.textlength(c, font=f_r) for c in direita) + 3 * (len(direita) - 1)
    _texto_espacado(draw, (W - px - larg, y_rodape + 1), direita, f_r, CREME, tracking=3)

    # 7) Salva
    nome_arquivo = OUTPUT_DIR / f"{tema.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    canvas.save(str(nome_arquivo), "JPEG", quality=92)
    print(f"   🖼️  Card gerado: {nome_arquivo}")
    return nome_arquivo

# =============================================================================
# --- LEGENDA (NOTÍCIA COMPLETA NA DESCRIÇÃO) ---
# =============================================================================
def gerar_legenda(tema, titulo, resumo):
    icone = ICONES_TEMA.get(tema, "📰")
    nome  = NOME_EXIBICAO.get(tema, tema.upper())
    tags  = HASHTAGS_TEMA.get(tema, "#noticias #brasil")
    return (
        f"{icone}  {nome}\n\n"
        f"{titulo.upper()}\n\n"
        f"{resumo}\n\n"
        f"— — —\n"
        f"📩  A edição completa chega todas as manhãs no seu e-mail.\n"
        f"Assine grátis no link da bio.\n\n"
        f"{tags}\n"
        f"@allnews_journal"
    )

# =============================================================================
# --- PUBLICAÇÃO NO INSTAGRAM ---
# =============================================================================
SESSION_FILE = Path("session.json")

def _materializar_sessao_do_secret():
    """Se INSTAGRAM_SESSION (base64 do dump_settings) estiver definido e não
    houver session.json local, escreve o arquivo a partir do secret. É isso
    que permite ao GitHub Actions reaproveitar a sessão gerada localmente,
    evitando login completo (e o challenge) no IP do datacenter."""
    if SESSION_FILE.exists() or not INSTAGRAM_SESSION:
        return
    try:
        SESSION_FILE.write_bytes(base64.b64decode(INSTAGRAM_SESSION))
        print("   🔑 Sessão restaurada a partir do secret INSTAGRAM_SESSION.")
    except Exception as e:
        print(f"   ⚠️ Não foi possível decodificar INSTAGRAM_SESSION: {e}")

def login_instagram():
    """Autentica UMA vez e retorna o client logado (ou None em falha).
    Prioriza reaproveitar a sessão salva; só faz login completo se necessário."""
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
                cl.get_timeline_feed()  # valida a sessão carregada
                print("   ✅ Sessão Instagram válida (reaproveitada).")
            except LoginRequired:
                # Sessão expirou: refaz login preservando o device (uuids),
                # o que reduz a chance de challenge.
                print("   ⚠️ Sessão expirada — refazendo login com o mesmo device.")
                uuids = cl.get_settings().get("uuids", {})
                cl = InstaClient(); cl.delay_range = [2, 5]
                cl.set_uuids(uuids)
                cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
        else:
            cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
            print("   ✅ Login completo realizado.")
        # Persiste a sessão (possivelmente renovada) para o próximo run/local.
        cl.dump_settings(str(SESSION_FILE))
        return cl
    except ChallengeRequired:
        print("   ❌ Instagram pediu verificação (challenge). Gere a sessão "
              "localmente com gerar_sessao_instagram.py e atualize o secret "
              "INSTAGRAM_SESSION.")
        return None
    except PleaseWaitFewMinutes as e:
        print(f"   ❌ Instagram pediu para aguardar: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Erro no login: {e}")
        return None

def postar_instagram(cl, caminho_imagem, legenda):
    """Faz upload de uma foto com legenda usando um client já logado."""
    try:
        cl.photo_upload(str(caminho_imagem), legenda)
        print("   ✅ Post publicado!")
        return True
    except Exception as e:
        print(f"   ❌ Erro ao publicar: {e}")
        return False

# =============================================================================
# --- COLETA DAS NOTÍCIAS (1 por caderno, com imagem) ---
# =============================================================================
def obter_noticias_para_instagram():
    """Retorna lista ordenada: [{tema, titulo, resumo, imagem}, ...] (1 por caderno)."""
    from sheets_db import conectar_banco, carregar_historico
    from feeds import processar_tema
    from config import ORDEM_CADERNOS

    _, sheet_historico, _ = conectar_banco()
    historico = carregar_historico(sheet_historico) if sheet_historico else set()

    noticias = []
    for tema in ORDEM_CADERNOS:
        try:
            resultado = processar_tema(tema, historico)
            if resultado:
                n = resultado[0]
                noticias.append({
                    "tema":   tema,
                    "titulo": n.get("titulo", ""),
                    "resumo": n.get("resumo", ""),
                    "imagem": n.get("imagem", ""),
                })
                print(f"   📂 {tema}: ok")
        except Exception as e:
            print(f"   ⚠️ {tema}: {e}")
    return noticias

# =============================================================================
# --- MAIN ---
# =============================================================================
def main():
    print("📸 All News Journal — Instagram Poster v16.0")
    print("─" * 50)

    if not INSTAGRAM_ENABLED:
        print("   ℹ️  INSTAGRAM_ENABLED=false — execução cancelada.")
        return
    if not PIL_OK:
        print("   ❌ Pillow não instalado: pip install Pillow"); sys.exit(1)

    hoje = datetime.now()
    data_str = f"{hoje.day:02d} {MESES_ABREV[hoje.month - 1]} {hoje.year}"

    noticias = obter_noticias_para_instagram()
    if not noticias:
        print("   ❌ Nenhuma notícia disponível."); return

    # Autentica UMA vez e reaproveita o client em todos os posts — bem menos
    # arriscado do que fazer login a cada publicação.
    cl = None
    if INSTAGRAM_ENABLED and INSTAGRAM_USER:
        print("\n   🔐 Autenticando no Instagram…")
        cl = login_instagram()
        if not cl:
            print("   ⚠️ Sem sessão válida — os cards serão apenas gerados, sem postar.")

    postados = 0
    for item in noticias:
        if postados >= MAX_POSTS_DIA:
            print(f"   ℹ️  Limite de {MAX_POSTS_DIA} posts atingido."); break
        tema, titulo, resumo, imagem = item["tema"], item["titulo"], item["resumo"], item["imagem"]
        if not titulo:
            continue
        print(f"\n   📰 {tema} — {titulo[:55]}…")
        caminho = gerar_imagem_post(tema, titulo, data_str, imagem_url=imagem)
        if not caminho:
            print(f"   ⚠️ Card não gerado para {tema}."); continue
        legenda = gerar_legenda(tema, titulo, resumo)
        if cl:
            if postar_instagram(cl, caminho, legenda):
                postados += 1
                if postados < MAX_POSTS_DIA:
                    print(f"   ⏳ Aguardando {ESPERA_ENTRE}s antes do próximo…")
                    time.sleep(ESPERA_ENTRE)
            else:
                print(f"   💾 Card salvo em: {caminho}")
        else:
            print(f"   💾 Card salvo em: {caminho}")
            postados += 1

    print(f"\n✅ Concluído — {postados} post(s).")
    print(f"   📁 Imagens em: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
