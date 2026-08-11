import os
import json
import re
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Tenta importar pydub e google.cloud
try:
    from pydub import AudioSegment
    from google.oauth2 import service_account
    from google.cloud import texttospeech
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

from claude_api import chamar_claude_api
from config import GCP_JSON

PODCAST_DIR = Path("edicoes/podcasts")
PODCAST_DIR.mkdir(parents=True, exist_ok=True)
RSS_FILE = PODCAST_DIR / "podcast.xml"

REPO_URL = "https://raw.githubusercontent.com/gustavojustusnunes-create/noticias-matinais/main"
PODCAST_TITLE = "All News Journal - Podcast Diário"
PODCAST_DESC = "Um resumo matinal ágil e descontraído das principais notícias do Brasil e do mundo, direto da curadoria do All News Journal."

def gerar_roteiro(edicao):
    """
    Usa o Gemini/Claude para transformar as notícias do dia em um roteiro teatral de podcast.
    """
    hoje_str = edicao.get("data", datetime.now().strftime("%Y-%m-%d"))
    
    # Monta um super-resumo de texto para o LLM não estourar tokens desnecessários
    texto_resumo = f"Edição de {hoje_str}\n\n"
    for caderno, noticias in edicao.items():
        if caderno == "data" or not isinstance(noticias, list): continue
        texto_resumo += f"=== {caderno} ===\n"
        for n in noticias[:3]: # Pega as 3 principais de cada caderno
            texto_resumo += f"- {n.get('titulo')}: {n.get('resumo', '')[:200]}...\n"

    prompt = (
        "Você é o roteirista de um podcast diário de notícias chamado 'All News Journal'.\n"
        "Com base nas notícias fornecidas abaixo, escreva um roteiro de áudio com duração "
        "estimada de 5 a 8 minutos, sendo bem denso, aprofundado e rico em detalhes.\n\n"
        "REGRAS:\n"
        "1. Apresentadores: LEO e ANA. Eles são simpáticos, dinâmicos e conversam entre si.\n"
        "2. Eles devem apresentar as notícias principais, um complementando a fala do outro, "
        "trazendo análises, contexto e reações naturais (ex: 'Nossa', 'Pois é', 'É verdade').\n"
        "3. Não invente notícias que não estão no texto.\n"
        "4. No final, eles se despedem desejando um ótimo dia e pedem para o ouvinte ler a edição completa.\n"
        "5. O formato de saída DEVE ser estritamente linha por linha começando com o nome. Exemplo:\n"
        "LEO: Olá, muito bom dia! Bem-vindo a mais um podcast do All News Journal.\n"
        "ANA: Bom dia, Leo! Hoje as notícias estão fervendo...\n"
        "\nNOTÍCIAS DE HOJE:\n"
        f"{texto_resumo}"
    )
    
    roteiro = chamar_claude_api(prompt, max_tokens=1500)
    
    # Filtra apenas linhas válidas do roteiro
    linhas_finais = []
    for linha in roteiro.split("\n"):
        linha = linha.strip()
        if linha.startswith("LEO:") or linha.startswith("ANA:"):
            linhas_finais.append(linha)
    
    return linhas_finais


def inicializar_tts():
    """Retorna True para indicar que o TTS está disponível (edge-tts não precisa de init)."""
    return True


def gerar_audio_linha(client, texto, locutor, indice):
    """Gera um pequeno MP3 para a fala individual usando edge-tts."""
    import edge_tts
    import asyncio
    
    if locutor == "LEO":
        voz = "pt-BR-AntonioNeural"
    else:
        voz = "pt-BR-FranciscaNeural"
        
    temp_file = PODCAST_DIR / f"temp_{indice}.mp3"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    communicate = edge_tts.Communicate(texto, voz)
    loop.run_until_complete(communicate.save(str(temp_file)))
        
    return temp_file


def atualizar_rss(mp3_filename, date_str, size_bytes):
    """Cria ou atualiza o podcast.xml com o novo episódio."""
    mp3_url = f"{REPO_URL}/edicoes/podcasts/{mp3_filename}"
    
    if RSS_FILE.exists():
        tree = ET.parse(RSS_FILE)
        rss = tree.getroot()
        channel = rss.find("channel")
    else:
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
    
    # Insere no topo da lista
    channel.insert(list(channel).index(channel.find("title")) + 5, item)
    
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    # Limpa linhas vazias do minidom
    xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(xml_str)


def compilar_podcast(edicao):
    """Função principal: Roteiro -> Áudio TTS -> Merge MP3 -> RSS."""
    if not AUDIO_OK:
        print("   ❌ Dependências de áudio ausentes. Rode: pip install pydub google-cloud-texttospeech")
        return None
        
    hoje_str = edicao.get("data", datetime.now().strftime("%Y-%m-%d"))
    final_mp3_name = f"podcast_{hoje_str}.mp3"
    final_mp3_path = PODCAST_DIR / final_mp3_name
    
    if final_mp3_path.exists():
        print(f"   🎧 Podcast já existe: {final_mp3_name}")
        return final_mp3_path

    print("   🎙️  Escrevendo roteiro do podcast...")
    linhas_roteiro = gerar_roteiro(edicao)
    if len(linhas_roteiro) < 5:
        print("   ❌ Roteiro gerado é muito curto ou inválido.")
        return None
        
    client = inicializar_tts()
    if not client:
        return None

    print(f"   🗣️  Gravando as vozes ({len(linhas_roteiro)} falas)...")
    arquivos_temporarios = []
    
    for i, linha in enumerate(linhas_roteiro):
        partes = linha.split(":", 1)
        if len(partes) != 2: continue
        locutor = partes[0].strip().upper()
        texto   = partes[1].strip()
        
        try:
            temp_file = gerar_audio_linha(client, texto, locutor, i)
            arquivos_temporarios.append(temp_file)
        except Exception as e:
            print(f"      ⚠️ Erro ao gerar fala {i}: {e}")

    if not arquivos_temporarios:
        print("   ❌ Nenhum áudio gerado.")
        return None

    print("   🎛️  Mixando áudio (pydub)...")
    podcast = AudioSegment.empty()
    for temp in arquivos_temporarios:
        segment = AudioSegment.from_mp3(str(temp))
        podcast += segment
        # Adiciona 0.3 segundos de pausa entre as falas para respirar
        podcast += AudioSegment.silent(duration=300) 
        
    podcast.export(str(final_mp3_path), format="mp3", bitrate="64k")
    
    # Limpeza
    for temp in arquivos_temporarios:
        try:
            temp.unlink()
        except:
            pass

    size_bytes = os.path.getsize(final_mp3_path)
    print("   📡 Atualizando feed RSS do Spotify...")
    atualizar_rss(final_mp3_name, hoje_str, size_bytes)
    
    print(f"   ✅ Podcast finalizado! {final_mp3_name} ({size_bytes/1024/1024:.1f} MB)")
    return final_mp3_path
