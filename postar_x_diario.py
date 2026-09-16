"""
postar_x_diario.py — Esteira de Publicação Automatizada no X (Twitter)
All News Journal (v1.0)

Orquestra:
1. Leitura do snapshot diário em edicoes/ (YYYY-MM-DD.json).
2. Curadoria estrita dos cadernos nobres: apenas "IA" ou "Economia" (exclui Política/Fofoca).
3. Seleção da matéria de maior relevância de mercado/tecnologia.
4. Geração de copy analítico de alto impacto via Google Gemini Flash (<= 240 caracteres).
5. Upload da imagem da Capa Editorial Clássica (Slide 1) via Tweepy (OAuth 1.0a).
6. Disparo do tweet principal com mídia anexada via Tweepy (API v2).
7. Espera de 12 segundos e publicação de auto-reply de conversão encadeado.
8. Tratamento resiliente de erros com registro em logs/x_post_errors.log.
"""

import os
import sys
import json
import time
import glob
import re
import argparse
import traceback
from datetime import datetime
from pathlib import Path

# Ajuste de encoding no terminal Windows
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =============================================================================
# --- CONFIGURAÇÃO & VARIÁVEIS DE AMBIENTE ---
# =============================================================================
GEMINI_API_KEY        = os.environ.get("GEMINI_API_KEY", "").strip()
X_API_KEY             = os.environ.get("X_API_KEY", "").strip()
X_API_SECRET          = os.environ.get("X_API_SECRET", "").strip()
X_ACCESS_TOKEN        = os.environ.get("X_ACCESS_TOKEN", "").strip()
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()
X_BEARER_TOKEN        = os.environ.get("X_BEARER_TOKEN", "").strip()

EDICOES_DIR           = Path("edicoes")
IMAGENS_DIR           = EDICOES_DIR / "imagens"
LOGS_DIR              = Path("logs")
ERROR_LOG_FILE        = LOGS_DIR / "x_post_errors.log"

AUTO_REPLY_TEXT = (
    "A análise completa desta e de outras notícias essenciais foi enviada hoje às 06:15 para nossos leitores.\n\n"
    "Receba as próximas edições em 4 minutos matinais:\n"
    "https://all-news-journal-ikgdbajp9nobmquagzvx3v.streamlit.app/?utm_source=x&utm_medium=organic&utm_campaign=daily_debate"
)

# =============================================================================
# --- LOGS & RESILIÊNCIA ---
# =============================================================================
def registrar_erro(mensagem: str, exc: Exception = None):
    """Grava mensagem de erro com timestamp no log de erros do X."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{agora}] ❌ {mensagem}\n"
    if exc:
        linha += f"{traceback.format_exc()}\n"
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha)
    except Exception as e:
        print(f"⚠️ Falha ao gravar log de erro: {e}")
    print(f"❌ {mensagem}", file=sys.stderr)

def registrar_sucesso(log_dict: dict):
    """Salva registro de publicação bem-sucedida."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    hist_file = LOGS_DIR / "x_posts_history.json"
    historico = []
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                historico = json.load(f)
        except Exception:
            historico = []
    historico.append(log_dict)
    try:
        with open(hist_file, "w", encoding="utf-8") as f:
            json.dump(historico[-100:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Falha ao salvar histórico do X: {e}")

# =============================================================================
# --- 1. LEITURA DO SNAPSHOT DIÁRIO ---
# =============================================================================
def carregar_edicao_alvo(data_especifica: str = None) -> tuple[dict, str]:
    """
    Localiza o arquivo JSON da edição em edicoes/ (ex: 2026-09-15.json).
    Se data_especifica não for informada, busca a de hoje ou a mais recente.
    """
    if data_especifica:
        p = EDICOES_DIR / f"{data_especifica}.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), data_especifica

    hoje_str = datetime.now().strftime("%Y-%m-%d")
    p_hoje = EDICOES_DIR / f"{hoje_str}.json"
    if p_hoje.exists():
        with open(p_hoje, "r", encoding="utf-8") as f:
            return json.load(f), hoje_str

    # Busca o arquivo mais recente
    arquivos = sorted(glob.glob(str(EDICOES_DIR / "????-??-??.json")), reverse=True)
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo de edição encontrado em edicoes/")

    mais_recente = arquivos[0]
    data_detectada = Path(mais_recente).stem
    with open(mais_recente, "r", encoding="utf-8") as f:
        return json.load(f), data_detectada

# =============================================================================
# --- 2. CURADORIA & SELEÇÃO DE CADERNOS NOBRES ---
# =============================================================================
def selecionar_materia_nobre(edicao_dados: dict) -> tuple[str, dict]:
    """
    Filtra estritamente os cadernos 'IA' e 'Economia'.
    Exclui categoricamente 'Politica' e 'Fofoca'.
    Se ambos existirem, prioriza a matéria de maior relevância de mercado/tecnologia.
    """
    cadernos = edicao_dados.get("cadernos", {})
    candidatas = []

    # Coleta matérias válidas exclusivamente de IA e Economia
    for tema in ["IA", "Economia"]:
        itens = cadernos.get(tema, [])
        for item in itens:
            if item.get("titulo") and item.get("resumo"):
                candidatas.append({
                    "tema": tema,
                    "item": item
                })

    if not candidatas:
        raise ValueError("Nenhuma matéria encontrada nos cadernos nobres ('IA' ou 'Economia').")

    if len(candidatas) == 1:
        c = candidatas[0]
        return c["tema"], c["item"]

    # Se houver mais de uma, ranquear por relevância de mercado/tecnologia
    # Palavras-chave de alto impacto de mercado, investimentos e disrupção
    palavras_peso = [
        "bilh", "milh", "mercado", "invest", "brics", "eua", "china", "fed", "juros",
        "lucro", "receita", "regul", "chip", "nvidia", "openai", "anthropic", "modelo",
        "segurança", "patente", "aquisição", "compra", "cade", "banco", "código aberto"
    ]

    melhor_cand = candidatas[0]
    maior_score = -1

    for cand in candidatas:
        t = cand["item"].get("titulo", "").lower()
        r = cand["item"].get("resumo", "").lower()
        texto_completo = f"{t} {r}"
        score = sum(texto_completo.count(k) for k in palavras_peso)
        # Bônus se tiver números e porcentagens
        score += len(re.findall(r"\d+[%]?", texto_completo)) * 2
        # Prioridade sutil para temas que abrem debates regulatórios ou econômicos
        if "código aberto" in texto_completo or "desligar" in texto_completo or "tesouro" in texto_completo:
            score += 5

        if score > maior_score:
            maior_score = score
            melhor_cand = cand

    print(f"   🏆 Matéria nobre selecionada: [{melhor_cand['tema']}] {melhor_cand['item'].get('titulo')[:60]}... (Score: {maior_score})")
    return melhor_cand["tema"], melhor_cand["item"]

# =============================================================================
# --- 3. ENGENHARIA DE PROMPT (GEMINI FLASH) ---
# =============================================================================
SYSTEM_INSTRUCTION_X = (
    "Você é o editor de distribuição e growth do All News Journal no X. "
    "Transforme o fato jornalístico fornecido em um post de alto impacto focado em abrir um debate analítico.\n\n"
    "DIRETRIZES ESTRITAS:\n"
    "1. Tamanho do texto: No máximo 240 caracteres no corpo principal.\n"
    "2. Estrutura do Post:\n"
    "   - Linha 1: Tese central ou o indicador numérico mais contundente do fato (sem emojis exagerados).\n"
    "   - Linha 2-3: Contexto sintético do dilema (tensão de mercado, choque regulatório ou quem ganha vs. quem perde).\n"
    "   - Linha final: Uma pergunta provocativa aberta convidando investidores/profissionais a debaterem.\n"
    "3. Restrições:\n"
    "   - NÃO inclua links no post principal (para não sofrer penalização de alcance algorítmico).\n"
    "   - NÃO use hashtags genéricas (#noticias, #brasil). Use no máximo uma tag de contexto (#IA ou #Economia).\n"
    "   - Tom de voz: Analítico, direto, sóbrio e instigante."
)

def gerar_copy_x(tema: str, titulo: str, resumo: str) -> str:
    """
    Invoca o Google Gemini Flash para gerar o texto do tweet principal (<= 240 caracteres).
    """
    tag = f"#{tema}" if tema in ["IA", "Economia"] else "#IA"

    prompt_usuario = (
        f"Matéria:\n"
        f"Caderno: {tema}\n"
        f"Título: {titulo}\n"
        f"Contexto: {resumo}\n\n"
        f"Gere o tweet analítico no padrão exato solicitado, com no máximo 240 caracteres no total. "
        f"Termine com a pergunta instigante e a tag {tag}."
    )

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)

            modelos = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.5-flash"]
            for m_nome in modelos:
                try:
                    model = genai.GenerativeModel(
                        m_nome,
                        system_instruction=SYSTEM_INSTRUCTION_X
                    )
                    resp = model.generate_content(
                        prompt_usuario,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=180,
                            temperature=0.3
                        ),
                        request_options={"timeout": 30}
                    )
                    if resp and resp.text:
                        texto = resp.text.strip()
                        # Validação de tamanho <= 240 caracteres
                        if len(texto) <= 240:
                            return texto
                        # Se ultrapassou levemente, remove quebras excessivas ou ajusta
                        linhas = [l.strip() for l in texto.split("\n") if l.strip()]
                        texto_enxuto = "\n".join(linhas)
                        if len(texto_enxuto) <= 240:
                            return texto_enxuto
                        # Tenta reduzir o excesso
                        return texto_enxuto[:237] + "..."
                except Exception as e_m:
                    continue
        except Exception as e:
            print(f"      ⚠️ Falha na API Gemini: {e}")

    # Fallback estruturado de alta qualidade caso o Gemini esteja indisponível
    print("      ℹ️ Utilizando gerador determinístico editorial de fallback.")
    titulo_curto = titulo[:75].rstrip()
    if not titulo_curto.endswith("."):
        titulo_curto += "."
    copy_fb = f"{titulo_curto}\nO avanço acirra a disputa regulatória e de capital entre gigantes globais.\nQual o impacto real para os players locais? {tag}"
    if len(copy_fb) > 240:
        copy_fb = copy_fb[:237] + "..."
    return copy_fb

# =============================================================================
# --- 4. GESTÃO DO ATIVO VISUAL (SLIDE 1 CAPA CLÁSSICA) ---
# =============================================================================
def obter_ou_gerar_capa(data_str: str, tema: str, titulo: str, url_foto: str) -> Path:
    """
    Localiza o arquivo de imagem do Slide 1 (Capa Editorial Clássica).
    Se ainda não existir em disco, gera em edicoes/imagens/capa_{data_str}.jpg
    reaproveitando o motor visual do Instagram Poster.
    """
    IMAGENS_DIR.mkdir(parents=True, exist_ok=True)
    caminho_capa = IMAGENS_DIR / f"capa_{data_str}.jpg"

    if caminho_capa.exists() and caminho_capa.stat().st_size > 1000:
        print(f"   🖼️  Capa pré-existente localizada: {caminho_capa}")
        return caminho_capa

    # Procura em saídas anteriores do carrossel
    candidatos = [
        IMAGENS_DIR / f"capa_{data_str}_{tema}.jpg",
        Path("preview_carrossel") / "slide_1_capa.jpg",
        Path(os.environ.get("INSTAGRAM_OUTPUT_DIR", "/tmp/instagram_posts")) / "post_01_slide01.jpg",
        Path("preview_insta") / "teste_1_slide1_capa.jpg"
    ]
    for c in candidatos:
        if c.exists() and c.stat().st_size > 1000:
            print(f"   🖼️  Reaproveitando capa de: {c}")
            import shutil
            shutil.copy2(c, caminho_capa)
            return caminho_capa

    # Gera a Capa Editorial Clássica diretamente
    print(f"   🎨 Gerando Capa Editorial Clássica para a matéria de {tema}...")
    try:
        from instagram_poster import gerar_slide_capa, obter_foto_garantida
        from PIL import Image

        dt = datetime.strptime(data_str, "%Y-%m-%d")
        data_formatada = dt.strftime("%d.%m.%Y")

        foto = None
        if url_foto:
            try:
                foto = obter_foto_garantida(url_foto, tema)
            except Exception:
                foto = None

        img_capa = gerar_slide_capa(
            tema=tema,
            manchete=titulo,
            foto=foto,
            data_str=data_formatada,
            total_slides=3
        )
        img_capa.save(str(caminho_capa), "JPEG", quality=94)
        print(f"   ✅ Capa gerada e salva com sucesso: {caminho_capa}")
        return caminho_capa
    except Exception as e:
        registrar_erro(f"Falha ao gerar capa via instagram_poster: {e}", e)
        # Se falhar, tenta criar um card simples de emergência com Pillow
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1080, 1350), (12, 27, 26))
            draw = ImageDraw.Draw(img)
            draw.rectangle([32, 32, 1080 - 32, 1350 - 32], outline=(209, 186, 115), width=2)
            draw.text((60, 60), "ALL NEWS JOURNAL", fill=(255, 255, 255))
            draw.text((60, 120), f"CADERNO: {tema.upper()}", fill=(209, 186, 115))
            img.save(str(caminho_capa), "JPEG", quality=90)
            return caminho_capa
        except Exception as e_pil:
            raise RuntimeError(f"Não foi possível obter ou gerar imagem da capa: {e_pil}")

# =============================================================================
# --- 5. PIPELINE DE PUBLICAÇÃO VIA TWEEPY (V1.1 + V2) ---
# =============================================================================
def autenticar_tweepy() -> tuple[object, object]:
    """
    Retorna (api_v1, client_v2) autenticados no X.
    """
    import tweepy

    # Validação de variáveis obrigatórias
    chaves = {
        "X_API_KEY": X_API_KEY,
        "X_API_SECRET": X_API_SECRET,
        "X_ACCESS_TOKEN": X_ACCESS_TOKEN,
        "X_ACCESS_TOKEN_SECRET": X_ACCESS_TOKEN_SECRET,
        "X_BEARER_TOKEN": X_BEARER_TOKEN
    }
    faltantes = [k for k, v in chaves.items() if not v]
    if faltantes:
        raise ValueError(f"Chaves do X ausentes: {', '.join(faltantes)}")

    # API v1.1 para upload de imagens (media_upload)
    auth = tweepy.OAuth1UserHandler(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET
    )
    api_v1 = tweepy.API(auth)

    # API v2 para postagem de tweets e replies
    client_v2 = tweepy.Client(
        bearer_token=X_BEARER_TOKEN,
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET
    )

    return api_v1, client_v2

def publicar_no_x(texto_tweet: str, caminho_imagem: Path, dry_run: bool = False) -> bool:
    """
    Executa a esteira de publicação:
    1. Upload da Capa Editorial (API v1.1).
    2. Tweet principal com mídia (API v2).
    3. Delay de 12 segundos.
    4. Auto-reply encadeado com link UTM de conversão.
    """
    print(f"\n📝 Post Principal ({len(texto_tweet)} caracteres):")
    print("─" * 60)
    print(texto_tweet)
    print("─" * 60)

    print(f"\n💬 Auto-Reply Encadeado:")
    print("─" * 60)
    print(AUTO_REPLY_TEXT)
    print("─" * 60)

    if dry_run:
        print("\n🧪 [MODO DRY-RUN] Postagem simulada com sucesso (nenhum tweet real foi enviado).")
        preview = {
            "timestamp": datetime.now().isoformat(),
            "tweet_principal": texto_tweet,
            "caracteres": len(texto_tweet),
            "imagem": str(caminho_imagem),
            "auto_reply": AUTO_REPLY_TEXT,
            "status": "SIMULADO_OK"
        }
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOGS_DIR / "x_preview.json", "w", encoding="utf-8") as f:
            json.dump(preview, f, indent=2, ensure_ascii=False)
        return True

    # Checagem graciosa de credenciais
    if not (X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET and X_BEARER_TOKEN):
        msg_aviso = "⚠️ Credenciais do X (Twitter) não configuradas no ambiente. Postagem ignorada sem falhar a pipeline."
        print(f"\n{msg_aviso}")
        registrar_erro(msg_aviso)
        return True

    import tweepy

    try:
        print("\n🔐 Autenticando na API do X...")
        api_v1, client_v2 = autenticar_tweepy()

        print(f"📤 Fazendo upload da imagem da Capa ({caminho_imagem})...")
        media = api_v1.media_upload(filename=str(caminho_imagem))
        media_id = media.media_id
        print(f"   ✅ Mídia carregada com sucesso (Media ID: {media_id})")

        print("🚀 Publicando Tweet principal...")
        resp_tweet = client_v2.create_tweet(
            text=texto_tweet,
            media_ids=[media_id]
        )
        tweet_id = resp_tweet.data.get("id")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        print(f"   ✅ Tweet principal publicado: {tweet_url}")

        # Delay anti-bot / anti-penalização algorítmica
        print("⏳ Aguardando delay de 12 segundos para encadeamento natural...")
        time.sleep(12)

        print("🔗 Publicando Auto-Reply encadeado de conversão...")
        resp_reply = client_v2.create_tweet(
            text=AUTO_REPLY_TEXT,
            in_reply_to_tweet_id=tweet_id
        )
        reply_id = resp_reply.data.get("id")
        print(f"   ✅ Auto-Reply publicado com sucesso: https://x.com/i/web/status/{reply_id}")

        # Salva histórico
        registrar_sucesso({
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "reply_id": reply_id,
            "texto": texto_tweet,
            "imagem": str(caminho_imagem)
        })

        return True

    except tweepy.errors.TweepyException as e_tw:
        registrar_erro(f"Erro da API Tweepy no X: {e_tw}", e_tw)
        return False
    except Exception as e_geral:
        registrar_erro(f"Falha inesperada no pipeline de publicação no X: {e_geral}", e_geral)
        return False

# =============================================================================
# --- 6. EXECUÇÃO PRINCIPAL (CLI) ---
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Publicador Automatizado do All News Journal no X (Twitter)")
    parser.add_argument("--dry-run", action="store_true", help="Simula execução sem disparar tweets reais na API.")
    parser.add_argument("--data", type=str, default=None, help="Data da edição no formato YYYY-MM-DD.")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("🐦 All News Journal — Esteira de Publicação no X (Twitter)")
    print("=" * 65)

    try:
        # 1. Carrega snapshot da edição
        edicao_dados, data_str = carregar_edicao_alvo(args.data)
        print(f"📂 Edição carregada: {data_str} ({len(edicao_dados.get('cadernos', {}))} cadernos)")

        # 2. Curadoria estrita dos cadernos nobres (IA e Economia)
        tema, materia = selecionar_materia_nobre(edicao_dados)
        titulo = materia.get("titulo", "")
        resumo = materia.get("resumo", "")
        foto_url = materia.get("imagem", "")

        print(f"📌 Pauta: [{tema}] {titulo}")

        # 3. Engenharia de prompt Gemini Flash
        print("🤖 Gerando copy analítico no Google Gemini Flash...")
        copy_x = gerar_copy_x(tema, titulo, resumo)
        print(f"   ✅ Copy gerado ({len(copy_x)}/240 caracteres).")

        # 4. Obtenção ou geração da Capa Editorial Clássica (Slide 1)
        caminho_capa = obter_ou_gerar_capa(data_str, tema, titulo, foto_url)

        # 5. Publicação no X (Principal + Auto-Reply)
        sucesso = publicar_no_x(copy_x, caminho_capa, dry_run=args.dry_run)

        if sucesso:
            print("\n🎉 Esteira do X concluída com sucesso!")
            sys.exit(0)
        else:
            print("\n⚠️ A esteira do X encontrou problemas reportados nos logs.")
            sys.exit(0)  # Não quebra workflow geral

    except Exception as e:
        registrar_erro(f"Erro fatal na esteira do X: {e}", e)
        sys.exit(0)  # Tolerante a falhas no CI

if __name__ == "__main__":
    main()
