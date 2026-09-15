"""
instagram_poster.py — Novo formato de posts no Instagram do All News Journal (v18.0)
Gera posts em formato carrossel baseado fielmente no design padrão:
- Palavra-chave de impacto repetida 3x no topo com máscara de foto recortada dentro das letras.
- Título em Playfair Display serifado de alta legibilidade.
- Descrição jornalística em Lora de alto contraste sobre fundo escuro (#0d0d0d).
- Indicadores de carrossel no rodapé.
- Garantia de imagem (fallback temático que impede cards pretos sem foto).
- Bloqueio anti-repetição de edições.
"""
import os
import sys
import json
import time
import re
import base64
from pathlib import Path
from datetime import datetime
from io import BytesIO

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# =============================================================================
# --- VARIÁVEIS DE AMBIENTE ---
# =============================================================================
INSTAGRAM_USER    = os.environ.get("INSTAGRAM_USER", "")
INSTAGRAM_PASS    = os.environ.get("INSTAGRAM_PASS", "")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() == "true"
INSTAGRAM_SESSION = os.environ.get("INSTAGRAM_SESSION", "").strip()

INSTAGRAM_DELIVERY = (os.environ.get("INSTAGRAM_DELIVERY", "") or "email").strip().lower()
INSTAGRAM_EMAIL_TO = (os.environ.get("INSTAGRAM_EMAIL_TO", "") or "gustavojustusnunes@gmail.com").strip()

OUTPUT_DIR   = Path(os.environ.get("INSTAGRAM_OUTPUT_DIR", "/tmp/instagram_posts"))
EDICOES_DIR  = Path("edicoes")
FONTS_DIR    = Path(__file__).parent / "fonts"
SESSION_FILE = Path("session.json")
MEMORY_FILE  = Path("logs") / "supervisor_memory.json"

ESPERA_ENTRE = 180   # 3 minutos entre posts para respeitar os limites do Instagram
FORMATO      = (1080, 1350)  # retrato 4:5 oficial do Instagram
MAX_POSTS    = 5

# =============================================================================
# --- DEPENDÊNCIAS OPCIONAIS ---
# =============================================================================
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠️ Pillow não instalado.")

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
    print("⚠️ instagrapi não instalado.")

# =============================================================================
# --- IDENTIDADE VISUAL & TEMAS ---
# =============================================================================
PETROLEO_DEEP  = (12, 27, 26)       # #0C1B1A (Slide 1 vinheta petróleo profundo)
GRAFITE_ESCURO = (11, 15, 20)       # #0B0F14 (Slide 2..N fundo sólido editorial brutalista)
BRANCO_PURO    = (255, 255, 255)    # #FFFFFF
CINZA_CORPO    = (226, 232, 240)    # #E2E8F0 (Slide 2..N bloco de leitura Inter)
OURO           = (201, 168, 76)     # #C9A84C (Linhas douradas e acentos)
OURO_SUAVE     = (209, 186, 115)    # #D1BA73 (Moldura hairline, tags e marcas)
TEXTO_MUTED    = (148, 163, 184)    # #94A3B8 (Topos e indicadores)
FUNDO_ESCURO   = GRAFITE_ESCURO
CREME          = (253, 251, 247)
TEXTO_CORPO    = CINZA_CORPO
ESMERALDA      = (10, 92, 90)

ICONES_TEMA = {
    "Mundo": "🌎", "Economia": "📈", "Politica": "🏛️", "IA": "🤖",
    "Wellness": "🏃", "Ciencia": "🔬", "Cinema": "🎬", "Fofoca": "⭐",
}

HASHTAGS_TEMA = {
    "Mundo":    "#noticias #mundo #geopolitica #internacional",
    "Economia": "#economia #mercado #investimentos #financas",
    "Politica": "#politica #brasil #governo #democracia",
    "IA":       "#ia #inteligenciaartificial #tecnologia #inovacao",
    "Wellness": "#wellness #saude #performance #longevidade",
    "Ciencia":  "#ciencia #pesquisa #descoberta",
    "Cinema":   "#cinema #filmes #series #streaming",
    "Fofoca":   "#celebridades #culturapop #entretenimento",
}

FALLBACK_IMAGENS_TEMA = {
    "Mundo": [
        "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=1200&fit=crop",
    ],
    "Economia": [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=1200&fit=crop",
    ],
    "Politica": [
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=1200&fit=crop",
    ],
    "IA": [
        "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&fit=crop",
    ],
    "Wellness": [
        "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1200&fit=crop",
    ],
    "Ciencia": [
        "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=1200&fit=crop",
    ],
    "Cinema": [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=1200&fit=crop",
    ],
    "Fofoca": [
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1200&fit=crop",
        "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=1200&fit=crop",
    ],
}

from config import ORDEM_CADERNOS

# =============================================================================
# --- TIPOGRAFIA ---
# =============================================================================
def _font(arquivo_marca, tamanho, weight=None):
    caminho = FONTS_DIR / arquivo_marca
    if caminho.exists():
        try:
            f = ImageFont.truetype(str(caminho), tamanho)
            if weight is not None:
                try: f.set_variation_by_axes([weight])
                except Exception: pass
            return f
        except Exception:
            pass
    try: return ImageFont.load_default(size=tamanho)
    except: return ImageFont.load_default()

def _montserrat(tamanho):
    return _font("Montserrat-Black.ttf", tamanho)

def _playfair(tamanho, weight=700):
    return _font("PlayfairDisplay.ttf", tamanho, weight=weight)

def _lora(tamanho, weight=400):
    return _font("Lora.ttf", tamanho, weight=weight)

def _newsreader(tamanho, weight=600):
    return _font("Newsreader.ttf", tamanho, weight=weight)

def _inter(tamanho, weight=400):
    return _font("Inter.ttf", tamanho, weight=weight)

def _texto_espacado(draw, xy, texto, font, fill, tracking=0):
    """Renderiza texto com espaçamento de caracteres (tracking) refinado."""
    x, y = xy
    for char in texto:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking

def _largura_espacado(draw, texto, font, tracking=0):
    """Calcula a largura total de um texto renderizado com tracking."""
    if not texto:
        return 0
    w = sum(draw.textlength(c, font=font) for c in texto)
    return w + (len(texto) - 1) * tracking

def _quebrar_texto(draw, texto, font, max_largura):
    """Quebra texto em linhas respeitando a largura máxima disponível."""
    linhas = []
    palavras = texto.split()
    linha_atual = []
    for p in palavras:
        linha_atual.append(p)
        if draw.textlength(" ".join(linha_atual), font=font) > max_largura:
            linha_atual.pop()
            if linha_atual:
                linhas.append(" ".join(linha_atual))
            linha_atual = [p]
    if linha_atual:
        linhas.append(" ".join(linha_atual))
    return linhas

# =============================================================================
# --- MEMÓRIA DO SUPERVISOR (ANTI-REPETIÇÃO) ---
# =============================================================================
def carregar_memoria():
    if not MEMORY_FILE.exists():
        return {"erros": [], "imagens_recentes": [], "ultima_edicao_instagram": ""}
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"erros": data, "imagens_recentes": [], "ultima_edicao_instagram": ""}
        if "imagens_recentes" not in data:
            data["imagens_recentes"] = []
        if "erros" not in data:
            data["erros"] = []
        if "ultima_edicao_instagram" not in data:
            data["ultima_edicao_instagram"] = ""
        return data
    except:
        return {"erros": [], "imagens_recentes": [], "ultima_edicao_instagram": ""}

def salvar_memoria(memoria):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(memoria, indent=4, ensure_ascii=False), encoding="utf-8")

# =============================================================================
# --- PROCESSAMENTO DE IMAGEM & DESIGN ---
# =============================================================================
def _baixar_imagem(url):
    if not REQ_OK or not url or not str(url).startswith("http"):
        return None
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)).convert("RGB")
    except:
        pass
    return None

def obter_foto_garantida(url_original, tema, idx_post=0, memoria=None):
    """
    Garante que SEMPRE haverá uma imagem de alta resolução válida.
    Se a imagem do RSS falhar ou for repetida recentemente, usa fallback temático curado.
    """
    foto = None
    recentes = memoria.get("imagens_recentes", []) if memoria else []
    
    # 1. Tenta imagem original se não estiver no histórico recente
    if url_original and url_original not in recentes:
        foto = _baixar_imagem(url_original)
        if foto and memoria:
            recentes.append(url_original)
            memoria["imagens_recentes"] = recentes[-50:]
            salvar_memoria(memoria)
            
    # 2. Se falhar, recorre aos fallbacks temáticos em alta resolução
    if not foto:
        fallbacks = FALLBACK_IMAGENS_TEMA.get(tema, FALLBACK_IMAGENS_TEMA["Mundo"])
        for url_fb in fallbacks:
            foto = _baixar_imagem(url_fb)
            if foto:
                break

    # 3. Se rede falhar completamente, gera imagem de textura esmeralda elegante
    if not foto:
        W, H = FORMATO
        foto = Image.new("RGB", (W, H), (10, 92, 90))
        d = ImageDraw.Draw(foto)
        d.rectangle([0, H // 2, W, H], fill=(8, 60, 58))
        
    return foto

def _cover_sem_corte(img, w, h):
    """Fundo adaptativo centralizado sem distorção para preencher o canvas."""
    sr, dr = img.width / img.height, w / h
    if sr > dr:
        nw, nh = int(h * sr), h
    else:
        nw, nh = w, int(w / sr)
        
    img_resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img_resized.crop((left, top, left + w, top + h))

# =============================================================================
# --- EXTRAÇÃO INTELIGENTE DE PALAVRAS-CHAVE ---
# =============================================================================
STOPWORDS = {
    "SOBRE", "ENTRE", "DISSE", "QUANDO", "PORQUE", "AGORA", "DEVE", "SERA",
    "APOS", "COMO", "ONDE", "MAIS", "MENOS", "MUITO", "POUCO", "ESTA", "ESSE",
    "ESSA", "AQUELE", "AQUELA", "PARA", "PELO", "PELA", "PODE", "DIZ", "VEJA",
    "QUAL", "QUAIS", "QUEM", "NOVO", "NOVA", "NOVOS", "NOVAS", "SEGUNDO", "APENAS"
}

def extrair_keywords(titulo, resumo, tema):
    """
    Extrai as palavras de maior impacto dramático/jornalístico para os slides.
    """
    palavras = re.findall(r'\b[A-ZÁÀÂÃÉÈÊÍÏÓÒÔÕÚÜÇ]{4,}\b', titulo.upper())
    candidatas = [p for p in palavras if p not in STOPWORDS and not p.isnumeric()]
    
    # Se faltar palavras no título, busca no resumo
    if len(candidatas) < 3:
        palavras_resumo = re.findall(r'\b[A-ZÁÀÂÃÉÈÊÍÏÓÒÔÕÚÜÇ]{5,}\b', resumo.upper())
        for p in palavras_resumo:
            if p not in STOPWORDS and p not in candidatas and not p.isnumeric():
                candidatas.append(p)
            if len(candidatas) >= 4:
                break
                
    # Fallback por tema
    fallbacks_tema = {
        "Mundo": ["GEOPOLÍTICA", "ALIANÇA", "CONFLITO", "IMPACTO"],
        "Economia": ["MERCADO", "INFLAÇÃO", "JUROS", "CAPITAL"],
        "Politica": ["DECISÃO", "PODER", "CONGRESSO", "LEGISLAÇÃO"],
        "IA": ["INTELIGÊNCIA", "ALGORITMO", "FUTURO", "INOVAÇÃO"],
        "Wellness": ["PERFORMANCE", "SAÚDE", "LONGEVIDADE", "HÁBITO"],
        "Ciencia": ["DESCOBERTA", "PESQUISA", "CIÊNCIA", "AVANÇO"],
        "Cinema": ["ESTREIA", "CRÍTICA", "INDÚSTRIA", "BILHETERIA"],
        "Fofoca": ["BASTIDORES", "FAMA", "REPERCUSSÃO", "MÍDIA"]
    }
    
    defaults = fallbacks_tema.get(tema, ["NOTÍCIA", "ANÁLISE", "DESTAQUE", "ALL NEWS"])
    for d in defaults:
        if d not in candidatas:
            candidatas.append(d)
            
    return candidatas[:4]

# =============================================================================
# --- MOTOR DO NOVO DESIGN DE CARROSSEL (CAPA CLÁSSICA VS BRUTALISTA) ---
# =============================================================================
def gerar_slide_capa(tema, manchete, foto, data_str="", total_slides=3):
    """
    1. SLIDE 1 (CAPA / HOOK PRINCIPAL):
    - Estilo: Jornalístico clássico, institucional e minimalista (revista executiva).
    - Fundo: Imagem de destaque em cover com vinheta em petróleo profundo (#0C1B1A).
    - Moldura: Linha de contorno fina dourada/bege elegante (~32px de margem).
    - Header: 'ALL NEWS JOURNAL' à esquerda e data ('DD.MM.AAAA') à direita, divisória abaixo.
    - Rodapé: '@ALL.NEWS.JOURNAL' à esquerda e 'ARRASTE PARA LER' à direita, divisória acima.
    - Bloco Inferior: Tag do caderno em dourado suave com traço decorativo, manchete em Playfair Display branca direta (sem resumo explicativo).
    """
    W, H = FORMATO  # 1080 x 1350
    if foto:
        canvas = _cover_sem_corte(foto, W, H)
    else:
        canvas = Image.new("RGB", (W, H), PETROLEO_DEEP)

    # Gradiente em petróleo profundo (#0C1B1A) nas bordas superior e inferior
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)

    # 1. Gradiente superior (y = 0 até 260) para legibilidade do header
    h_top = 260
    for y in range(h_top):
        alpha = int(220 * (1 - (y / h_top) ** 1.3))
        gd.line([(0, y), (W, y)], fill=(*PETROLEO_DEEP, alpha))

    # 2. Gradiente inferior suave e profundo (y = 560 até 1350)
    h_bot_start = 560
    for y in range(h_bot_start, H):
        t = (y - h_bot_start) / (H - h_bot_start)
        alpha = int(255 * (0.10 + 0.90 * (t ** 1.4)))
        gd.line([(0, y), (W, y)], fill=(*PETROLEO_DEEP, alpha))

    canvas = Image.alpha_composite(canvas.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Moldura fina dourada/bege elegante (margem de segurança ~32px)
    m = 32
    draw.rectangle([m, m, W - m, H - m], outline=OURO_SUAVE, width=1)
    draw.rectangle([m + 5, m + 5, W - m - 5, H - m - 5], outline=OURO_SUAVE, width=1)

    px = m + 28  # margem interna ~60px

    # Header Topo: "ALL NEWS JOURNAL" à esquerda, data à direita
    y_hdr = m + 26
    f_hdr = _playfair(21, weight=700)
    _texto_espacado(draw, (px, y_hdr), "ALL NEWS JOURNAL", f_hdr, BRANCO_PURO, tracking=5)

    # Traço fino sob "ALL NEWS"
    w_brand_first = _largura_espacado(draw, "ALL NEWS", f_hdr, tracking=5)
    draw.line([(px, y_hdr + 32), (px + w_brand_first, y_hdr + 32)], fill=OURO, width=1)

    # Data à direita ("DD.MM.AAAA")
    if not data_str:
        data_str = datetime.now().strftime("%d.%m.%Y")
    f_data = _playfair(20, weight=600)
    w_data = _largura_espacado(draw, data_str, f_data, tracking=3)
    _texto_espacado(draw, (W - px - w_data, y_hdr + 1), data_str, f_data, BRANCO_PURO, tracking=3)

    # Linha divisória horizontal contínua logo abaixo do header
    draw.line([(m + 1, y_hdr + 46), (W - m - 1, y_hdr + 46)], fill=OURO_SUAVE, width=1)

    # Rodapé: separador horizontal acima do rodapé
    y_foot = H - m - 46
    draw.line([(m + 1, y_foot - 14), (W - m - 1, y_foot - 14)], fill=OURO_SUAVE, width=1)

    f_foot = _playfair(19, weight=700)
    _texto_espacado(draw, (px, y_foot), "@ALL.NEWS.JOURNAL", f_foot, OURO_SUAVE, tracking=3)

    txt_arraste = "ARRASTE PARA LER"
    f_arraste = _inter(17, weight=600)
    w_arraste = _largura_espacado(draw, txt_arraste, f_arraste, tracking=3)
    _texto_espacado(draw, (W - px - w_arraste, y_foot + 2), txt_arraste, f_arraste, BRANCO_PURO, tracking=3)

    # Dots indicadores de carrossel no rodapé da Capa (Slide 1 de N)
    if total_slides > 1:
        raio = 4
        espacamento = 20
        largura_total = (total_slides - 1) * espacamento
        x_inicio_dots = (W - largura_total) // 2
        y_dots = H - m - 14
        for s in range(total_slides):
            cx = x_inicio_dots + s * espacamento
            cor_dot = BRANCO_PURO if s == 0 else (90, 100, 100)
            draw.ellipse([cx - raio, y_dots - raio, cx + raio, y_dots + raio], fill=cor_dot)

    # Bloco Inferior de Texto
    max_w = W - 2 * px
    f_manchete = _playfair(54, weight=700)
    linhas_manchete = _quebrar_texto(draw, manchete, f_manchete, max_w)

    # Limita a manchete a 4 linhas para elegância absoluta
    linhas_manchete = linhas_manchete[:4]
    line_h = 68
    total_h_manchete = len(linhas_manchete) * line_h

    # Posição vertical calculada a partir do rodapé
    y_bloco = y_foot - 35 - total_h_manchete - 55

    # Linha dourada decorativa acima da tag
    draw.line([(px, y_bloco - 12), (px + 65, y_bloco - 12)], fill=OURO, width=2)

    # Tag do caderno em caixa alta com cor mostarda/dourado suave
    f_tag = _inter(22, weight=700)
    tag_texto = tema.strip().upper()
    _texto_espacado(draw, (px, y_bloco), tag_texto, f_tag, OURO_SUAVE, tracking=4)

    # Manchete principal em tipografia serifada encorpada branca (Playfair Display)
    cur_y = y_bloco + 45
    for linha in linhas_manchete:
        draw.text((px, cur_y), linha, font=f_manchete, fill=BRANCO_PURO)
        cur_y += line_h

    return canvas

def gerar_slide_conteudo(tema, kw, subtitulo, corpo_texto, foto, slide_idx, total_slides):
    """
    2. SLIDES SEGUINTES (SLIDES 2 A N - CONTEÚDO / CORPO DA NOTÍCIA):
    - Editorial brutalista refinado e escuro sobre fundo #0B0F14.
    - Topo com 'ALL NEWS JOURNAL • [NOME DO CADERNO]' discreto.
    - Elemento gráfico central com 3 linhas sobrepostas de palavra-chave em Montserrat-Black (Knockout mask da foto).
    - Subtítulo/gancho analítico em serifa branca refinada (Playfair Display).
    - Bloco de leitura com 85 a 105 palavras em tipografia sem serifa (Inter), cor #E2E8F0, entrelinha 1.45.
    - Dots indicadores de carrossel no rodapé.
    """
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), GRAFITE_ESCURO)

    px = 70
    max_w = W - 2 * px

    # 1. Topo: Identificador conciso "ALL NEWS JOURNAL • [NOME DO CADERNO]"
    draw = ImageDraw.Draw(canvas)
    f_top = _playfair(19, weight=700)
    top_str = f"ALL NEWS JOURNAL  •  {tema.upper()}"
    _texto_espacado(draw, (px, 52), top_str, f_top, TEXTO_MUTED, tracking=3)

    # 2. Elemento Gráfico Central: 3 linhas sobrepostas de Knockout Text
    mask_im = Image.new("L", (W, H), 0)
    draw_mask = ImageDraw.Draw(mask_im)

    kw_clean = kw.strip().upper()
    font_size = 175
    while font_size > 65 and draw_mask.textlength(kw_clean, font=_montserrat(font_size)) > max_w:
        font_size -= 4

    f_mask = _montserrat(font_size)
    w_kw = draw_mask.textlength(kw_clean, font=f_mask)
    x_kw = (W - w_kw) // 2

    y_mask_start = 100
    step_y = int(font_size * 0.90)  # ritmo vertical imponente

    for rep in range(3):
        draw_mask.text((x_kw, y_mask_start + rep * step_y), kw_clean, font=f_mask, fill=255)

    if foto:
        foto_cover = _cover_sem_corte(foto, W, H)
        canvas.paste(foto_cover, (0, 0), mask=mask_im)

    draw = ImageDraw.Draw(canvas)

    # 3. Subtítulo / Gancho analítico em serifa refinada branca
    cur_y = y_mask_start + (3 * step_y) + 40

    if subtitulo:
        f_sub = _playfair(44, weight=700)
        linhas_sub = _quebrar_texto(draw, subtitulo, f_sub, max_w)
        for linha in linhas_sub[:2]:  # 2 linhas de gancho
            draw.text((px, cur_y), linha, font=f_sub, fill=BRANCO_PURO)
            cur_y += 54
        cur_y += 18

    # 4. Bloco de Leitura: 85 a 105 palavras, tipografia sem serifa Inter, cor #E2E8F0, entrelinha 1.45
    if corpo_texto:
        f_corpo = _inter(31, weight=400)
        line_height_corpo = int(31 * 1.45)  # ~45px
        linhas_corpo = _quebrar_texto(draw, corpo_texto, f_corpo, max_w)

        for linha in linhas_corpo:
            if cur_y + line_height_corpo > 1240:
                draw.text((px, cur_y), linha[:max(10, len(linha)-3)] + "...", font=f_corpo, fill=CINZA_CORPO)
                break
            draw.text((px, cur_y), linha, font=f_corpo, fill=CINZA_CORPO)
            cur_y += line_height_corpo

    # 5. Indicadores de Carrossel (Dots)
    if total_slides > 1:
        raio = 5
        espacamento = 24
        largura_total = (total_slides - 1) * espacamento
        x_inicio_dots = (W - largura_total) // 2
        y_dots = 1295
        for s in range(total_slides):
            cx = x_inicio_dots + s * espacamento
            cor_dot = BRANCO_PURO if (s + 1) == slide_idx else (60, 65, 75)
            draw.ellipse([cx - raio, y_dots - raio, cx + raio, y_dots + raio], fill=cor_dot)

    return canvas

def gerar_slide(slide_idx, total_slides, tema, titulo, corpo, kw, foto, data_str=""):
    """
    3. REGRA DE TRANSIÇÃO ESTRITA:
    IF slide_idx == 1 THEN aplicar template de Capa Clássica;
    ELSE aplicar template Tipográfico Escuro Brutalista.
    """
    if slide_idx == 1:
        return gerar_slide_capa(
            tema=tema,
            manchete=titulo,
            foto=foto,
            data_str=data_str,
            total_slides=total_slides
        )
    else:
        return gerar_slide_conteudo(
            tema=tema,
            kw=kw,
            subtitulo=titulo,
            corpo_texto=corpo,
            foto=foto,
            slide_idx=slide_idx,
            total_slides=total_slides
        )

# Alias de compatibilidade com versões anteriores
gerar_slide_knockout = gerar_slide_conteudo

def segmentar_corpo_leitura(resumo, tema):
    """
    Segmenta e normaliza o resumo da notícia para compor blocos de leitura
    editorial de 85 a 105 palavras por slide de conteúdo.
    Se o resumo for escasso, enriquece com contextualização temática profissional.
    """
    resumo_limpo = re.sub(r'<[^>]+>', ' ', resumo or '')
    resumo_limpo = ' '.join(resumo_limpo.split())

    palavras = resumo_limpo.split()

    if len(palavras) < 45:
        contextos_fallback = {
            "Mundo": "Os desdobramentos diplomáticos e geopolíticos desta medida continuam a movimentar líderes globais e organismos internacionais. Analistas apontam que as próximas decisões estratégicas definirão novos equilíbrios de poder e alianças de segurança multilateral nas próximas semanas.",
            "Economia": "O movimento dos mercados reflete a cautela de investidores diante das novas sinalizações de juros e indicadores macroeconômicos. Especialistas destacam que a reação dos ativos pode ditar o ritmo de alocação de capital e fluxo cambial ao longo do trimestre.",
            "Politica": "As negociações institucionais em Brasília ganham novos contornos à medida que lideranças partidárias e parlamentares articulam votos e acordos de bastidores. O desfecho das votações deve impactar diretamente a tramitação das pautas prioritárias.",
            "IA": "O avanço de novas arquiteturas e modelos generativos acelera a corrida por infraestrutura computacional e governança algorítmica. O setor debate agora os equilíbrios necessários entre inovação de ponta, segurança operacional e regulação sistêmica.",
            "Wellness": "Pesquisas recentes e especialistas em longevidade reforçam a importância de consistência em hábitos diários para a saúde metabólica e cognitiva. Pequenos ajustes de rotina produzem impactos cumulativos significativos na vitalidade a longo prazo.",
            "Ciencia": "Os dados coletados abrem novas frentes de investigação acadêmica e colaboração científica internacional. Pesquisadores afirmam que a validação experimental destes achados pode redefinir paradigmas metodológicos da área.",
            "Cinema": "A recepção de crítica e público evidencia transformações nos padrões de consumo audiovisual e estratégias de lançamento das grandes produtoras e plataformas de streaming.",
            "Fofoca": "A repercussão nas redes sociais e os bastidores do meio artístico continuam gerando engajamento recorde e discussões sobre a dinâmica contemporânea da cultura pop e da visibilidade pública."
        }
        complemento = contextos_fallback.get(tema, contextos_fallback["Mundo"])
        if resumo_limpo:
            resumo_limpo = f"{resumo_limpo} {complemento}"
        else:
            resumo_limpo = complemento
        palavras = resumo_limpo.split()

    if len(palavras) <= 125:
        return [resumo_limpo]

    frases = re.split(r'(?<=[.!?])\s+', resumo_limpo)
    bloco1, bloco2 = [], []
    w1 = 0
    for f in frases:
        nw = len(f.split())
        if w1 + nw <= 105 or w1 < 80:
            bloco1.append(f)
            w1 += nw
        else:
            bloco2.append(f)

    txt1 = ' '.join(bloco1).strip()
    txt2 = ' '.join(bloco2).strip()

    if txt2 and len(txt2.split()) >= 35:
        return [txt1, txt2]
    return [resumo_limpo]

# =============================================================================
# --- CARREGAMENTO DE NOTÍCIAS & ANTI-DUPLICATA ---
# =============================================================================
def obter_top5_noticias():
    """
    Carrega as notícias da edição mais recente com proteção contra republicação no mesmo dia.
    """
    ed_dir = Path(EDICOES_DIR)
    antigos = sorted(ed_dir.glob('????-??-??.json'), reverse=True)
    if not antigos:
        print("   ❌ Nenhuma edição encontrada em edicoes/.")
        return []
        
    mais_recente = antigos[0]
    data_edicao = mais_recente.stem  # 'YYYY-MM-DD'
    
    memoria = carregar_memoria()
    ultima_postada = memoria.get("ultima_edicao_instagram", "")
    
    # Se já foi postada essa edição exata, não duplica
    if ultima_postada == data_edicao:
        print(f"   ℹ️ A edição {data_edicao} já foi publicada no Instagram anteriormente. Pulando para não duplicar.")
        return []
        
    try:
        edicao = json.loads(mais_recente.read_text(encoding='utf-8'))
        cadernos = edicao.get('cadernos', {})
    except Exception as e:
        print(f"   ❌ Erro ao ler JSON da edição {data_edicao}: {e}")
        return []

    noticias = []
    for tema in ORDEM_CADERNOS:
        if tema in cadernos and cadernos[tema]:
            item = cadernos[tema][0]
            noticias.append({
                'tema': tema,
                'titulo': item.get('titulo', ''),
                'resumo': item.get('resumo', ''),
                'imagem': item.get('imagem', ''),
                'data_edicao': data_edicao
            })
            if len(noticias) == MAX_POSTS:
                break
                
    return noticias

def gerar_legenda(tema, titulo, resumo):
    icone = ICONES_TEMA.get(tema, "📰")
    tags  = HASHTAGS_TEMA.get(tema, "#noticias #brasil")
    
    # Limpa tags HTML como <b> do resumo para a legenda
    resumo_limpo = re.sub(r'<[^>]+>', '', resumo)
    
    return (
        f"{icone}  {tema.upper()} — ALL NEWS JOURNAL\n\n"
        f"{titulo.upper()}\n\n"
        f"{resumo_limpo[:450]}...\n\n"
        f"📩  A edição completa chega todas as manhãs no seu e-mail.\n"
        f"Assine grátis no link da nossa bio.\n\n"
        f"{tags}\n"
        f"@all.news.journal"
    )

# =============================================================================
# --- FLUXO PRINCIPAL DE GERAÇÃO E POSTAGEM ---
# =============================================================================
def main():
    print("📸 All News Journal — Instagram Álbum Poster (Padrão Knockout) v18.0")
    print("─" * 60)

    if not PIL_OK:
        print("   ❌ Pillow não instalado."); sys.exit(1)

    noticias = obter_top5_noticias()
    if not noticias:
        return

    data_edicao = noticias[0]["data_edicao"]
    try:
        data_formatada = datetime.strptime(data_edicao, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        data_formatada = datetime.now().strftime("%d.%m.%Y")

    memoria = carregar_memoria()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gerados = []

    print(f"   🔍 Processando {len(noticias)} notícias da edição {data_edicao} ({data_formatada})...")

    for i, item in enumerate(noticias, 1):
        tema, titulo, resumo, url_imagem = item["tema"], item["titulo"], item["resumo"], item["imagem"]
        
        # Garante a foto de alta qualidade (nunca None)
        foto = obter_foto_garantida(url_imagem, tema, idx_post=i, memoria=memoria)
        
        # Extrai palavras-chave de alto impacto
        keywords = extrair_keywords(titulo, resumo, tema)
        
        # Normaliza e segmenta blocos de leitura de 85 a 105 palavras
        blocos = segmentar_corpo_leitura(resumo, tema)

        # Montagem dos slides do Carrossel:
        # Condição lógica estrita:
        # IF slide_index == 1 THEN aplicar template de Capa Clássica;
        # ELSE aplicar template Tipográfico Escuro Brutalista.
        slides = []
        if len(blocos) == 1:
            total_slides = 3
            # Slide 1: Capa Clássica (sem resumo)
            s1 = gerar_slide(
                slide_idx=1,
                total_slides=total_slides,
                tema=tema,
                titulo=titulo,
                corpo="",
                kw=keywords[0],
                foto=foto,
                data_str=data_formatada
            )
            # Slide 2: Conteúdo Brutalista Knockout
            s2 = gerar_slide(
                slide_idx=2,
                total_slides=total_slides,
                tema=tema,
                titulo=titulo,
                corpo=blocos[0],
                kw=keywords[0],
                foto=foto,
                data_str=data_formatada
            )
            # Slide 3: Fechamento institucional / CTA
            s3 = gerar_slide(
                slide_idx=3,
                total_slides=total_slides,
                tema=tema,
                titulo="INFORMAÇÃO DIRETO AO PONTO",
                corpo="Notícias completas e aprofundadas, entregues diariamente às 6h no seu e-mail. Cadastre-se gratuitamente pelo link na nossa bio para não perder nenhuma edição matinal.",
                kw="ALL NEWS",
                foto=foto,
                data_str=data_formatada
            )
            slides = [s1, s2, s3]
        else:
            total_slides = 4
            kw2 = keywords[1] if len(keywords) > 1 else keywords[0]
            # Slide 1: Capa Clássica (sem resumo)
            s1 = gerar_slide(
                slide_idx=1,
                total_slides=total_slides,
                tema=tema,
                titulo=titulo,
                corpo="",
                kw=keywords[0],
                foto=foto,
                data_str=data_formatada
            )
            # Slide 2: Conteúdo Brutalista Knockout (Parte 1)
            s2 = gerar_slide(
                slide_idx=2,
                total_slides=total_slides,
                tema=tema,
                titulo=titulo,
                corpo=blocos[0],
                kw=keywords[0],
                foto=foto,
                data_str=data_formatada
            )
            # Slide 3: Conteúdo Brutalista Knockout (Parte 2 - Desdobramentos)
            s3 = gerar_slide(
                slide_idx=3,
                total_slides=total_slides,
                tema=tema,
                titulo="DESDOBRAMENTOS & IMPACTO",
                corpo=blocos[1],
                kw=kw2,
                foto=foto,
                data_str=data_formatada
            )
            # Slide 4: Fechamento institucional / CTA
            s4 = gerar_slide(
                slide_idx=4,
                total_slides=total_slides,
                tema=tema,
                titulo="INFORMAÇÃO DIRETO AO PONTO",
                corpo="Notícias completas e aprofundadas, entregues diariamente às 6h no seu e-mail. Cadastre-se gratuitamente pelo link na nossa bio para não perder nenhuma edição matinal.",
                kw="ALL NEWS",
                foto=foto,
                data_str=data_formatada
            )
            slides = [s1, s2, s3, s4]

        # Salva os arquivos de imagem
        paths = []
        for j, slide_img in enumerate(slides, 1):
            p = OUTPUT_DIR / f"post_{i:02d}_slide{j:02d}.jpg"
            slide_img.save(str(p), "JPEG", quality=94)
            paths.append(str(p))
            
        legenda = gerar_legenda(tema, titulo, resumo)
        gerados.append({"tema": tema, "paths": paths, "legenda": legenda})
        print(f"   🖼️  Carrossel {i} pronto: [{tema}] com {len(paths)} slides (Slide 1 Capa Clássica + {len(paths)-1} Slides Brutalistas).")

    # ── ENTREGA / PUBLICAÇÃO ──
    if not INSTAGRAM_ENABLED:
        print(f"\n   ℹ️  INSTAGRAM_ENABLED=false. {len(gerados)} álbuns salvos em {OUTPUT_DIR}.")
        return

    if INSTAGRAM_DELIVERY == "post":
        print("\n   🔐 Autenticando no Instagram…")
        if INSTAGRAM_SESSION:
            try: SESSION_FILE.write_bytes(base64.b64decode(INSTAGRAM_SESSION))
            except: pass
            
        cl = InstaClient()
        cl.delay_range = [2, 5]
        try:
            if SESSION_FILE.exists():
                cl.load_settings(str(SESSION_FILE))
                cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
            else:
                cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
        except Exception as e:
            print(f"   ❌ Erro de login no Instagram: {e}")
            return
            
        postados = 0
        for i, g in enumerate(gerados):
            print(f"\n   📤 Postando Álbum {g['tema']}…")
            try:
                cl.album_upload(g["paths"], g["legenda"])
                postados += 1
                print("   ✅ Álbum publicado com sucesso!")
                if i < len(gerados) - 1:
                    print(f"   ⏳ Aguardando {ESPERA_ENTRE}s de intervalo...")
                    time.sleep(ESPERA_ENTRE)
            except Exception as e:
                print(f"   ❌ Erro ao postar álbum: {e}")
                
        if postados > 0:
            # Registra na memória que esta edição já foi postada
            memoria["ultima_edicao_instagram"] = data_edicao
            salvar_memoria(memoria)
            print(f"\n✅ Concluído — {postados} post(s) publicado(s). Memória atualizada para {data_edicao}.")
    else:
        print(f"\n   ✉️  Modo fallback ({INSTAGRAM_DELIVERY}). {len(gerados)} álbuns prontos.")

if __name__ == "__main__":
    main()
