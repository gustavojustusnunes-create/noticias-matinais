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
PRETO         = (15, 15, 18)

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

def _montserrat(tamanho):
    return _font("Montserrat-Black.ttf", tamanho)

def extrair_sintese(resumo):
    import re
    frases = [f.strip() for f in re.split(r'[.!?]', resumo) if len(f.strip()) > 10]
    if not frases:
        return resumo[:80] + "..."
    primeira = frases[0]
    palavras = primeira.split()
    if len(palavras) > 12:
        return " ".join(palavras[:12]) + "..."
    return primeira

def extrair_keywords(titulo):
    import re
    palavras = re.findall(r'\b\w+\b', titulo.upper())
    validas = [p for p in palavras if len(p) > 3 and not p.isnumeric()]
    if len(validas) < 3:
        validas = palavras
    return sorted(validas, key=len, reverse=True)[:3]

def desenhar_identidade_minimalista(draw, W, H, px, tema, data_str):
    _texto_espacado(draw, (px, 60), f"ALL NEWS JOURNAL — {tema.upper()}", _lora(22, 600), CREME, tracking=4)
    w_data = draw.textlength(data_str, font=_lora(22, 500))
    draw.text((W - px - w_data, 60), data_str, font=_lora(22, 500), fill=CREME)

def gerar_slide_1_hook(tema, titulo, data_str, foto):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), TURQUESA_DARK)
    if foto:
        img_bg = _cover_sem_corte(foto, W, H)
        mask = Image.new("RGBA", (W, H), (10, 37, 64, 180))
        img_bg = img_bg.convert("RGBA")
        img_bg.alpha_composite(mask)
        canvas.paste(img_bg.convert("RGB"), (0, 0))
    
    draw = ImageDraw.Draw(canvas)
    desenhar_identidade_minimalista(draw, W, H, 60, tema, data_str)
    
    f_titulo = _montserrat(90)
    palavras = titulo.upper().split()
    linhas, linha_atual = [], []
    for p in palavras:
        linha_atual.append(p)
        if draw.textlength(" ".join(linha_atual), font=f_titulo) > (W - 120):
            linha_atual.pop()
            linhas.append(" ".join(linha_atual))
            linha_atual = [p]
    if linha_atual: linhas.append(" ".join(linha_atual))
        
    y_text = (H - (len(linhas) * 100)) // 2
    for linha in linhas:
        draw.text((60, y_text), linha, font=f_titulo, fill=CREME)
        y_text += 100
    return canvas

def gerar_slide_2_sintese(tema, resumo, data_str):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), PRETO)
    draw = ImageDraw.Draw(canvas)
    desenhar_identidade_minimalista(draw, W, H, 60, tema, data_str)
    
    sintese = extrair_sintese(resumo).upper()
    f_sintese = _montserrat(80)
    palavras = sintese.split()
    linhas, linha_atual = [], []
    for p in palavras:
        linha_atual.append(p)
        if draw.textlength(" ".join(linha_atual), font=f_sintese) > (W - 160):
            linha_atual.pop()
            linhas.append(" ".join(linha_atual))
            linha_atual = [p]
    if linha_atual: linhas.append(" ".join(linha_atual))
        
    y_text = (H - (len(linhas) * 90)) // 2
    for i, linha in enumerate(linhas):
        cor = OURO if i % 2 != 0 else CREME
        draw.text((80, y_text), linha, font=f_sintese, fill=cor)
        y_text += 90
    return canvas

def gerar_slide_mascara(resumo, titulo, foto, parte_idx):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), PRETO)
    mask_im = Image.new("L", (W, H), 0)
    draw_mask = ImageDraw.Draw(mask_im)
    
    keywords = extrair_keywords(titulo)
    kw = keywords[parte_idx-1] if (parte_idx-1) < len(keywords) else "ALL NEWS"
    
    f_mask = _montserrat(160)
    y_mask = H // 2 - 300
    for _ in range(4):
        w_kw = draw_mask.textlength(kw, font=f_mask)
        draw_mask.text(((W - w_kw)//2, y_mask), kw, font=f_mask, fill=255)
        y_mask += 160
        
    if foto:
        img_bg = _cover_sem_corte(foto, W, H).convert("RGB")
        canvas.paste(img_bg, (0, 0), mask=mask_im)
    
    draw = ImageDraw.Draw(canvas)
    f_texto = _lora(45, 500)
    meio = len(resumo) // 2
    texto_parte = resumo[:meio] + "..." if parte_idx == 1 else "..." + resumo[meio:]
    
    palavras = texto_parte.split()
    linhas, linha_atual = [], []
    for p in palavras:
        linha_atual.append(p)
        if draw.textlength(" ".join(linha_atual), font=f_texto) > (W - 160):
            linha_atual.pop()
            linhas.append(" ".join(linha_atual))
            linha_atual = [p]
    if linha_atual: linhas.append(" ".join(linha_atual))
        
    y_texto_detalhe = H - 80 - (len(linhas) * 60)
    draw.rectangle([0, y_texto_detalhe - 40, W, H], fill=PRETO)
    for linha in linhas:
        draw.text((80, y_texto_detalhe), linha, font=f_texto, fill=CREME)
        y_texto_detalhe += 60
    return canvas

def gerar_slide_5_veredito(resumo):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), TURQUESA_DARK)
    draw = ImageDraw.Draw(canvas)
    
    f_conclusao = _montserrat(110)
    draw.text((80, 200), "EM", font=f_conclusao, fill=OURO_CLARO)
    draw.text((80, 310), "RESUMO:", font=f_conclusao, fill=OURO)
    
    import re
    frases = [f.strip() for f in re.split(r'[.!?]', resumo) if len(f.strip()) > 10]
    final_text = frases[-1] if frases else resumo[-100:]
    
    f_texto = _lora(55, 400)
    palavras = final_text.split()
    linhas, linha_atual = [], []
    for p in palavras:
        linha_atual.append(p)
        if draw.textlength(" ".join(linha_atual), font=f_texto) > (W - 160):
            linha_atual.pop()
            linhas.append(" ".join(linha_atual))
            linha_atual = [p]
    if linha_atual: linhas.append(" ".join(linha_atual))
        
    y_text = 600
    for linha in linhas:
        draw.text((80, y_text), linha, font=f_texto, fill=CREME)
        y_text += 70
    return canvas

def gerar_slide_cta(data_str):
    W, H = FORMATO
    canvas = Image.new("RGB", (W, H), OURO)
    draw = ImageDraw.Draw(canvas)
    
    f_cta = _montserrat(90)
    text_cta = ["RECEBA ESTA", "E OUTRAS", "ANÁLISES", "EXCLUSIVAS", "ÀS 6H."]
    y_cta = 250
    for linha in text_cta:
        draw.text((80, y_cta), linha, font=f_cta, fill=TURQUESA_DARK)
        y_cta += 100
        
    y_btn = y_cta + 100
    draw.rounded_rectangle([80, y_btn, W - 80, y_btn + 120], radius=60, fill=PRETO)
    
    f_btn = _lora(45, 600)
    w_btn_txt = draw.textlength("Link na Bio para Assinar", font=f_btn)
    draw.text((80 + ((W - 160) - w_btn_txt)//2, y_btn + 30), "Link na Bio para Assinar", font=f_btn, fill=CREME)
    return canvas

# =============================================================================
# --- ORQUESTRAÇÃO DE POSTS ---
# =============================================================================
def obter_top5_noticias():
    ed_dir = Path(EDICOES_DIR)
    antigos = sorted(ed_dir.glob('????-??-??.json'), reverse=True)
    if not antigos: return []
    
    dia_atual = antigos[0].stem
    try:
        edicao = json.loads(antigos[0].read_text(encoding='utf-8'))
        cadernos = edicao.get('cadernos', {})
    except:
        return []

    # Tenta ler a fila do Google Sheets
    noticias = []
    selecoes = None
    try:
        if os.environ.get('GCP_JSON') and os.environ.get('GOOGLE_SHEETS_ID'):
            import gspread
            from google.oauth2.service_account import Credentials
            creds_dict = json.loads(os.environ['GCP_JSON'])
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = os.environ['GOOGLE_SHEETS_ID']
            planilha = client.open_by_key(sheet_id)
            ws = planilha.worksheet('Instagram_Queue')
            
            records = ws.get_all_records()
            for row in records:
                if str(row.get('Data')) == dia_atual:
                    selecoes = json.loads(str(row.get('Selecao_JSON')))
                    break
    except Exception as e:
        print(f'⚠️ Erro ao ler planilha do Instagram: {e}')
        selecoes = None

    if selecoes:
        print(f'✅ Usando curadoria manual: {selecoes}')
        for tema, idx in selecoes.items():
            if tema in cadernos and cadernos[tema] and idx < len(cadernos[tema]):
                noticia = cadernos[tema][idx]
                noticias.append({
                    'tema': tema,
                    'titulo': noticia.get('titulo', ''),
                    'resumo': noticia.get('resumo', ''),
                    'imagem': noticia.get('imagem', ''),
                })
        return noticias
        
    print('⚠️ Sem curadoria manual. Usando lógica padrão (Top 1).')
    for tema in ORDEM_CADERNOS:
        if tema in cadernos and cadernos[tema]:
            noticias.append({
                'tema': tema,
                'titulo': cadernos[tema][0].get('titulo', ''),
                'resumo': cadernos[tema][0].get('resumo', ''),
                'imagem': cadernos[tema][0].get('imagem', ''),
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
        
        slide_capa = gerar_slide_1_hook(tema, titulo, data_str, foto)
        slide_sintese = gerar_slide_2_sintese(tema, resumo, data_str)
        slide_mask1 = gerar_slide_mascara(resumo, titulo, foto, 1)
        slide_mask2 = gerar_slide_mascara(resumo, titulo, foto, 2)
        slide_ver = gerar_slide_5_veredito(resumo)
        slide_cta = gerar_slide_cta(data_str)
        
        # Junta tudo no álbum
        album_imagens = [slide_capa, slide_sintese, slide_mask1, slide_mask2, slide_ver, slide_cta]
        
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
