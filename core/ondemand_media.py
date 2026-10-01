"""
core/ondemand_media.py — Nó de Busca de Mídia & Renderização Gráfica (Node Media Retriever)
All News Journal (v2.2)

1. Busca em cascata inteligente de imagens em alta definição:
   - Wikimedia Commons API (namespace 6 de arquivos de mídia jornalística livre)
   - Unsplash API (se UNSPLASH_ACCESS_KEY presente)
   - Fallback para o banco editorial temático do jornal.
2. Renderização oficial no formato 1080x1350 (4:5):
   - Slide 1: Capa Clássica Executiva (vinheta petróleo #0C1B1A, moldura dourada e manchete em Playfair Display)
   - Slide 2: Conteúdo Brutalista Knockout com palavra-chave vazada e texto em Inter
   - Slide 3: Desdobramentos Estratégicos & CTA institucional
3. Exportação dos arquivos em edicoes/ondemand/{task_id}/.
"""

import os
import re
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from PIL import Image

from core.ondemand_state import OnDemandState
from instagram_poster import (
    gerar_slide,
    gerar_slide_capa,
    gerar_slide_conteudo,
    FALLBACK_IMAGENS_TEMA
)

OUTPUT_ONDEMAND_DIR = Path("edicoes") / "ondemand"


def _buscar_imagem_wikimedia(query: str) -> Optional[Dict[str, str]]:
    """Busca fotos jornalísticas e de líderes em alta definição no Wikimedia Commons."""
    try:
        q_enc = urllib.parse.quote(query)
        url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrsearch={q_enc}&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url|size|mime&format=json"
        )
        headers = {"User-Agent": "AllNewsJournal/2.2 (editorial@allnewsjournal.com)"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for pid, p in pages.items():
                imageinfo = p.get("imageinfo", [])
                if not imageinfo:
                    continue
                info = imageinfo[0]
                mime = info.get("mime", "").lower()
                img_url = info.get("url", "")
                width = info.get("width", 0)
                height = info.get("height", 0)
                
                # Aceita apenas JPEG/PNG com resolução de foto real (mínimo 600px)
                if ("jpeg" in mime or "png" in mime or img_url.lower().endswith((".jpg", ".jpeg", ".png"))) and (width >= 600 or height >= 600):
                    return {
                        "url": img_url,
                        "source": f"Wikimedia Commons ({p.get('title', '')})",
                        "width": width,
                        "height": height
                    }
    except Exception as e:
        print(f"   ⚠️ [media] Falha na busca Wikimedia ({e}).")
    return None


# Alias público para testes e consumo modular
buscar_imagem_wikimedia = _buscar_imagem_wikimedia


def _buscar_imagem_unsplash(query: str, access_key: str) -> Optional[Dict[str, str]]:
    """Busca foto em alta resolução no Unsplash se a chave estiver configurada."""
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": query, "per_page": 3, "orientation": "portrait"}
        headers = {"Authorization": f"Client-ID {access_key.strip()}"}
        resp = requests.get(url, params=params, headers=headers, timeout=6)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                foto = results[0]
                urls = foto.get("urls", {})
                return {
                    "url": urls.get("regular") or urls.get("full"),
                    "source": f"Unsplash (por {foto.get('user', {}).get('name', 'Fotógrafo')})",
                    "width": foto.get("width", 1080),
                    "height": foto.get("height", 1350)
                }
    except Exception as e:
        print(f"   ⚠️ [media] Falha na busca Unsplash ({e}).")
    return None


def obter_foto_em_cascata(query: str, tema: str) -> Image.Image:
    """Executa a busca em cascata de foto e retorna um objeto PIL.Image garantido."""
    foto_info = None

    # 1. Tenta Unsplash se chave configurada
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if unsplash_key:
        foto_info = _buscar_imagem_unsplash(query, unsplash_key)

    # 2. Tenta Wikimedia Commons (ideal para líderes, eventos e geopolítica)
    if not foto_info:
        foto_info = _buscar_imagem_wikimedia(query)

    # 3. Se achou URL, faz download
    if foto_info and foto_info.get("url"):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AllNewsJournal/2.2"}
            resp_img = requests.get(foto_info["url"], headers=headers, timeout=10)
            if resp_img.status_code == 200 and len(resp_img.content) > 10000:
                im = Image.open(BytesIO(resp_img.content)).convert("RGB")
                print(f"   📸 [media] Foto obtida com sucesso via {foto_info.get('source')}.")
                return im
        except Exception as e_down:
            print(f"   ⚠️ [media] Erro ao baixar foto remota ({e_down}). Acionando banco temático...")

    # 4. Fallback temático do jornal
    urls_fallback = FALLBACK_IMAGENS_TEMA.get(tema, FALLBACK_IMAGENS_TEMA["Mundo"])
    for fb_url in urls_fallback:
        try:
            resp_fb = requests.get(fb_url, timeout=8)
            if resp_fb.status_code == 200:
                im = Image.open(BytesIO(resp_fb.content)).convert("RGB")
                print(f"   📸 [media] Foto aplicada via banco temático editorial ({tema}).")
                return im
        except Exception:
            continue

    # Fallback extremo: gradiente preto e dourado
    im_pura = Image.new("RGB", (1080, 1350), (12, 27, 26))
    return im_pura


def node_media_retriever(state: OnDemandState) -> Dict[str, Any]:
    """
    Nó 4 do Subgrafo On-Demand: Media Retriever & Canvas Renderer
    Gera as peças visuais nos padrões estritos do All News Journal (1080x1350).
    """
    task_id = state.get("task_id", "ondemand_task")
    headline = state.get("headline", "DESTAQUE EDITORIAL")
    subtitulo = state.get("subtitulo", "Análise analítica profunda")
    keyword = state.get("keyword", "NOTÍCIA")
    slides_text = state.get("slides_text", [])
    tema = state.get("tema", "Mundo")
    image_query = state.get("image_query", headline)
    formato = state.get("formato", "carrossel")
    logs = list(state.get("execution_log", []))

    # 1. Obtém a foto em alta resolução
    foto = obter_foto_em_cascata(image_query, tema)

    # 2. Prepara diretório de saída
    target_dir = OUTPUT_ONDEMAND_DIR / task_id
    target_dir.mkdir(parents=True, exist_ok=True)

    slide_paths = []

    if formato == "card_unico" or len(slides_text) <= 1:
        # Card Único: Renderiza Slide 1 Capa Clássica
        s1 = gerar_slide(
            slide_idx=1,
            total_slides=1,
            tema=tema,
            titulo=headline,
            corpo=slides_text[0] if slides_text else "",
            kw=keyword,
            foto=foto,
            data_str="EDIÇÃO EXTRA"
        )
        p1 = target_dir / "slide_01.jpg"
        s1.save(str(p1), "JPEG", quality=95)
        slide_paths.append(str(p1))
    else:
        # Carrossel Editorial de 3 Slides
        total_slides = 3
        # Slide 1: Capa Clássica Oficial
        s1 = gerar_slide(
            slide_idx=1,
            total_slides=total_slides,
            tema=tema,
            titulo=headline,
            corpo="",
            kw=keyword,
            foto=foto,
            data_str="EDIÇÃO EXTRA"
        )
        p1 = target_dir / "slide_01.jpg"
        s1.save(str(p1), "JPEG", quality=95)
        slide_paths.append(str(p1))

        # Slide 2: Conteúdo Brutalista Knockout com o Fato
        s2 = gerar_slide(
            slide_idx=2,
            total_slides=total_slides,
            tema=tema,
            titulo=headline,
            corpo=slides_text[0],
            kw=keyword,
            foto=foto,
            data_str="EDIÇÃO EXTRA"
        )
        p2 = target_dir / "slide_02.jpg"
        s2.save(str(p2), "JPEG", quality=95)
        slide_paths.append(str(p2))

        # Slide 3: Desdobramentos Estratégicos & CTA
        s3 = gerar_slide(
            slide_idx=3,
            total_slides=total_slides,
            tema=tema,
            titulo="DESDOBRAMENTOS & IMPACTO",
            corpo=slides_text[1] if len(slides_text) > 1 else slides_text[0],
            kw="DESDOBRAMENTOS",
            foto=foto,
            data_str="EDIÇÃO EXTRA"
        )
        p3 = target_dir / "slide_03.jpg"
        s3.save(str(p3), "JPEG", quality=95)
        slide_paths.append(str(p3))

    logs.append({
        "node": "node_media_retriever",
        "message": f"{len(slide_paths)} slide(s) gerado(s) com sucesso em '{target_dir}'.",
        "slide_paths": slide_paths
    })

    return {
        "slide_paths": slide_paths,
        "execution_log": logs
    }
