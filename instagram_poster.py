"""
instagram_poster.py — Novo formato de posts no Instagram do All News Journal (v17.0)
Gera posts de 2 slides (álbum) para as Top 5 notícias do dia.
- Slide 1: Manchete imponente (background blur + imagem inteira sem cortes).
- Slide 2: Resumo completo com fonte adaptativa (auto-scaling) para não cortar.
- IA Supervisor: Rastreia imagens postadas para não repeti-las.
"""
import os
import sys
import json
import time
import textwrap
import base64
from pathlib import Path
from datetime import datetime
from io import BytesIO

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

ESPERA_ENTRE = 180   # 3 minutos entre posts
FORMATO      = (1080, 1350)  # retrato
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
# --- IDENTIDADE VISUAL ---
# =============================================================================
TURQUESA      = (10, 92, 90)     
TURQUESA_DARK = (8, 60, 58)      
CREME         = (253, 251, 247)  
OURO          = (201, 168, 76)   
OURO_CLARO    = (214, 184, 102)

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
    "Mundo":    "#noticias #mundo #geopolitica #internacional",
    "Economia": "#economia #mercado #investimentos #financas",
    "Politica": "#politica #brasil #governo #democracia",
    "IA":       "#ia #inteligenciaartificial #tecnologia",
    "Wellness": "#wellness #saude #performance",
    "Ciencia":  "#ciencia #pesquisa #descoberta",
    "Cinema":   "#cinema #filmes #series #streaming",
    "Fofoca":   "#celebridades #entretenimento",
}

from config import ORDEM_CADERNOS

# =============================================================================
# --- FONTES ---
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

def _playfair(tamanho, weight=800):
    return _font("PlayfairDisplay.ttf", tamanho, weight=weight)

def _lora(tamanho, weight=500):
    return _font("Lora.ttf", tamanho, weight=weight)

def _texto_espacado(draw, xy, texto, font, fill, tracking=0):
    x, y = xy
    larguras = [draw.textlength(ch, font=font) for ch in texto]
    for ch, w in zip(texto, larguras):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return sum(larguras) + tracking * max(0, len(texto) - 1)

# =============================================================================
# --- MEMÓRIA DO SUPERVISOR (FOTOS REPETIDAS) ---
# =============================================================================
def carregar_memoria():
    if not MEMORY_FILE.exists(): return {"erros": [], "imagens_recentes": []}
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"erros": data, "imagens_recentes": []}
        if "imagens_recentes" not in data:
            data["imagens_recentes"] = []
        return data
    except:
        return {"erros": [], "imagens_recentes": []}

def salvar_memoria(memoria):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(memoria, indent=4), encoding="utf-8")

def validar_imagem(imagem_url, memoria):
    if not imagem_url: return False
    recentes = memoria.get("imagens_recentes", [])
    if imagem_url in recentes:
        return False
    # Atualiza memória (mantém as últimas 50 imagens)
    recentes.append(imagem_url)
    memoria["imagens_recentes"] = recentes[-50:]
    salvar_memoria(memoria)
    return True

# =============================================================================
# --- IMAGEM E DESIGN ---
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

def _cover_sem_corte(img, w, h):
    """Fundo borrado com imagem inteira centralizada para não haver corte."""
    fundo = img.copy()
    sr, dr = fundo.width / fundo.height, w / h
    if sr > dr: nw, nh = int(h * sr), h
    else:       nw, nh = w, int(w / sr)
    
    fundo = fundo.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    fundo = fundo.crop((left, top, left + w, top + h))
    fundo = fundo.filter(ImageFilter.GaussianBlur(radius=40))
    
    if sr > dr: nw, nh = w, int(w / sr)
    else:       nw, nh = int(h * sr), h
    img_fit = img.resize((nw, nh), Image.LANCZOS)
    
    offset_x = (w - nw) // 2
    offset_y = (h - nh) // 2
    fundo.paste(img_fit, (offset_x, offset_y))
    return fundo

def desenhar_identidade(draw, W, H, px, tema, data_str):
    _texto_espacado(draw, (px, 64), "ALL NEWS JOURNAL", _lora(25, 600), CREME, tracking=6)
    draw.line([(px, 104), (px + 168, 104)], fill=OURO, width=2)
    f_data = _lora(21, 500)
    dw = draw.textlength(data_str, font=f_data)
    draw.text((W - px - dw, 66), data_str, font=f_data, fill=CREME)

    y_rodape = H - 88
    draw.line([(px, y_rodape - 18), (W - px, y_rodape - 18)], fill=OURO, width=1)
    _texto_espacado(draw, (px, y_rodape), "@ALL.NEWS.JOURNAL", _lora(22, 500), OURO_CLARO, tracking=3)
    direita = "ARRASTE PARA LER"
    f_r = _lora(20, 500)
    larg = sum(draw.textlength(c, font=f_r) for c in direita) + 3 * (len(direita) - 1)
    _texto_espacado(draw, (W - px - larg, y_rodape + 1), direita, f_r, CREME, tracking=3)

# =============================================================================
# --- SLIDE 1 (MANCHETE) ---
# =============================================================================
def gerar_slide_1(tema, titulo, data_str, foto):
    W, H = FORMATO
    canvas = (_cover_sem_corte(foto, W, H) if foto else Image.new("RGB", (W, H), TURQUESA_DARK)).convert("RGB")
    
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    base_rgb = tuple(int(c * 0.45) for c in TURQUESA_DARK)
    for y in range(H):
        t = y / H
        alpha = int(255 * (0.30 + 0.70 * (t ** 1.6)))
        gd.line([(0, y), (W, y)], fill=(*base_rgb, alpha))
    topo = int(H * 0.20)
    for y in range(topo):
        a = int(180 * (1 - y / topo))
        gd.line([(0, y), (W, y)], fill=(*TURQUESA_DARK, a))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    px = 70
    desenhar_identidade(draw, W, H, px, tema, data_str)

    linhas = textwrap.wrap(titulo, width=15)
    if len(linhas) <= 3: f_titulo, lh = _playfair(82), 92
    elif len(linhas) == 4: f_titulo, lh = _playfair(68), 78
    elif len(linhas) == 5:
        f_titulo, lh = _playfair(58), 68
        linhas = textwrap.wrap(titulo, width=20)
    else:
        f_titulo, lh = _playfair(48), 58
        linhas = textwrap.wrap(titulo, width=22)[:7]
        
    altura_manchete = lh * len(linhas)
    y_rodape = H - 88
    y_titulo = (y_rodape - 80) - altura_manchete

    selo = NOME_EXIBICAO.get(tema, tema.upper())
    draw.line([(px, y_titulo - 40), (px + 54, y_titulo - 40)], fill=OURO, width=3)
    _texto_espacado(draw, (px, y_titulo - 30), selo, _lora(24, 700), OURO_CLARO, tracking=4)

    y = y_titulo
    for ln in linhas:
        draw.text((px, y), ln, font=f_titulo, fill=CREME)
        y += lh
        
    m = 34
    draw.rectangle([m, m, W - m, H - m], outline=OURO, width=2)
    draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=OURO_CLARO, width=1)

    return canvas

# =============================================================================
# --- SLIDES INTERMEDIÁRIOS (NOTÍCIA PAGINADA) ---
# =============================================================================
def gerar_slides_noticia(tema, resumo, data_str):
    W, H = FORMATO
    px = 70
    m = 34
    y_rodape = H - 88
    max_w = W - (px * 2)
    max_h = y_rodape - 220
    y_inicio = 160
    
    tamanho = 50
    font = _lora(tamanho, 400)
    lh = int(tamanho * 1.6)
    max_linhas_por_slide = max_h // lh

    # Divide o texto em linhas
    draw_mock = ImageDraw.Draw(Image.new("RGB", (1,1)))
    palavras = resumo.split()
    linhas = []
    linha_atual = ""
    for p in palavras:
        teste = linha_atual + " " + p if linha_atual else p
        if draw_mock.textlength(teste, font=font) <= max_w:
            linha_atual = teste
        else:
            linhas.append(linha_atual)
            linha_atual = p
    if linha_atual:
        linhas.append(linha_atual)

    # Agrupa as linhas em páginas
    paginas = []
    for i in range(0, len(linhas), max_linhas_por_slide):
        paginas.append(linhas[i:i + max_linhas_por_slide])

    slides = []
    total_paginas = len(paginas)
    
    for i, pagina in enumerate(paginas):
        canvas = Image.new("RGB", (W, H), CREME)
        draw = ImageDraw.Draw(canvas)
        
        draw.rectangle([m, m, W - m, H - m], outline=TURQUESA_DARK, width=2)
        draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=TURQUESA, width=1)
        
        _texto_espacado(draw, (px, 64), "ALL NEWS JOURNAL", _lora(25, 600), TURQUESA_DARK, tracking=6)
        draw.line([(px, 104), (px + 168, 104)], fill=OURO, width=2)
        
        draw.line([(px, y_rodape - 18), (W - px, y_rodape - 18)], fill=OURO, width=1)
        _texto_espacado(draw, (px, y_rodape), "@ALL.NEWS.JOURNAL", _lora(22, 500), TURQUESA, tracking=3)

        # Numeração e Seta indicativa
        num_str = f"Parte {i+1} de {total_paginas}"
        f_r = _lora(20, 500)
        larg_num = sum(draw.textlength(c, font=f_r) for c in num_str) + 3 * (len(num_str) - 1)
        _texto_espacado(draw, (W - px - larg_num, y_rodape + 1), num_str, f_r, TURQUESA_DARK, tracking=3)
        
        # Seta maior no canto superior direito para guiar a leitura
        seta = "CONTINUA 👉"
        larg_seta = sum(draw.textlength(c, font=f_r) for c in seta) + 3 * (len(seta) - 1)
        _texto_espacado(draw, (W - px - larg_seta, 66), seta, f_r, TURQUESA, tracking=3)

        # Centraliza verticalmente o texto no slide
        altura_total = len(pagina) * lh
        folga_y = max(0, (max_h - altura_total) // 2)
        y = y_inicio + folga_y
        for ln in pagina:
            draw.text((px, y), ln, font=font, fill=TURQUESA_DARK)
            y += lh
            
        slides.append(canvas)
        
    return slides

# =============================================================================
# --- SLIDE FINAL (CTA) ---
# =============================================================================
def gerar_slide_cta(data_str):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), TURQUESA_DARK)
    draw = ImageDraw.Draw(canvas)
    
    px = 70
    m = 34
    draw.rectangle([m, m, W - m, H - m], outline=OURO, width=2)
    draw.rectangle([m + 8, m + 8, W - m - 8, H - m - 8], outline=OURO_CLARO, width=1)
    
    _texto_espacado(draw, (px, 64), "ALL NEWS JOURNAL", _lora(25, 600), CREME, tracking=6)
    draw.line([(px, 104), (px + 168, 104)], fill=OURO, width=2)
    
    y_rodape = H - 88
    draw.line([(px, y_rodape - 18), (W - px, y_rodape - 18)], fill=OURO, width=1)
    _texto_espacado(draw, (px, y_rodape), "@ALL.NEWS.JOURNAL", _lora(22, 500), OURO_CLARO, tracking=3)

    # Texto central de Inscrição
    f_titulo = _playfair(62, 800)
    f_sub = _lora(36, 400)
    
    msg1 = "Gostou da leitura?"
    msg2 = "A edição completa"
    msg3 = "chega todas as manhãs."
    
    y_centro = (H // 2) - 160
    
    for text in [msg1, msg2, msg3]:
        w_txt = draw.textlength(text, font=f_titulo)
        draw.text(((W - w_txt)//2, y_centro), text, font=f_titulo, fill=CREME)
        y_centro += 80
        
    y_centro += 40
    # Botão visual
    w_btn = 500
    h_btn = 90
    x_btn = (W - w_btn) // 2
    draw.rounded_rectangle([x_btn, y_centro, x_btn + w_btn, y_centro + h_btn], radius=45, fill=OURO)
    
    txt_btn = "Assine no link da Bio"
    w_btn_txt = draw.textlength(txt_btn, font=f_sub)
    draw.text((x_btn + (w_btn - w_btn_txt)//2, y_centro + 20), txt_btn, font=f_sub, fill=TURQUESA_DARK)
    
    return canvas

# =============================================================================
# --- ORQUESTRAÇÃO DE POSTS ---
# =============================================================================
def obter_top5_noticias():
    ed_dir = Path(EDICOES_DIR)
    antigos = sorted(ed_dir.glob("????-??-??.json"), reverse=True)
    if not antigos: return []
    
    try:
        edicao = json.loads(antigos[0].read_text(encoding="utf-8"))
        cadernos = edicao.get("cadernos", {})
    except:
        return []

    noticias = []
    for tema in ORDEM_CADERNOS:
        if tema in cadernos and cadernos[tema]:
            noticias.append({
                "tema": tema,
                "titulo": cadernos[tema][0].get("titulo", ""),
                "resumo": cadernos[tema][0].get("resumo", ""),
                "imagem": cadernos[tema][0].get("imagem", ""),
            })
            if len(noticias) == MAX_POSTS:
                break
    return noticias

def gerar_legenda(tema, titulo, resumo):
    icone = ICONES_TEMA.get(tema, "📰")
    nome  = NOME_EXIBICAO.get(tema, tema.upper())
    tags  = HASHTAGS_TEMA.get(tema, "#noticias #brasil")
    return (
        f"{icone}  {nome}\n\n"
        f"{titulo.upper()}\n\n"
        f"📩  A edição completa chega todas as manhãs no seu e-mail.\n"
        f"Assine grátis no link da bio.\n\n"
        f"{tags}\n"
        f"@all.news.journal"
    )

def main():
    print("📸 All News Journal — Instagram Álbum Poster (Top 5) v17.0")
    print("─" * 50)

    if not INSTAGRAM_ENABLED:
        print("   ℹ️  INSTAGRAM_ENABLED=false — as imagens serão geradas, mas a entrega será pulada.")
    if not PIL_OK:
        print("   ❌ Pillow não instalado."); sys.exit(1)

    hoje = datetime.now()
    data_str = f"{hoje.day:02d}.{hoje.month:02d}.{hoje.year}"

    noticias = obter_top5_noticias()
    if not noticias:
        print("   ❌ Nenhuma notícia encontrada na edição diária."); return

    memoria = carregar_memoria()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gerados = []

    print(f"   🔍 Analisando {len(noticias)} notícias para gerar os posts...")
    for i, item in enumerate(noticias, 1):
        tema, titulo, resumo, imagem = item["tema"], item["titulo"], item["resumo"], item["imagem"]
        
        if imagem and not validar_imagem(imagem, memoria):
            print(f"   🤖 Supervisor: Imagem já usada recentemente para '{titulo[:30]}'. Usando gradiente base.")
            imagem = None 

        foto = _baixar_imagem(imagem)
        
        slide_capa = gerar_slide_1(tema, titulo, data_str, foto)
        slides_meio = gerar_slides_noticia(tema, resumo, data_str)
        slide_cta = gerar_slide_cta(data_str)
        
        # Junta tudo no álbum
        album_imagens = [slide_capa] + slides_meio + [slide_cta]
        
        paths = []
        for j, img_canvas in enumerate(album_imagens, 1):
            p = OUTPUT_DIR / f"post_{i:02d}_slide{j:02d}.jpg"
            img_canvas.save(str(p), "JPEG", quality=92)
            paths.append(str(p))
        
        legenda = gerar_legenda(tema, titulo, resumo)
        gerados.append({"tema": tema, "paths": paths, "legenda": legenda})
        print(f"   🖼️  Carrossel {i} gerado: {tema} ({len(paths)} fotos)")

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
            print(f"   ❌ Erro de login: {e}")
            return
            
        postados = 0
        for i, g in enumerate(gerados):
            print(f"\n   📤 Postando Álbum {g['tema']}…")
            try:
                cl.album_upload(g["paths"], g["legenda"])
                postados += 1
                print("   ✅ Álbum publicado!")
                if i < len(gerados) - 1:
                    print(f"   ⏳ Aguardando {ESPERA_ENTRE}s...")
                    time.sleep(ESPERA_ENTRE)
            except Exception as e:
                print(f"   ❌ Erro ao postar álbum: {e}")
                
        print(f"\n✅ Concluído — {postados} post(s) publicado(s).")
    else:
        print(f"\n   ✉️  Modo fallback. {len(gerados)} álbuns gerados em {OUTPUT_DIR}.")

if __name__ == "__main__":
    main()
