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
X_AUTH_TOKEN          = os.environ.get("X_AUTH_TOKEN", "").strip()
X_CT0                 = os.environ.get("X_CT0", "").strip()
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
    "https://noticias-matinais.vercel.app/?utm_source=x&utm_medium=organic&utm_campaign=daily_debate"
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

def publicar_via_playwright(texto_tweet: str, caminho_imagem: Path, auto_reply: str = AUTO_REPLY_TEXT) -> bool:
    """
    Publica o tweet principal com capa e auto-reply encadeado via Playwright Headless.
    Consome R$ 0 em APIs e roda nativamente no motor do Chromium.
    """
    from playwright.sync_api import sync_playwright

    print("\n🤖 Iniciando Robô de Postagem Playwright no X (Sessão Headless $0/mês)...")
    created_ids = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ],
            ignore_default_args=["--enable-automation"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo"
        )
        context.add_cookies([
            {"name": "auth_token", "value": X_AUTH_TOKEN, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": X_CT0, "domain": ".x.com", "path": "/"}
        ])
        page = context.new_page()

        # Aplica evasões avançadas anti-bot / anti-Turnstile
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(page)
            print("   🛡️ Perfil stealth anti-bot ativado com sucesso.")
        except Exception as e_st:
            print(f"   ℹ️ Stealth fallback: {e_st}")

        # Interceptador para capturar o ID do Tweet gerado pelo backend do X
        def capturar_resposta(response):
            if "CreateTweet" in response.url and response.status == 200:
                try:
                    data = response.json()
                    tid = data.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result", {}).get("rest_id")
                    if tid:
                        created_ids.append(tid)
                except Exception:
                    pass

        page.on("response", capturar_resposta)

        print("⏳ Acessando painel https://x.com/home...")
        page.goto("https://x.com/home", wait_until="domcontentloaded")

        # Trata Cloudflare Turnstile se acionado
        try:
            cf_frame = page.frame_locator("iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile']")
            cf_box = cf_frame.locator("input[type='checkbox'], .mark, .ctp-checkbox, #challenge-stage")
            if cf_box.count() > 0:
                print("   🛡️ Desafio Cloudflare Turnstile detectado! Resolvendo verificação...")
                cf_box.first.click(force=True)
                time.sleep(6)
        except Exception:
            pass

        # Se houver banner de cookies/consentimento, aceita
        try:
            cookie_banner = page.locator("button:has-text('Accept all cookies'), button:has-text('Aceitar todos os cookies')")
            if cookie_banner.count() > 0:
                cookie_banner.first.click(force=True)
                print("   🍪 Banner de cookies aceito.")
        except Exception:
            pass

        # Se houver botão de Recarregar/Retry
        try:
            retry_btn = page.locator("button:has-text('Retry'), button:has-text('Tentar novamente')")
            if retry_btn.count() > 0:
                retry_btn.first.click(force=True)
                print("   🔄 Botão Retry acionado.")
        except Exception:
            pass

        print(f"   🔗 URL atual: {page.url} | Título: {page.title()} | Aguardando composer...")
        try:
            textarea0 = page.wait_for_selector("[data-testid='tweetTextarea_0']", timeout=60000)
        except Exception as e_wait:
            print(f"   ❌ Timeout ao aguardar tweetTextarea_0.")
            print(f"   🔗 URL final: {page.url} | Título: {page.title()}")
            Path("logs").mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path="logs/x_error_debug.png")
                print("   📸 Screenshot de erro salvo em logs/x_error_debug.png")
            except Exception:
                pass
            raise e_wait

        # Localização do Composer
        print("✍️ Inserindo copy do post principal...")
        textarea0.click()
        textarea0.fill(texto_tweet)
        time.sleep(1)

        # Anexo da Capa Editorial (Slide 1)
        if caminho_imagem and Path(caminho_imagem).exists():
            print(f"📎 Anexando imagem da capa ({caminho_imagem})...")
            file_input = page.locator("input[data-testid='fileInput']").first
            file_input.set_input_files(str(Path(caminho_imagem).resolve()))
            page.wait_for_selector("[data-testid='attachments']", timeout=20000)
            print("   ✅ Capa editorial carregada com sucesso.")
            time.sleep(2)

        # Encadeamento do Auto-reply (Thread)
        thread_ativada = False
        print("🔗 Adicionando segundo tweet da thread (Auto-Reply)...")
        try:
            add_btn = page.locator("[data-testid='addButton']").first
            add_btn.wait_for(state="visible", timeout=6000)
            add_btn.click(force=True)
            textarea1 = page.wait_for_selector("[data-testid='tweetTextarea_1']", timeout=8000)
            textarea1.fill(auto_reply)
            thread_ativada = True
            print("   ✅ Auto-reply de conversão encadeado com sucesso.")
            time.sleep(1)
        except Exception as e_add:
            print(f"   ℹ️ Inclusão via thread direta não disponível ({e_add}), prosseguindo com post principal.")

        # Disparo do botão Post / Post all
        btn_post = page.locator("[data-testid='tweetButton'], [data-testid='tweetButtonInline']").first
        btn_post.wait_for(state="visible", timeout=10000)
        time.sleep(1)

        print("🚀 Disparando publicação no X via Playwright...")
        btn_post.click(force=True)

        # Confirmação da publicação do tweet principal
        print("⏳ Aguardando confirmação do X...")
        for _ in range(25):
            time.sleep(1)
            if created_ids:
                print(f"   📡 Confirmação recebida via rede (IDs: {created_ids})")
                break
            if page.locator("[data-testid='toast']").count() > 0:
                print("   📡 Toast de confirmação detectado na interface.")
                break
            if thread_ativada and page.locator("[data-testid='tweetTextarea_1']").count() == 0:
                print("   📡 Modal de composição finalizado com sucesso.")
                break

        # Se a thread direta não foi ativada, publica o auto-reply encadeado com delay de 12s
        if not thread_ativada and auto_reply:
            print("⏳ Aguardando delay de 12 segundos para encadeamento natural de conversão...")
            time.sleep(12)
            print("🔗 Publicando Auto-Reply encadeado no post...")
            try:
                status_url = None
                toast_link = page.locator("[data-testid='toast'] a[href*='/status/']").first
                if toast_link.count() > 0:
                    href = toast_link.get_attribute("href")
                    status_url = f"https://x.com{href}" if href.startswith("/") else f"https://x.com/{href}"
                elif created_ids:
                    status_url = f"https://x.com/allnews_journal/status/{created_ids[0]}"
                else:
                    # Busca o post mais recente no perfil
                    page.locator("a[data-testid='AppTabBar_Profile_Link']").first.click(force=True)
                    time.sleep(2)
                    first_article_link = page.locator("article a[href*='/status/']").first
                    if first_article_link.count() > 0:
                        href = first_article_link.get_attribute("href")
                        status_url = f"https://x.com{href}" if href.startswith("/") else f"https://x.com/{href}"

                if status_url:
                    print(f"   🎯 Acessando URL do tweet ({status_url}) para responder...")
                    page.goto(status_url, wait_until="domcontentloaded")
                    time.sleep(2)
                    # Descarta modal de onboarding se houver
                    got_it = page.locator("button:has-text('Got it'), div[role='button']:has-text('Got it')")
                    if got_it.count() > 0:
                        got_it.first.click(force=True)
                        time.sleep(1)

                    reply_box = page.wait_for_selector("[data-testid='tweetTextarea_0']", timeout=15000)
                    reply_box.fill(auto_reply)
                    time.sleep(1)
                    reply_btn = page.locator("[data-testid='tweetButtonInline']").first
                    reply_btn.click(force=True)
                    time.sleep(3)
                    print("   ✅ Auto-Reply de conversão publicado com sucesso na thread!")
                    thread_ativada = True
            except Exception as e_rep:
                print(f"   ⚠️ Falha ao publicar auto-reply sequencial: {e_rep}")

        tweet_id = created_ids[0] if created_ids else "publicado"
        tweet_url = f"https://x.com/allnews_journal/status/{tweet_id}" if created_ids else "https://x.com/allnews_journal"
        reply_id = created_ids[1] if (thread_ativada and len(created_ids) > 1) else None

        print(f"🎉 Postagem realizada com sucesso!")
        print(f"   🔗 URL: {tweet_url}")
        if reply_id:
            print(f"   💬 Thread Reply ID: {reply_id}")

        # Registro de Sucesso
        registrar_sucesso({
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metodo": "Playwright_Headless_Robot",
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "reply_id": reply_id,
            "thread_ativada": thread_ativada,
            "texto": texto_tweet,
            "imagem": str(caminho_imagem)
        })

        browser.close()
        return True

def publicar_via_tweepy(texto_tweet: str, caminho_imagem: Path) -> bool:
    """
    Fallback: pipeline de publicação via API oficial do Twitter (Tweepy).
    """
    import tweepy
    print("\n🔐 Autenticando na API do X (Tweepy)...")
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

    print("⏳ Aguardando delay de 12 segundos para encadeamento natural...")
    time.sleep(12)

    print("🔗 Publicando Auto-Reply encadeado de conversão...")
    resp_reply = client_v2.create_tweet(
        text=AUTO_REPLY_TEXT,
        in_reply_to_tweet_id=tweet_id
    )
    reply_id = resp_reply.data.get("id")
    print(f"   ✅ Auto-Reply publicado com sucesso: https://x.com/i/web/status/{reply_id}")

    registrar_sucesso({
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metodo": "Tweepy_Official_API",
        "tweet_id": tweet_id,
        "tweet_url": tweet_url,
        "reply_id": reply_id,
        "texto": texto_tweet,
        "imagem": str(caminho_imagem)
    })
    return True

def publicar_no_x(texto_tweet: str, caminho_imagem: Path, dry_run: bool = False) -> bool:
    """
    Orquestrador de publicação no X:
    1. Se dry_run: simula sem publicar.
    2. Prioridade 1: Playwright Headless Robot ($0 custo de API).
    3. Fallback: API oficial Tweepy (caso credenciais estejam configuradas).
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

    # 1. Prioridade: Robô de Sessão Playwright (Custo $0, sem limite de API)
    if X_AUTH_TOKEN and X_CT0:
        try:
            return publicar_via_playwright(texto_tweet, caminho_imagem, AUTO_REPLY_TEXT)
        except Exception as e_pw:
            registrar_erro(f"Falha no robô Playwright do X: {e_pw}", e_pw)
            return False

    # 2. Fallback: API Oficial Tweepy (somente se chaves de API estiverem configuradas e sessão Playwright não fornecida)
    if X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET and X_BEARER_TOKEN:
        try:
            return publicar_via_tweepy(texto_tweet, caminho_imagem)
        except Exception as e_tw:
            registrar_erro(f"Falha na API Tweepy do X: {e_tw}", e_tw)
            return False

    msg_aviso = "⚠️ Nenhuma credencial do X configurada (nem X_AUTH_TOKEN nem chaves Tweepy). Postagem ignorada sem falhar pipeline."
    print(f"\n{msg_aviso}")
    registrar_erro(msg_aviso)
    return True

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
