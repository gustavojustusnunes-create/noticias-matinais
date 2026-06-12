import os
import sys
import time
import textwrap
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
import urllib.request
import tempfile
import numpy as np

from PIL import Image, ImageDraw

try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
        CompositeAudioClip, concatenate_audioclips, ColorClip
    )
except ImportError:
    print("MoviePy nao instalado. Execute: pip install moviepy")
    sys.exit(1)

from config import CORES_TEMA, ICONES_TEMA, FALLBACK_IMAGES

# Importando a identidade visual recém atualizada do instagram_diario
from instagram_diario import (
    slide_capa, _moldura, _masthead, _rotulo_caderno, 
    _playfair, _lora, _texto_espacado, _largura_espacado, 
    CREME, OURO, OURO_CLARO, INSTAGRAM_HANDLE, TURQUESA_DARK,
    DIAS, MESES
)

# =============================================================================
# --- VARIÁVEIS GLOBAIS E PASTAS ---
# =============================================================================
OUTPUT_DIR = Path(os.environ.get("VIDEO_OUTPUT_DIR", "assets/videos_gerados"))
TEMP_DIR = Path(tempfile.gettempdir()) / "all_news_journal_video"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_FILE = ASSETS_DIR / "news_ticker.mp3"

VOICE = "pt-BR-AntonioNeural" # Estilo âncora masculino

# =============================================================================
# --- FUNÇÕES AUXILIARES ---
# =============================================================================
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _baixar_e_processar(url: str, tema: str, nome_arquivo: str) -> Path:
    """Baixa e processa a imagem (Crop 9:16 e redimensionamento leve para Ken Burns)."""
    cor_hex = CORES_TEMA.get(tema, "0a5c5a")
    bg_path = TEMP_DIR / f"{nome_arquivo}.jpg"
    
    if url:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response, open(bg_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"   ⚠️ Erro ao baixar imagem {nome_arquivo}: {e}")
            img = Image.new("RGB", (1080, 1920), _hex_to_rgb(cor_hex))
            img.save(bg_path)
    else:
        img = Image.new("RGB", (1080, 1920), _hex_to_rgb(cor_hex))
        img.save(bg_path)
        
    img = Image.open(bg_path).convert("RGB")
    w, h = img.size
    target_ratio = 1080 / 1920
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
    
    # Redimensiona para dar espaço de sobra para o Ken Burns (1200x2133 em vez de 1080x1920)
    img = img.resize((1200, int(1200 / target_ratio)), Image.Resampling.LANCZOS)
    bg_path_processed = TEMP_DIR / f"{nome_arquivo}_processed.jpg"
    img.save(bg_path_processed, quality=95)
    return bg_path_processed

# =============================================================================
# --- GERAÇÃO DE ÁUDIO (TTS) ---
# =============================================================================
async def _gerar_tts(texto: str, arquivo_saida: Path):
    comando = [
        sys.executable, "-m", "edge_tts",
        "--voice", VOICE,
        "--rate=+20%",
        "--text", texto,
        "--write-media", str(arquivo_saida)
    ]
    proc = await asyncio.create_subprocess_exec(
        *comando,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    if proc.returncode != 0:
        print(f"❌ Erro ao gerar TTS para: {texto[:30]}...")

def gerar_audios(tema: str, titulo: str, resumo: str):
    intro_texto = f"All News Journal. Edição diária, caderno de {tema}."
    cta_texto = "Leia a edição completa e sem ruídos no seu e-mail. Assine gratuitamente no link da bio."
    
    arq_intro = TEMP_DIR / "intro.mp3"
    arq_tit = TEMP_DIR / "titulo.mp3"
    arq_res = TEMP_DIR / "resumo.mp3"
    arq_cta = TEMP_DIR / "cta.mp3"
    
    async def gerar_todos():
        await asyncio.gather(
            _gerar_tts(intro_texto, arq_intro),
            _gerar_tts(titulo, arq_tit),
            _gerar_tts(resumo, arq_res),
            _gerar_tts(cta_texto, arq_cta)
        )
    asyncio.run(gerar_todos())
    
    a_intro = AudioFileClip(str(arq_intro))
    a_tit = AudioFileClip(str(arq_tit))
    a_res = AudioFileClip(str(arq_res))
    a_cta = AudioFileClip(str(arq_cta))
    
    from moviepy.audio.AudioClip import AudioArrayClip
    sil_curto = AudioArrayClip(np.zeros((int(44100 * 0.3), 2)), fps=44100)
    sil_longo = AudioArrayClip(np.zeros((int(44100 * 0.5), 2)), fps=44100)
    
    audio_capa = concatenate_audioclips([a_intro, sil_longo])
    audio_noticia = concatenate_audioclips([a_tit, sil_longo, a_res, sil_curto, a_cta])
    
    return audio_capa, audio_noticia

# =============================================================================
# --- GERAÇÃO DE OVERLAYS VISUAIS ---
# =============================================================================
def gerar_overlay_transparente(tema: str, titulo: str, resumo: str) -> str:
    """Gera apenas o gradiente, bordas e textos em PNG transparente (Identidade Visual)."""
    W, H = 1080, 1920
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # 1. Gradiente Turquesa Translúcido (Baixo para Cima)
    base = tuple(int(c * 0.55) for c in TURQUESA_DARK)
    for y in range(H):
        t = y / H
        alpha = int(255 * (0.10 + 0.88 * (t ** 1.6)))
        draw.line([(0, y), (W, y)], fill=(*base, alpha))
        
    topo = int(H * 0.18)
    for y in range(topo):
        a = int(140 * (1 - y / topo))
        draw.line([(0, y), (W, y)], fill=(*TURQUESA_DARK, a))
        
    # 2. Moldura dupla dourada e Masthead
    _moldura(draw, W, H)
    px = 70
    _masthead(draw, W, px)
    
    # 3. Resumo em Lora (adaptativo, max 3 linhas)
    resumo = (resumo or "").strip()
    if len(resumo) > 200:
        corte = resumo[:200].rsplit(" ", 1)[0]
        resumo = corte + "…"
    linhas_resumo = textwrap.wrap(resumo, width=52)[:3] if resumo else []
    f_resumo, lh_resumo = _lora(28, 500), 38
    
    # 4. Título em Playfair (adaptativo)
    titulo = (titulo or "").strip()
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
    
    # 5. Rótulo do Tema
    selo = _rotulo_caderno(tema)
    draw.line([(px, y_titulo - 40), (px + 54, y_titulo - 40)], fill=OURO, width=3)
    _texto_espacado(draw, (px, y_titulo - 30), selo, _lora(24, 700), OURO_CLARO, tracking=4)
    
    # 6. Desenhar Textos Principais
    y = y_titulo
    for ln in linhas_t:
        draw.text((px, y), ln, font=f_t, fill=CREME)
        y += lh_t
        
    y = y_resumo
    for ln in linhas_resumo:
        draw.text((px, y), ln, font=f_resumo, fill=(235, 232, 226))
        y += lh_resumo
        
    # 7. Rodapé do Insta
    draw.line([(px, y_rodape - 16), (W - px, y_rodape - 16)], fill=OURO, width=1)
    _texto_espacado(draw, (px, y_rodape), INSTAGRAM_HANDLE.upper(), _lora(20, 500), OURO_CLARO, tracking=3)
    
    caminho = TEMP_DIR / "overlay_jornal.png"
    canvas.save(caminho, "PNG")
    return str(caminho)

# =============================================================================
# --- MONTAGEM DO VÍDEO COMPLETO ---
# =============================================================================
def criar_video(tema: str, titulo: str, resumo: str, url_fundo: str):
    print(f"🎬 Iniciando criação de vídeo Reel contínuo para: {tema}...")
    
    # 1. Gerar e Salvar Capa Estática
    agora = datetime.now()
    data_extenso = f"{DIAS[agora.weekday()]}, {agora.day} de {MESES[agora.month - 1]} de {agora.year}"
    capa_img = slide_capa(1080, 1920, data_extenso, caderno=tema)
    capa_path = TEMP_DIR / "capa.jpg"
    capa_img.save(capa_path, "JPEG", quality=95)
    
    # 2. Gerar Áudio Total
    print("   🎙️ Gerando locução completa...")
    audio_capa, audio_noticia = gerar_audios(tema, titulo, resumo)
    duracao_capa = audio_capa.duration
    duracao_noticia = audio_noticia.duration
    duracao_total = duracao_capa + duracao_noticia - 0.5 # Overlap na transição
    
    # 3. Preparar Imagens de Fundo
    print("   🔄 Baixando imagens de fundo e fallback para o movimento rotativo...")
    img1_path = _baixar_e_processar(url_fundo, tema, "bg_principal")
    
    import random
    fallback_urls = FALLBACK_IMAGES.get(tema, [])
    if isinstance(fallback_urls, list) and fallback_urls:
        amostra = random.sample(fallback_urls, min(2, len(fallback_urls)))
        url_bg2 = amostra[0]
        url_bg3 = amostra[1] if len(amostra) > 1 else url_bg2
    else:
        # Fallback de segurança legacy
        url_bg2 = fallback_urls if isinstance(fallback_urls, str) else url_fundo
        url_bg3 = url_fundo
        
    img2_path = _baixar_e_processar(url_bg2, tema, "bg_secundario")
    img3_path = _baixar_e_processar(url_bg3, tema, "bg_terciario")
    
    # 4. Construção dos Clipes MoviePy
    print("   🎥 Preparando Efeitos Ken Burns e Camadas...")
    
    # Capa Initial (Mostrada durante a locução de intro)
    clip_capa = ImageClip(str(capa_path)).set_duration(duracao_capa)
    
    # Background Animado: Intercalando as imagens para "rodam para dar impressão de movimento"
    # Animação de Pan/Zoom In
    def pan_in(get_frame, t):
        f = get_frame(t)
        # Move levemente o offset
        offset_x = int(0 + (1200 - 1080) * (t / duracao_noticia) / 2)
        offset_y = int(0 + (2133 - 1920) * (t / duracao_noticia) / 2)
        return f[offset_y:offset_y+1920, offset_x:offset_x+1080]
        
    # Animação de Pan/Zoom Out
    def pan_out(get_frame, t):
        f = get_frame(t)
        # Reversa: Inicia deslocado e vai voltando pro centro
        t_rev = duracao_noticia - t
        offset_x = int(0 + (1200 - 1080) * (t_rev / duracao_noticia) / 2)
        offset_y = int(0 + (2133 - 1920) * (t_rev / duracao_noticia) / 2)
        return f[offset_y:offset_y+1920, offset_x:offset_x+1080]

    # Dividimos a duração da notícia em 3 para mostrar as três imagens
    d_parte = duracao_noticia / 3
    
    c_bg1 = ImageClip(str(img1_path)).set_duration(d_parte + 1.0).fl(pan_in).set_position("center")
    
    c_bg2 = ImageClip(str(img2_path)).set_duration(d_parte + 1.0).fl(pan_out).set_position("center")
    c_bg2 = c_bg2.set_start(d_parte - 1.0).crossfadein(1.0)
    
    c_bg3 = ImageClip(str(img3_path)).set_duration(d_parte + 1.0).fl(pan_in).set_position("center")
    c_bg3 = c_bg3.set_start(d_parte * 2 - 1.0).crossfadein(1.0)
    
    # Overlay Estático e Transparente
    overlay_path = gerar_overlay_transparente(tema, titulo, resumo)
    c_overlay = ImageClip(overlay_path).set_duration(duracao_noticia).set_position("center")
    
    # Junta os fundos com o Overlay por cima (Esta é a parte 2 do vídeo)
    clip_noticia = CompositeVideoClip([c_bg1, c_bg2, c_bg3, c_overlay], size=(1080, 1920))
    clip_noticia = clip_noticia.set_duration(duracao_noticia).set_start(duracao_capa - 0.5).crossfadein(0.5)
    
    # Monta a Master
    video = CompositeVideoClip([clip_capa, clip_noticia], size=(1080, 1920))
    
    # Combina o Áudio Total
    audio_master = CompositeAudioClip([
        audio_capa.set_start(0),
        audio_noticia.set_start(duracao_capa - 0.5)
    ])
    
    # Adicionar Música de Fundo (Se houver)
    if MUSIC_FILE.exists():
        from moviepy.audio.fx.all import volumex
        musica = AudioFileClip(str(MUSIC_FILE))
        # Loop simplificado
        if musica.duration < duracao_total:
            pass
        musica = musica.subclip(0, min(musica.duration, duracao_total))
        musica = volumex(musica, 0.08) # 8% do volume para não ofuscar o âncora
        audio_master = CompositeAudioClip([audio_master, musica.set_start(0)])
        
    video = video.set_audio(audio_master)
    
    arquivo_saida = OUTPUT_DIR / f"{tema.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    print(f"   💾 Renderizando arquivo final: {arquivo_saida}")
    
    video.write_videofile(
        str(arquivo_saida),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast",
        logger=None # desativa logs poluidos do tqdm
    )
    
    print(f"✅ Vídeo estilo Reel contínuo gerado com sucesso em {arquivo_saida}")
    return arquivo_saida

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🎥 Teste Rápido do Video Builder (Estilo Capa de Jornal)")
    
    TEMA = "Economia"
    TITULO = ""
    RESUMO = ""
    URL_BG = ""
    
    try:
        import feeds
        from claude_api import extrair_contexto_base, chamar_claude_api
        print("   📡 Buscando notícia real do caderno Economia...")
        
        entries = feeds.coletar_entries_unico("Economia")
        if entries:
            entry = entries[0]
            TITULO_BASE = entry.get("title", "Economia Global")
            contexto = extrair_contexto_base(entry, max_chars=1500)
            
            prompt = (
                "Você é o âncora principal de um telejornal/podcast muito respeitado. "
                "Crie um roteiro aprofundado, analítico e de tom sério (aprox. 80-100 palavras) "
                "sobre a notícia abaixo. Vá direto aos fatos, sem saudações. "
                "O texto será lido por um sintetizador de voz (use pontuação para pausas). "
                f"\n\nTítulo Original: {TITULO_BASE}\nContexto: {contexto}"
            )
            resumo_ia = chamar_claude_api(prompt, max_tokens=300)
            
            if resumo_ia and len(resumo_ia.split()) > 20:
                RESUMO = resumo_ia.strip().strip('"')
                TITULO = TITULO_BASE
            else:
                print("   ⚠️ Sem IA. Usando texto base.")
                TITULO = TITULO_BASE
                RESUMO = contexto[:400].rsplit('.', 1)[0] + "."
                
            URL_BG = feeds.extrair_imagem_rss(entry, TEMA)
            
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar notícia real: {e}")
        
    if not TITULO or not RESUMO:
        print("   ⚠️ Usando texto de demonstração.")
        TITULO = "Banco Central eleva projeção de inflação para 2026 e alerta mercado"
        RESUMO = (
            "O cenário econômico brasileiro sofreu um forte abalo nesta manhã. "
            "O comitê central de política monetária divulgou uma revisão drástica em suas "
            "projeções de inflação para os próximos anos, apontando riscos fiscais e "
            "incertezas globais como os principais vetores de instabilidade. Analistas de "
            "mercado já precificam um ciclo prolongado de juros altos, o que impactou "
            "imediatamente a bolsa de valores."
        )
        URL_BG = "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1080&auto=format&fit=crop"

    criar_video(TEMA, TITULO, RESUMO, URL_BG)
