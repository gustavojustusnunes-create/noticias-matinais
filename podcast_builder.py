import os
import sys
import json
import re
import asyncio

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Tenta importar pydub para mixagem com silêncios
try:
    from pydub import AudioSegment
    PYDUB_OK = True
except ImportError:
    PYDUB_OK = False

from claude_api import chamar_claude_api

PODCAST_DIR = Path("edicoes/podcasts")
PODCAST_DIR.mkdir(parents=True, exist_ok=True)
RSS_FILE = PODCAST_DIR / "podcast.xml"

REPO_URL = "https://raw.githubusercontent.com/gustavojustusnunes-create/noticias-matinais/main"
PODCAST_TITLE = "All News Journal - Podcast Diário"
PODCAST_DESC = "Um resumo matinal ágil e descontraído das principais notícias do Brasil e do mundo, direto da curadoria do All News Journal."


def gerar_roteiro_editorial_fallback(cadernos_dict, data_str):
    """
    Gera um roteiro conversacional fluido entre Leo e Ana diretamente das matérias catalogadas,
    garantindo que o podcast NUNCA falhe, mesmo se a API de IA atingir limites momentâneos de cota.
    """
    linhas = [
        "LEO: Olá! Muito bom dia! Bem-vindo a mais uma edição em áudio do All News Journal.",
        f"ANA: Bom dia, Leo! E um excelente dia para quem nos acompanha nesta edição de {data_str}. Hoje nossa redação selecionou os acontecimentos mais relevantes para você começar o dia informado.",
        "LEO: Exatamente, Ana. Vamos direto aos destaques que estão movimentando os principais setores do Brasil e do mundo."
    ]

    temas_cobertos = 0
    for cad_nome, noticias in cadernos_dict.items():
        if cad_nome in ["data", "data_extenso", "editorial", "manchete"] or not isinstance(noticias, list) or not noticias:
            continue
        
        top_noticia = noticias[0]
        titulo = top_noticia.get("titulo", "").strip()
        resumo = re.sub(r'<[^>]+>', '', top_noticia.get("resumo", "")).strip()
        # Pega a primeira frase ou até 180 caracteres
        resumo_curto = resumo.split(". ")[0] if ". " in resumo else resumo[:180]

        if not titulo:
            continue

        temas_cobertos += 1
        if temas_cobertos % 2 == 1:
            linhas.append(f"LEO: No caderno de {cad_nome}, o principal destaque é: {titulo}.")
            if resumo_curto:
                linhas.append(f"ANA: Pois é, Leo. Segundo a cobertura, {resumo_curto}. Um desdobramento importante para acompanharmos de perto.")
        else:
            linhas.append(f"ANA: E no panorama de {cad_nome}, a manchete aponta que {titulo}.")
            if resumo_curto:
                linhas.append(f"LEO: Com certeza, Ana. As informações indicam que {resumo_curto}. Isso certamente vai repercutir ao longo do dia.")

        if temas_cobertos >= 6:
            break

    linhas.append("LEO: E essas foram as principais notícias da manhã curadas pela equipe do All News Journal.")
    linhas.append("ANA: Para ler as reportagens completas e personalizadas, acesse nossa edição completa no site. Tenha um ótimo dia e até a próxima edição!")
    linhas.append("LEO: Um grande abraço a todos e até amanhã!")

    return linhas


def gerar_roteiro(edicao):
    """
    Usa o Gemini para criar um roteiro dinâmico e natural de podcast,
    com fallback automático e garantido em caso de instabilidade na API.
    """
    hoje_str = edicao.get("data", datetime.now().strftime("%Y-%m-%d"))
    cadernos_dict = edicao.get("cadernos", edicao)
    
    texto_resumo = f"Edição de {hoje_str}\n\n"
    tem_noticias = False
    for caderno, noticias in cadernos_dict.items():
        if caderno in ["data", "data_extenso", "editorial", "manchete"] or not isinstance(noticias, list):
            continue
        texto_resumo += f"=== {caderno} ===\n"
        for n in noticias[:3]:
            tit = n.get("titulo", "")
            res = re.sub(r'<[^>]+>', '', n.get("resumo", ""))[:200]
            if tit:
                texto_resumo += f"- {tit}: {res}...\n"
                tem_noticias = True

    if not tem_noticias:
        return gerar_roteiro_editorial_fallback(cadernos_dict, hoje_str)

    prompt = (
        "Você é o roteirista do podcast diário de notícias 'All News Journal'.\n"
        "Com base nas notícias abaixo, escreva um roteiro de áudio dinâmico, natural e envolvente.\n\n"
        "REGRAS ESTRITAS:\n"
        "1. Apresentadores: LEO e ANA. Eles conversam de forma amigável, ágil e profissional.\n"
        "2. Eles apresentam as notícias intercalando as falas (um cita a manchete, o outro complementa com contexto).\n"
        "3. Não invente notícias inexistentes no texto.\n"
        "4. No final, eles se despedem convidando o ouvinte a ler a edição completa no site.\n"
        "5. O formato de saída DEVE ser estritamente linha por linha começando com 'LEO:' ou 'ANA:'. Exemplo:\n"
        "LEO: Olá, muito bom dia! Bem-vindo ao podcast do All News Journal.\n"
        "ANA: Bom dia, Leo! Hoje as notícias estão movimentando os mercados...\n\n"
        "NOTÍCIAS DE HOJE:\n"
        f"{texto_resumo}"
    )
    
    roteiro = None
    try:
        roteiro = chamar_claude_api(prompt, max_tokens=1500)
    except Exception as e:
        print(f"      ⚠️ Exceção ao chamar IA para roteiro: {e}")

    if not roteiro or not isinstance(roteiro, str) or len(roteiro.strip()) < 50:
        print("   ℹ️ Ativando roteirista editorial automático (fallback resiliente)...")
        return gerar_roteiro_editorial_fallback(cadernos_dict, hoje_str)

    linhas_finais = []
    for linha in roteiro.split("\n"):
        linha = linha.strip()
        if linha.startswith("LEO:") or linha.startswith("ANA:"):
            linhas_finais.append(linha)

    if len(linhas_finais) < 4:
        print("   ℹ️ Roteiro gerado pela IA incompleto: completando via fallback...")
        return gerar_roteiro_editorial_fallback(cadernos_dict, hoje_str)

    return linhas_finais


def gerar_audio_linha(texto, locutor, indice):
    """Gera um pequeno MP3 para a fala individual usando edge-tts."""
    import edge_tts
    
    voz = "pt-BR-AntonioNeural" if locutor == "LEO" else "pt-BR-FranciscaNeural"
    temp_file = PODCAST_DIR / f"temp_{indice}.mp3"

    async def _gravar():
        communicate = edge_tts.Communicate(texto, voz)
        await communicate.save(str(temp_file))

    try:
        asyncio.run(_gravar())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_gravar())
        loop.close()
        
    return temp_file


def atualizar_rss(mp3_filename, date_str, size_bytes):
    """Cria ou atualiza o podcast.xml com o novo episódio."""
    mp3_url = f"{REPO_URL}/edicoes/podcasts/{mp3_filename}"
    
    if RSS_FILE.exists():
        try:
            tree = ET.parse(RSS_FILE)
            rss = tree.getroot()
            channel = rss.find("channel")
        except Exception:
            channel = None
    else:
        channel = None

    if channel is None:
        rss = ET.Element("rss", version="2.0", attrib={"xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"})
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = PODCAST_TITLE
        ET.SubElement(channel, "link").text = "https://all-news-journal-ikgdbajp9nobmquagzvx3v.streamlit.app"
        ET.SubElement(channel, "description").text = PODCAST_DESC
        ET.SubElement(channel, "language").text = "pt-br"
        ET.SubElement(channel, "itunes:author").text = "All News Journal"
        ET.SubElement(channel, "itunes:category", text="News")
        
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = "https://raw.githubusercontent.com/gustavojustusnunes-create/noticias-matinais/main/assets/logo.png"
        ET.SubElement(image, "title").text = PODCAST_TITLE
        ET.SubElement(image, "link").text = "https://all-news-journal-ikgdbajp9nobmquagzvx3v.streamlit.app"
        
        owner = ET.SubElement(channel, "itunes:owner")
        ET.SubElement(owner, "itunes:name").text = "Gustavo Justus"
        ET.SubElement(owner, "itunes:email").text = "gustavojustusnunes@gmail.com"
        
    item = ET.Element("item")
    ET.SubElement(item, "title").text = f"Edição de {date_str}"
    ET.SubElement(item, "description").text = f"As notícias desta manhã: {date_str}. Apresentado por Leo e Ana."
    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "enclosure", url=mp3_url, length=str(size_bytes), type="audio/mpeg")
    ET.SubElement(item, "guid", isPermaLink="false").text = f"anj-{date_str}"
    
    channel.append(item)
    
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(xml_str)


def compilar_podcast(edicao):
    """Função principal: Roteiro -> Áudio TTS -> Merge MP3 -> RSS."""
    hoje_str = edicao.get("data", datetime.now().strftime("%Y-%m-%d"))
    final_mp3_name = f"podcast_{hoje_str}.mp3"
    final_mp3_path = PODCAST_DIR / final_mp3_name
    
    if final_mp3_path.exists() and os.path.getsize(final_mp3_path) > 1024:
        print(f"   🎧 Podcast já existe: {final_mp3_name}")
        return final_mp3_path

    print("   🎙️  Escrevendo roteiro do podcast...")
    linhas_roteiro = gerar_roteiro(edicao)
    if not linhas_roteiro:
        print("   ❌ Não foi possível gerar roteiro.")
        return None

    print(f"   🗣️  Sintetizando vozes neurais de Leo e Ana ({len(linhas_roteiro)} falas)...")
    arquivos_temporarios = []
    
    for i, linha in enumerate(linhas_roteiro):
        partes = linha.split(":", 1)
        if len(partes) != 2: 
            continue
        locutor = partes[0].strip().upper()
        texto   = partes[1].strip()
        
        try:
            temp_file = gerar_audio_linha(texto, locutor, i)
            if temp_file.exists() and os.path.getsize(temp_file) > 0:
                arquivos_temporarios.append(temp_file)
        except Exception as e:
            print(f"      ⚠️ Erro ao gerar fala {i}: {e}")

    if not arquivos_temporarios:
        print("   ❌ Nenhum áudio sintetizado.")
        return None

    print("   🎛️  Unificando faixas de áudio...")
    sucesso_merge = False
    if PYDUB_OK:
        try:
            podcast = AudioSegment.empty()
            for temp in arquivos_temporarios:
                segment = AudioSegment.from_mp3(str(temp))
                podcast += segment
                podcast += AudioSegment.silent(duration=250)
            podcast.export(str(final_mp3_path), format="mp3", bitrate="64k")
            sucesso_merge = True
        except Exception as err:
            print(f"      ℹ️ Pydub/ffmpeg indisponível ({err}), mesclando fluxo de áudio nativo...")

    if not sucesso_merge:
        # Fallback de fusão MP3 de baixo nível (válido para streams de áudio com mesmo codec)
        with open(final_mp3_path, "wb") as outfile:
            for temp in arquivos_temporarios:
                with open(temp, "rb") as infile:
                    outfile.write(infile.read())

    # Limpeza dos temporários
    for temp in arquivos_temporarios:
        try:
            temp.unlink()
        except Exception:
            pass

    size_bytes = os.path.getsize(final_mp3_path)
    print("   📡 Atualizando feed RSS do podcast...")
    try:
        atualizar_rss(final_mp3_name, hoje_str, size_bytes)
    except Exception as e:
        print(f"      ⚠️ Erro ao atualizar RSS: {e}")
    
    print(f"   ✅ Podcast finalizado com sucesso! {final_mp3_name} ({size_bytes/1024/1024:.1f} MB)")
    return final_mp3_path
