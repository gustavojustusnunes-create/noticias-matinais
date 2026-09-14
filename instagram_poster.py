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
FUNDO_ESCURO = (13, 13, 13)
CREME        = (253, 251, 247)
TEXTO_CORPO  = (226, 224, 218)
TEXTO_MUTED  = (160, 160, 160)
OURO         = (201, 168, 76)
ESMERALDA    = (10, 92, 90)

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
# --- MOTOR DO NOVO DESIGN (SLIDE KNOCKOUT) ---
# =============================================================================
def gerar_slide_knockout(tema, kw, titulo_texto, corpo_texto, foto, slide_idx, total_slides):
    """
    Gera o slide seguindo fielmente a referência visual:
    1. Palavra-chave repetida 3 vezes no topo.
    2. A foto recortada e visível ESTRITAMENTE dentro das letras (Knockout Mask).
    3. Fundo preto nobre (#0d0d0d).
    4. Título em Playfair Display e descrição em Lora.
    5. Indicadores de carrossel no rodapé.
    """
    W, H = FORMATO  # 1080 x 1350
    canvas = Image.new("RGB", (W, H), FUNDO_ESCURO)
    
    # ── 1. Máscara das Letras (Knockout Mask) ──
    mask_im = Image.new("L", (W, H), 0)
    draw_mask = ImageDraw.Draw(mask_im)
    
    kw_clean = kw.strip().upper()
    font_size = 175
    # Reduz gradativamente até que a palavra ocupe a largura ideal com margem
    while font_size > 60 and draw_mask.textlength(kw_clean, font=_montserrat(font_size)) > (W - 120):
        font_size -= 4
        
    f_mask = _montserrat(font_size)
    w_kw = draw_mask.textlength(kw_clean, font=f_mask)
    x_kw = (W - w_kw) // 2
    
    y_mask_start = 85
    step_y = int(font_size * 0.92)
    
    # 3 repetições verticais imponentes
    for rep in range(3):
        draw_mask.text((x_kw, y_mask_start + rep * step_y), kw_clean, font=f_mask, fill=255)
        
    # Aplica a foto na máscara
    if foto:
        foto_cover = _cover_sem_corte(foto, W, H)
        canvas.paste(foto_cover, (0, 0), mask=mask_im)
        
    draw = ImageDraw.Draw(canvas)
    
    # ── 2. Conteúdo Textual Inferior ──
    y_texto_start = y_mask_start + (3 * step_y) + 40
    max_w = W - 140  # 70px de margem lateral
    
    # Linha discreta de categoria no topo
    draw.text((70, 42), f"ALL NEWS JOURNAL  •  {tema.upper()}", font=_lora(20, 600), fill=TEXTO_MUTED)
    
    cur_y = y_texto_start
    
    # Título (Playfair Display)
    if titulo_texto:
        f_tit = _playfair(46, weight=700)
        linhas_tit = _quebrar_texto(draw, titulo_texto, f_tit, max_w)
        for linha in linhas_tit[:3]:
            draw.text((70, cur_y), linha, font=f_tit, fill=CREME)
            cur_y += 56
        cur_y += 18
        
    # Corpo / Descrição (Lora)
    if corpo_texto:
        f_corpo = _lora(32, weight=400)
        linhas_corpo = _quebrar_texto(draw, corpo_texto, f_corpo, max_w)
        for linha in linhas_corpo:
            if cur_y + 44 > 1240:
                draw.text((70, cur_y), linha[:max(10, len(linha)-3)] + "...", font=f_corpo, fill=TEXTO_CORPO)
                break
            draw.text((70, cur_y), linha, font=f_corpo, fill=TEXTO_CORPO)
            cur_y += 44
            
    # ── 3. Indicadores de Carrossel (Dots) ──
    if total_slides > 1:
        raio = 5
        espacamento = 24
        largura_total = (total_slides - 1) * espacamento
        x_inicio_dots = (W - largura_total) // 2
        y_dots = 1290
        for s in range(total_slides):
            cx = x_inicio_dots + s * espacamento
            cor_dot = CREME if (s + 1) == slide_idx else (70, 70, 70)
            draw.ellipse([cx - raio, y_dots - raio, cx + raio, y_dots + raio], fill=cor_dot)
            
    return canvas

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
    memoria = carregar_memoria()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gerados = []

    print(f"   🔍 Processando {len(noticias)} notícias da edição {data_edicao}...")

    for i, item in enumerate(noticias, 1):
        tema, titulo, resumo, url_imagem = item["tema"], item["titulo"], item["resumo"], item["imagem"]
        
        # Garante a foto de alta qualidade (nunca None)
        foto = obter_foto_garantida(url_imagem, tema, idx_post=i, memoria=memoria)
        
        # Extrai palavras-chave de alto impacto
        keywords = extrair_keywords(titulo, resumo, tema)
        
        # Divide o resumo em partes para o carrossel narrativo (2 a 3 parágrafos)
        paragrafos = [p.strip() for p in re.split(r'\n+', resumo) if len(p.strip()) > 15]
        if not paragrafos:
            paragrafos = [resumo]
            
        p1 = paragrafos[0]
        p2 = paragrafos[1] if len(paragrafos) > 1 else ""
        p3 = paragrafos[2] if len(paragrafos) > 2 else ""

        # Montagem dos slides do Carrossel (3 slides narrativos + 1 slide CTA)
        slides = []
        total_slides = 3 if not p3 else 4
        
        # Slide 1: Hook principal (Palavra 1 + Título + Lead)
        s1 = gerar_slide_knockout(
            tema=tema,
            kw=keywords[0],
            titulo_texto=titulo,
            corpo_texto=p1,
            foto=foto,
            slide_idx=1,
            total_slides=total_slides
        )
        slides.append(s1)
        
        # Slide 2: Aprofundamento / Contexto (Palavra 2 + Antecedentes)
        texto_s2 = p2 if p2 else "A análise completa e os impactos desta cobertura chegam todas as manhãs no seu e-mail pelo All News Journal."
        s2 = gerar_slide_knockout(
            tema=tema,
            kw=keywords[1],
            titulo_texto="O CONTEXTO & OS FATOS",
            corpo_texto=texto_s2,
            foto=foto,
            slide_idx=2,
            total_slides=total_slides
        )
        slides.append(s2)
        
        # Slide 3: Desdobramentos ou CTA
        if p3 and total_slides == 4:
            s3 = gerar_slide_knockout(
                tema=tema,
                kw=keywords[2],
                titulo_texto="DESDOBRAMENTOS",
                corpo_texto=p3,
                foto=foto,
                slide_idx=3,
                total_slides=total_slides
            )
            slides.append(s3)
            
        # Slide Final: Fechamento com a marca
        s_final = gerar_slide_knockout(
            tema=tema,
            kw="ALL NEWS",
            titulo_texto="INFORMAÇÃO DIRETO AO PONTO",
            corpo_texto="Notícias completas e aprofundadas, entregues diariamente às 6h no seu e-mail. Cadastre-se gratuitamente pelo link na bio.",
            foto=foto,
            slide_idx=total_slides,
            total_slides=total_slides
        )
        slides.append(s_final)
        
        # Salva os arquivos de imagem
        paths = []
        for j, slide_img in enumerate(slides, 1):
            p = OUTPUT_DIR / f"post_{i:02d}_slide{j:02d}.jpg"
            slide_img.save(str(p), "JPEG", quality=94)
            paths.append(str(p))
            
        legenda = gerar_legenda(tema, titulo, resumo)
        gerados.append({"tema": tema, "paths": paths, "legenda": legenda})
        print(f"   🖼️  Carrossel {i} pronto: [{tema}] com {len(paths)} slides estilizados no padrão knockout.")

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
