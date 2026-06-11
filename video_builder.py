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
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
        CompositeAudioClip, concatenate_audioclips, ColorClip
    )
except ImportError:
    print("MoviePy nao instalado. Execute: pip install moviepy")
    sys.exit(1)

from config import CORES_TEMA, ICONES_TEMA

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

# Voz da âncora (edge-tts)
# pt-BR-FranciscaNeural (Feminina), pt-BR-AntonioNeural (Masculino)
VOICE = "pt-BR-FranciscaNeural" 

# =============================================================================
# --- FUNÇÕES AUXILIARES DE CORES E FONTES ---
# =============================================================================
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _buscar_fonte(tamanho: int, negrito: bool = False):
    candidatas = []
    if negrito:
        candidatas = [
            "fonts/PlayfairDisplay.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
            "C:/Windows/Fonts/timesbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ]
    else:
        candidatas = [
            "fonts/Lora.ttf",
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    for caminho in candidatas:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except Exception:
                continue
    return ImageFont.load_default()

# =============================================================================
# --- GERAÇÃO DE ÁUDIO (TTS) ---
# =============================================================================
async def _gerar_tts(texto: str, arquivo_saida: Path):
    """Usa edge-tts via subprocess para gerar o áudio."""
    comando = [
        sys.executable, "-m", "edge_tts",
        "--voice", "pt-BR-AntonioNeural",
        "--rate=-10%",
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

def gerar_narracao(titulo: str, resumo: str) -> AudioFileClip:
    """Gera os trechos de áudio e os concatena com pausas."""
    arquivo_titulo = TEMP_DIR / "titulo.mp3"
    arquivo_resumo = TEMP_DIR / "resumo.mp3"
    arquivo_cta = TEMP_DIR / "cta.mp3"
    
    cta = "Leia a edição completa e sem ruídos no seu e-mail. Assine gratuitamente no link da bio."
    
    # Roda assíncrono para gerar os arquivos
    async def gerar_todos():
        await asyncio.gather(
            _gerar_tts(titulo, arquivo_titulo),
            _gerar_tts(resumo, arquivo_resumo),
            _gerar_tts(cta, arquivo_cta)
        )
    
    asyncio.run(gerar_todos())
    
    audio_t = AudioFileClip(str(arquivo_titulo))
    audio_r = AudioFileClip(str(arquivo_resumo))
    audio_c = AudioFileClip(str(arquivo_cta))
    
    from moviepy.audio.AudioClip import AudioArrayClip
    import numpy as np
    
    # Pausa de 0.5s
    # Criar clip de silencio (0.5s)
    silencio = AudioArrayClip(np.zeros((int(44100 * 0.5), 2)), fps=44100)
    
    # Concatena: Titulo -> Pausa -> Resumo -> Pausa curta -> CTA
    audio_final = concatenate_audioclips([audio_t, silencio, audio_r, silencio.subclip(0, 0.3), audio_c])
    
    return audio_final

# =============================================================================
# --- GERAÇÃO DE OVERLAYS (VISUAIS) ---
# =============================================================================
def gerar_overlay_base(tema: str, icone: str, cor_hex: str) -> str:
    """Cria uma imagem PNG transparente com o gradiente inferior e a faixa superior."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cor_rgb = _hex_to_rgb(cor_hex)
    
    # 1. Gradiente escuro de baixo para cima
    for i in range(1920):
        # Vai de 0 no y=0 até 220 no y=1920
        # Mas queremos que o escuro comece no y=1000 e fique bem escuro no rodapé
        if i > 1000:
            alpha = int(240 * ((i - 1000) / 920))
            draw.line([(0, i), (1080, i)], fill=(*cor_rgb[:], alpha))
            
    # 2. Faixa superior com 60% de opacidade
    faixa_cor = (*cor_rgb, int(255 * 0.6))
    draw.rectangle([(0, 0), (1080, 200)], fill=faixa_cor)
    
    # 3. Textos superiores
    fonte_logo = _buscar_fonte(45, negrito=True)
    draw.text((54, 40), "ALL NEWS JOURNAL", font=fonte_logo, fill=(255, 255, 255, 255))
    
    fonte_tema = _buscar_fonte(55, negrito=True)
    draw.text((54, 110), f"{icone} {tema.upper()}", font=fonte_tema, fill=(255, 255, 255, 255))
    
    # 4. Rodapé fixo
    draw.rectangle([(0, 1820), (1080, 1920)], fill=(0, 0, 0, 180))
    fonte_rodape = _buscar_fonte(35)
    draw.text((54, 1850), "@all.news.journal", font=fonte_rodape, fill=(220, 220, 220, 255))
    
    caminho_overlay = TEMP_DIR / "overlay_base.png"
    img.save(caminho_overlay)
    return str(caminho_overlay)

def desenhar_texto_sombra(texto: str, tamanho: int) -> str:
    """Cria uma imagem transparente com o texto centralizado dinâmico e sombra."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fonte = _buscar_fonte(tamanho, negrito=True)
    
    linhas = textwrap.wrap(texto, width=22)
    altura_linha = tamanho + 20
    altura_total = len(linhas) * altura_linha
    y_inicio = (1920 - altura_total) // 2
    
    for i, linha in enumerate(linhas):
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        largura_txt = bbox[2] - bbox[0]
        x = (1080 - largura_txt) // 2
        y = y_inicio + i * altura_linha
        
        # Sombra
        deslocamentos = [(3,3), (-3,-3), (3,-3), (-3,3), (0,4), (0,-4), (4,0), (-4,0)]
        for dx, dy in deslocamentos:
            draw.text((x + dx, y + dy), linha, font=fonte, fill=(0, 0, 0, 200))
        
        # Texto Principal
        draw.text((x, y), linha, font=fonte, fill=(255, 255, 255, 255))
        
    arquivo_temp = TEMP_DIR / f"texto_{hash(texto)}.png"
    img.save(arquivo_temp)
    return str(arquivo_temp)

# =============================================================================
# --- MONTAGEM DO VÍDEO ---
# =============================================================================
def criar_video(tema: str, titulo: str, resumo: str, url_fundo: str):
    print(f"🎬 Iniciando criação de vídeo para: {tema} - {titulo[:30]}...")
    
    # 1. Obter Ícone e Cor
    icone = ICONES_TEMA.get(tema, "📰")
    cor_hex = CORES_TEMA.get(tema, "0a5c5a")
    
    # 2. Baixar Imagem de Fundo
    print("   ⬇️ Baixando imagem de fundo...")
    bg_path = TEMP_DIR / "bg.jpg"
    try:
        req = urllib.request.Request(url_fundo, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(bg_path, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"   ⚠️ Erro ao baixar imagem: {e}")
        # Criar fundo sólido em caso de falha
        img = Image.new("RGB", (1080, 1920), _hex_to_rgb(cor_hex))
        img.save(bg_path)
        
    # Processar imagem de fundo (cortar para 9:16)
    img = Image.open(bg_path).convert("RGB")
    w, h = img.size
    target_ratio = 1080 / 1920
    current_ratio = w / h
    if current_ratio > target_ratio:
        # Imagem é mais larga -> cortar laterais
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        # Imagem é mais alta -> cortar topo/base
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
    
    # Redimensiona para ser ligeiramente maior que a tela para o Ken Burns
    img = img.resize((1200, int(1200 / target_ratio)), Image.Resampling.LANCZOS)
    bg_path_processed = TEMP_DIR / "bg_processed.jpg"
    img.save(bg_path_processed)
    
    # 3. Gerar Áudio
    print("   🎙️ Gerando narração TTS...")
    audio_narracao = gerar_narracao(titulo, resumo)
    duracao_total = audio_narracao.duration
    
    # 4. Música de Fundo
    audio_final = audio_narracao
    if MUSIC_FILE.exists():
        musica = AudioFileClip(str(MUSIC_FILE))
        # Loop na musica se for menor que o video
        from moviepy.audio.fx.all import volumex
        if musica.duration < duracao_total:
            # Isso é simplificado, o certo seria um loop, mas pra n complicar:
            pass
        musica = musica.subclip(0, min(musica.duration, duracao_total))
        musica = volumex(musica, 0.10) # 10% do volume
        audio_final = CompositeAudioClip([audio_narracao, musica])
        
    # 5. Efeito Ken Burns (Movimentação simples ao longo do tempo)
    print("   🎥 Preparando clipes e Ken Burns...")
    # Ao invés de resize dinâmico (muito lento), vamos usar crop dinâmico (Pan)
    bg_clip = ImageClip(str(bg_path_processed)).set_duration(duracao_total)
    
    def pan_zoom(get_frame, t):
        # A imagem tem 1200x2133, a tela é 1080x1920. 
        # Movemos do centro para uma das bordas suavemente
        frame = get_frame(t)
        # Corta a parte da imagem com base no t
        x_center = 1200 / 2
        y_center = 2133 / 2
        
        # Fator de zoom leve:
        # começa com 1200x2133 e termina exibindo uma janela menor (ex: 1080x1920)
        # Na verdade, basta cortar um 1080x1920 movendo o offset
        offset_x = int(0 + (1200 - 1080) * (t / duracao_total) / 2)
        offset_y = int(0 + (2133 - 1920) * (t / duracao_total) / 2)
        return frame[offset_y:offset_y+1920, offset_x:offset_x+1080]

    bg_clip = bg_clip.fl(pan_zoom)
    bg_clip = bg_clip.set_position("center")
    
    # 6. Sobreposições
    overlay_path = gerar_overlay_base(tema, icone, cor_hex)
    overlay_clip = ImageClip(overlay_path).set_duration(duracao_total)
    
    # 7. Textos Dinâmicos (Título no centro)
    # Mostraremos o título durante os primeiros 5 segundos
    path_txt = desenhar_texto_sombra(titulo, 75)
    duracao_titulo = min(6.0, duracao_total)
    txt_clip = ImageClip(path_txt).set_duration(duracao_titulo).crossfadeout(1.0)
    
    # Mostrar resumo aos poucos (fracionado em 2 partes se for longo)
    partes_resumo = textwrap.wrap(resumo, width=60)
    resumo_clips = []
    t_inicio = duracao_titulo - 0.5
    
    for i, p in enumerate(partes_resumo):
        d_p = (duracao_total - duracao_titulo - 4) / len(partes_resumo) # Reserva 4s pro CTA
        if d_p < 2: d_p = 2
        pt_path = desenhar_texto_sombra(p, 65)
        rc = ImageClip(pt_path).set_start(t_inicio).set_duration(d_p).crossfadein(0.5).crossfadeout(0.5)
        resumo_clips.append(rc)
        t_inicio += d_p
        
    # Compor tudo
    video = CompositeVideoClip(
        [bg_clip, overlay_clip, txt_clip] + resumo_clips,
        size=(1080, 1920)
    ).set_audio(audio_final)
    
    arquivo_saida = OUTPUT_DIR / f"{tema.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    print(f"   💾 Renderizando vídeo final: {arquivo_saida}")
    
    video.write_videofile(
        str(arquivo_saida),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast",
        logger=None # desativa a barra de progresso no console que polui o output
    )
    
    print(f"✅ Vídeo gerado com sucesso em {arquivo_saida}")
    return arquivo_saida

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🎥 Teste Rápido do Video Builder (Tom Sério/Telejornal)")
    
    TEMA = "Economia"
    TITULO = ""
    RESUMO = ""
    URL_BG = ""
    
    try:
        import feeds
        from claude_api import extrair_contexto_base, chamar_claude_api
        print("   📡 Buscando notícia real do caderno Economia para o teste...")
        
        # Coleta as entries de Economia
        entries = feeds.coletar_entries_unico("Economia")
        if entries:
            entry = entries[0]
            TITULO_BASE = entry.get("title", "Economia Global")
            # Extrai até 1500 caracteres do artigo real
            contexto = extrair_contexto_base(entry, max_chars=1500)
            
            # Tenta gerar um roteiro profissional via IA
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
                # Fallback sem IA: Usa o próprio texto base
                print("   ⚠️ Sem API Key ou erro na IA. Usando texto extraído diretamente do RSS.")
                TITULO = TITULO_BASE
                # Pega as primeiras frases (aprox 400 caracteres)
                RESUMO = contexto[:400].rsplit('.', 1)[0] + "."
                
            URL_BG = feeds.extrair_imagem_rss(entry, TEMA)
            print(f"   📰 Notícia escolhida: {TITULO[:50]}...")
            
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar notícia real: {e}")
        
    if not TITULO or not RESUMO:
        print("   ⚠️ Usando texto de demonstração estendido.")
        TITULO = "Banco Central eleva projeção de inflação para 2026 e alerta mercado"
        RESUMO = (
            "Boa noite. O cenário econômico brasileiro sofreu um forte abalo nesta manhã. "
            "O comitê central de política monetária divulgou uma revisão drástica em suas "
            "projeções de inflação para os próximos anos, apontando riscos fiscais e "
            "incertezas globais como os principais vetores de instabilidade. Analistas de "
            "mercado já precificam um ciclo prolongado de juros altos, o que impactou "
            "imediatamente a bolsa de valores, fechando em queda de mais de dois por cento. "
            "O dólar, como reflexo de proteção, disparou. Continuaremos acompanhando as "
            "consequências desta decisão."
        )
        URL_BG = "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1080&auto=format&fit=crop"

    if not MUSIC_FILE.exists():
        print("⚠️ Música de fundo não encontrada. O vídeo será gerado sem música.")
        
    criar_video(TEMA, TITULO, RESUMO, URL_BG)
