"""
claude_api.py — Camada de integração com a API Anthropic (Claude)
Inclui: chamada com retry/fallback, limpeza de texto RSS, extração de contexto base.
"""
import re
import time
import requests

from config import GEMINI_API_KEY


def chamar_claude_api(prompt, max_tokens=4096):
    """
    Chama a API do Google Gemini (mantendo o nome da função para retrocompatibilidade).
    """
    if not GEMINI_API_KEY:
        print("      ❌ GEMINI_API_KEY não definida.")
        return None

    headers = {
        "Content-Type": "application/json",
    }
    
    # Payload para a API do Gemini
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3
        }
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    print(f"      🤖 gemini-1.5-flash...")
    for tentativa in range(1, 4):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if r.status_code == 200:
                data = r.json()
                texto = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                # Extraindo contagem de tokens se disponível (Gemini as vezes fornece na raiz)
                usage = data.get("usageMetadata", {})
                print(f"      ✅ OK  in={usage.get('promptTokenCount','?')}  out={usage.get('candidatesTokenCount','?')}")
                return texto.strip()
                
            elif r.status_code == 429:
                espera = 20 * tentativa
                print(f"      ⏳ Rate-limit (Cota Grátis). Aguardando {espera}s…")
                time.sleep(espera)
            elif r.status_code == 400:
                print(f"      ❌ GEMINI_API_KEY inválida ou malformada.")
                return None
            else:
                print(f"      ⚠️ HTTP {r.status_code}: {r.text[:150]}")
                break
        except requests.exceptions.Timeout:
            print(f"      ⚠️ Timeout (90s) no gemini-1.5-flash.")
            break
        except Exception as e:
            print(f"      ⚠️ Exceção: {e}")
            break

    print("      ❌ O modelo Gemini falhou.")
    return None


def chamar_claude_haiku(prompt, max_tokens=300):
    """
    Alias para chamar_claude_api usando o mesmo modelo (gemini-1.5-flash é super rápido).
    Mantido para retrocompatibilidade.
    """
    return chamar_claude_api(prompt, max_tokens)


def limpar_texto_rss(texto):
    """Remove HTML, entidades, CTAs de engajamento e lixo de feeds RSS."""
    texto = re.sub(r"<[^>]+>", "", texto)

    entidades = {
        "&#8220;": '"', "&#8221;": '"', "&#8216;": "'", "&#8217;": "'",
        "&amp;": "&", "&quot;": '"', "&nbsp;": " ", "&#38;": "&",
        "&#8230;": "", "[&#8230;]": "", "[…]": "", "[...]": "",
    }
    for ent, sub in entidades.items():
        texto = texto.replace(ent, sub)

    # Rodapés WordPress
    texto = re.sub(
        r"\s*The post .+?appeared first on .+?\.?\s*", " ",
        texto, flags=re.DOTALL | re.IGNORECASE
    )
    texto = re.sub(r"\s*appeared first on .+", "", texto, flags=re.IGNORECASE)

    # CTAs e ruído de redes sociais
    padroes_cta = [
        r"✅\s*Siga\b.*",
        r"🔔\s*Siga\b.*",
        r"Siga\s+o\s+canal.*",
        r"Veja\s+no\s+vídeo\s+acima\.?",
        r"Acompanhe\s+as\s+notícias.*",
        r"Acompanhe\s+ao\s+vivo.*",
        r"Clique\s+aqui\s+e.*",
        r"Inscreva-se\s+no.*",
        r"Acesse\s+o\s+canal.*",
        r"Por:\s+[A-ZÀ-Ú][a-zà-ú]+\s+[A-ZÀ-Ú][a-zà-ú]+",
        r"nfoMoney\.?\s*$",
        r"Notícia\.\.\.",
        r"\[&#\d+;\]",
        # WordPress PT-BR "apareceu primeiro em"
        r"\s*O\s+post\s+.+?apareceu\s+primeiro\s+em\s+.+?\.?\s*",
        r"\s*apareceu\s+primeiro\s+em\s+.+",
        # CTAs de jornalismo (Estadão, g1, etc)
        r"Tem\s+alguma\s+sugestão\s+de\s+reportagem\?.*",
        r"Envie\s+para\s+o\s+WhatsApp.*",
        r"Ouça\s+o\s+podcast.*",
        # Resíduo de [&#8230;] e similares
        r"\[\s*\]",
        # "Leia também" + texto atrelado
        r"Leia\s+tamb[eé]m\s*[A-ZÀ-Úa-zà-ú].*?(?=\.|$)",
        # Créditos de foto entre parênteses
        r"\(Foto:\s*[^)]+\)",
        # Dateline Reuters/agências: "13 Abr (Reuters) –"
        r"^\d{1,2}\s+(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)\s+\([^)]+\)\s*[–—\-]\s*",
        # Créditos de imagem entre parênteses
        r"\(Imagem:\s*[^)]+\)",
        # Caracteres Unicode invisíveis (zero-width, BOM)
        r"[\u200b\u200c\u200d\u2060\ufeff]",
        # Emojis de CTA frequentes em feeds
        r"[📲💬🎯🔗]",
        # Lixo de newsletter e ofertas (Grupo Abril, etc)
        r"Você receberá nossa newsletter em breve.*",
        r"Newsletter(?:\s+Dicas\s+de)?.*?Inscreva-se.*?Cadastro efetuado com sucesso!?",
        r"Inscreva-se(?: aqui)? para receber a nossa newsletter.*",
        r"Aceito receber ofertas.*?Grupo Abril.*",
        r"E o melhor:\s*sem pagar nada por isso.*",
        r"Cadastro efetuado com sucesso!?",
        r"Assine a newsletter.*",
    ]
    for padrao in padroes_cta:
        texto = re.sub(padrao, " ", texto, flags=re.DOTALL | re.IGNORECASE)

    # Créditos de foto
    texto = re.sub(
        r"\b(Reuters|AFP|AP|EFE|G1|Globo|GE|Getty)[\s/][^\.\n]{0,60}",
        " ", texto, flags=re.IGNORECASE
    )

    # Remove perguntas no final do texto
    texto = re.sub(r"\s*[^.!?]+\?\s*$", ".", texto)

    texto = re.sub(r"\s*\.\.\.\s*$", ".", texto.strip())
    texto = re.sub(r"\s*…\s*$", ".", texto.strip())

    return re.sub(r"\s+", " ", texto).strip()


def remover_titulo_duplicado(titulo: str, corpo: str) -> str:
    """
    Remove repetição do título no início do corpo do texto.
    Resolve o padrão da Revista Quem e feeds que incluem título + texto no summary.
    """
    if not titulo or not corpo:
        return corpo
    titulo_norm = re.sub(r"\s+", " ", titulo.lower().strip())
    corpo_norm  = re.sub(r"\s+", " ", corpo.lower().strip())
    if corpo_norm.startswith(titulo_norm):
        corpo = corpo[len(titulo):].lstrip(".,;: \n")
    return corpo


def extrair_contexto_base(entry, max_chars: int = 800) -> str:
    """
    Extrai o melhor texto disponível da entrada RSS.
    Hierarquia: content > summary > description.
    Remove lixo e garante que termina em frase completa.
    """
    texto = ""
    if "content" in entry:
        for c in entry.content:
            texto += c.value
    if not texto.strip() and "summary" in entry:
        texto = entry.summary
    if not texto.strip():
        texto = entry.get("description", "")

    texto = limpar_texto_rss(texto)

    titulo = entry.get("title", "")
    if titulo:
        texto = remover_titulo_duplicado(titulo, texto)

    if len(texto) > max_chars:
        cortado      = texto[:max_chars]
        ultimo_ponto = max(cortado.rfind("."), cortado.rfind("!"), cortado.rfind("?"))
        if ultimo_ponto > max_chars // 2:
            cortado = cortado[: ultimo_ponto + 1]
        texto = cortado

    return texto.strip()


def limpar_resumo(texto: str) -> str:
    """Limpa markdown, numerações, artefatos e emojis do texto retornado pela IA."""
    texto = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", texto)
    texto = re.sub(r"^[\*\s]*Not[íi]cia\s*\d+[\:\.\s\*]*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"^\d+[\.\)]\s*", "", texto)
    
    # Remove emojis e símbolos pictográficos comuns usando ranges Unicode
    texto = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27BF\u2300-\u23FF\u2B50\u2139]', '', texto)
    
    texto = limpar_texto_rss(texto)
    texto = re.sub(r"\s*\.\.\.\s*$", ".", texto.strip())
    texto = re.sub(r"\s*…\s*$", ".", texto.strip())
    return texto.strip()

def gerar_keyword_imagem(texto: str) -> str:
    """Usa IA para gerar uma única palavra-chave em inglês para buscar uma imagem no Unsplash."""
    prompt = (
        f"Leia o texto abaixo e resuma o tema visual central em EXATAMENTE UMA PALAVRA em INGLÊS. "
        f"A palavra deve ser um substantivo visualizável e bom para busca de banco de imagens "
        f"(ex: business, technology, health, nature, politics). "
        f"Retorne APENAS a palavra e absolutamente mais nada.\n\n"
        f"Texto:\n{texto[:1000]}"
    )
    keyword = chamar_claude_api(prompt, max_tokens=10)
    if keyword:
        # Limpa qualquer aspa ou ponto
        keyword = re.sub(r"[^a-zA-Z]", "", keyword).strip().lower()
        if len(keyword) > 2:
            return keyword
    return "news"
