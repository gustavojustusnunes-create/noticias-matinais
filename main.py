"""
All News Journal - Pipeline principal
Coleta RSS → Filtra → Reescreve com IA → Monta e-mail → Envia
"""

import argparse
import json
import logging
import os
import re
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import anthropic
import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from config import (
    ORDEM_CADERNOS,
    RSS_FEEDS,
    ICONES_TEMA,
    CORES_TEMA,
    FILTROS_TEMA,
    INSTRUCAO_TEMA,
)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BRT = timezone(timedelta(hours=-3))

MAX_ARTICLES_PER_CATEGORY = 5
MAX_FEED_AGE_HOURS = 48

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"journal_{datetime.now(BRT).strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("allnews")

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def load_global_filters() -> list[str]:
    """Carrega palavras-chave globais de filtro de filters/global.txt."""
    words: list[str] = []
    filters_dir = BASE_DIR / "filters"
    if not filters_dir.exists():
        return words
    for f in filters_dir.glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line.lower())
    log.info("Filtros globais carregados: %d palavras-chave", len(words))
    return words


def should_filter(title: str, summary: str, global_filters: list[str], tema: str) -> bool:
    """Retorna True se a notícia deve ser removida (filtro global + por tema)."""
    text = f"{title} {summary}".lower()
    if any(word in text for word in global_filters):
        return True
    tema_filters = FILTROS_TEMA.get(tema, [])
    return any(word in text for word in tema_filters)

# ---------------------------------------------------------------------------
# Coleta RSS
# ---------------------------------------------------------------------------

def clean_html(raw: str) -> str:
    """Remove tags HTML e limpa espaços."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_entry_date(entry) -> datetime | None:
    """Extrai a data de um entry do feedparser."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            from time import mktime
            return datetime.fromtimestamp(mktime(parsed), tz=BRT)
    return None


def fetch_tema_articles(tema: str, global_filters: list[str]) -> list[dict]:
    """Coleta artigos de todos os feeds de um tema."""
    urls = RSS_FEEDS.get(tema, [])
    articles: list[dict] = []
    cutoff = datetime.now(BRT) - timedelta(hours=MAX_FEED_AGE_HOURS)

    for url in urls:
        log.info("  Buscando feed: %s", url)
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                log.warning("  Feed com erro e sem entries: %s", url)
                continue
        except Exception as e:
            log.error("  Erro ao buscar feed %s: %s", url, e)
            continue

        source = feed.feed.get("title", url)

        for entry in feed.entries:
            title = clean_html(entry.get("title", ""))
            if not title:
                continue

            summary_raw = entry.get("summary", "") or entry.get("description", "")
            summary = clean_html(summary_raw)
            link = entry.get("link", "")
            pub_date = parse_entry_date(entry)

            if pub_date and pub_date < cutoff:
                continue

            if should_filter(title, summary, global_filters, tema):
                log.info("  [FILTRADO] %s", title[:60])
                continue

            articles.append({
                "title": title,
                "summary": summary,
                "link": link,
                "source": source,
                "date": pub_date.strftime("%d/%m/%Y %H:%M") if pub_date else "Hoje",
            })

    # Remove duplicatas por título similar
    seen_titles: set[str] = set()
    unique: list[dict] = []
    for art in articles:
        key = re.sub(r"[^a-z0-9]", "", art["title"].lower())[:50]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(art)

    unique = unique[:MAX_ARTICLES_PER_CATEGORY]
    log.info("  Tema '%s': %d artigos coletados", tema, len(unique))
    return unique

# ---------------------------------------------------------------------------
# Reescrita com IA (fallback de 3 camadas)
# ---------------------------------------------------------------------------

def rewrite_with_ai(article: dict, tema: str, client: anthropic.Anthropic | None) -> str:
    """
    Fallback de 3 camadas:
    1. Reescreve o resumo do RSS com IA (instrução editorial por tema)
    2. Se não tem resumo, gera a partir do título
    3. Se a API falhar, usa o texto original do RSS
    """
    if client is None:
        return article.get("summary", "") or article["title"]

    instrucao = INSTRUCAO_TEMA.get(tema, "")
    has_summary = bool(article.get("summary", "").strip())

    if has_summary:
        prompt = (
            f"Reescreva este resumo de noticia em portugues brasileiro, em 2-3 paragrafos "
            f"claros e objetivos. Mantenha apenas os fatos, sem opiniao.\n\n"
            f"INSTRUCOES EDITORIAIS PARA ESTE CADERNO:\n{instrucao}\n\n"
            f"Titulo: {article['title']}\n"
            f"Resumo original: {article['summary'][:800]}"
        )
    else:
        prompt = (
            f"Com base apenas neste titulo de noticia, escreva um resumo de 2 paragrafos "
            f"em portugues brasileiro. Seja factual e objetivo.\n\n"
            f"INSTRUCOES EDITORIAIS PARA ESTE CADERNO:\n{instrucao}\n\n"
            f"Titulo: {article['title']}"
        )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text:
            return text
    except Exception as e:
        log.error("  Erro na API Anthropic: %s", e)

    return article.get("summary", "") or article["title"]

# ---------------------------------------------------------------------------
# Montagem do e-mail HTML
# ---------------------------------------------------------------------------

def load_template(name: str) -> str:
    """Carrega um template HTML."""
    path = BASE_DIR / "templates" / name
    return path.read_text(encoding="utf-8")


def build_email_html(all_news: dict[str, list[dict]]) -> str:
    """Monta o HTML completo do e-mail."""
    email_tpl = load_template("email.html")
    section_tpl = load_template("section.html")
    article_tpl = load_template("article.html")

    today = datetime.now(BRT).strftime("%d de %B de %Y")
    months_pt = {
        "January": "Janeiro", "February": "Fevereiro", "March": "Marco",
        "April": "Abril", "May": "Maio", "June": "Junho",
        "July": "Julho", "August": "Agosto", "September": "Setembro",
        "October": "Outubro", "November": "Novembro", "December": "Dezembro",
    }
    for en, pt in months_pt.items():
        today = today.replace(en, pt)

    sections_html = ""

    for tema in ORDEM_CADERNOS:
        articles = all_news.get(tema, [])
        if not articles:
            continue

        articles_html = ""
        for art in articles:
            art_html = article_tpl
            art_html = art_html.replace("{{ARTICLE_TITLE}}", art["title"])
            art_html = art_html.replace("{{ARTICLE_SUMMARY}}", art["ai_summary"])
            art_html = art_html.replace("{{ARTICLE_URL}}", art["link"])
            art_html = art_html.replace("{{ARTICLE_SOURCE}}", art["source"])
            art_html = art_html.replace("{{ARTICLE_DATE}}", art["date"])
            articles_html += art_html

        sec_html = section_tpl
        sec_html = sec_html.replace("{{CATEGORY_NAME}}", f"{ICONES_TEMA[tema]} {tema}")
        sec_html = sec_html.replace("{{CATEGORY_ICON}}", ICONES_TEMA[tema])
        sec_html = sec_html.replace("{{CATEGORY_COLOR}}", f"#{CORES_TEMA[tema]}")
        sec_html = sec_html.replace("{{ARTICLES}}", articles_html)
        sections_html += sec_html

    html = email_tpl.replace("{{SECTIONS}}", sections_html)
    html = html.replace("{{DATA_HOJE}}", today)
    return html

# ---------------------------------------------------------------------------
# Assinantes (simples JSON)
# ---------------------------------------------------------------------------

def load_subscribers() -> list[str]:
    """Carrega lista de e-mails de assinantes."""
    path = BASE_DIR / "subscribers.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [e for e in data if isinstance(e, str) and "@" in e]
    return []

# ---------------------------------------------------------------------------
# Envio de e-mail
# ---------------------------------------------------------------------------

def send_email(html: str, subscribers: list[str]) -> None:
    """Envia o e-mail para todos os assinantes via SMTP."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("FROM_EMAIL", user)
    from_name = os.getenv("FROM_NAME", "All News Journal")

    if not user or not password:
        log.error("SMTP_USER e SMTP_PASS nao configurados. E-mail nao enviado.")
        return

    today = datetime.now(BRT).strftime("%d/%m/%Y")
    subject = f"All News Journal - {today}"

    log.info("Conectando ao SMTP %s:%d...", host, port)
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)

        for recipient in subscribers:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(from_email, recipient, msg.as_string())
            log.info("  E-mail enviado para: %s", recipient)

    log.info("Todos os e-mails enviados com sucesso!")

# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> str:
    """Executa o pipeline completo. Retorna o HTML gerado."""
    log.info("=" * 60)
    log.info("ALL NEWS JOURNAL - Iniciando pipeline")
    log.info("Modo: %s", "DRY-RUN (teste)" if dry_run else "PRODUCAO")
    log.info("Cadernos: %s", ", ".join(ORDEM_CADERNOS))
    log.info("=" * 60)

    # 1. Carregar filtros globais
    global_filters = load_global_filters()

    # 2. Inicializar cliente Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    client = None
    if api_key and not api_key.startswith("sk-ant-xxx"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            log.info("API Anthropic configurada com sucesso")
        except Exception as e:
            log.warning("Erro ao inicializar Anthropic: %s", e)
    else:
        log.warning("ANTHROPIC_API_KEY nao configurada - usando textos originais do RSS")

    # 3. Coletar notícias por tema
    all_news: dict[str, list[dict]] = {}
    total_articles = 0

    for tema in ORDEM_CADERNOS:
        log.info("Coletando caderno: %s %s", ICONES_TEMA[tema], tema)
        articles = fetch_tema_articles(tema, global_filters)

        # 4. Reescrever com IA usando instrução editorial do tema
        for art in articles:
            log.info("  Reescrevendo: %s", art["title"][:50])
            art["ai_summary"] = rewrite_with_ai(art, tema, client)

        all_news[tema] = articles
        total_articles += len(articles)

    log.info("Total de artigos processados: %d", total_articles)

    if total_articles == 0:
        log.warning("Nenhum artigo encontrado! Verifique os feeds.")
        return ""

    # 5. Montar HTML
    log.info("Montando e-mail HTML...")
    html = build_email_html(all_news)

    # 6. Salvar preview
    preview_path = BASE_DIR / "preview.html"
    preview_path.write_text(html, encoding="utf-8")
    log.info("Preview salvo em: %s", preview_path)

    # 7. Enviar ou simular
    if dry_run:
        log.info("=" * 60)
        log.info("DRY-RUN: E-mail NAO enviado")
        log.info("Abra 'preview.html' no navegador para ver o resultado")
        log.info("=" * 60)

        def safe_print(text: str):
            try:
                print(text)
            except UnicodeEncodeError:
                print(text.encode("ascii", errors="replace").decode("ascii"))

        safe_print("\n" + "=" * 60)
        safe_print("  ALL NEWS JOURNAL - PREVIEW")
        safe_print("=" * 60)
        for tema in ORDEM_CADERNOS:
            articles = all_news.get(tema, [])
            if not articles:
                continue
            safe_print(f"\n[{tema}] ({len(articles)} noticias)")
            safe_print("-" * 40)
            for i, art in enumerate(articles, 1):
                safe_print(f"  {i}. {art['title'][:70]}")
                safe_print(f"     {art['ai_summary'][:100]}...")
                safe_print(f"     Fonte: {art['source']}")
                safe_print("")
        safe_print("=" * 60)
        safe_print(f"Total: {total_articles} noticias")
        safe_print(f"Preview HTML salvo em: {preview_path}")
        safe_print("=" * 60)
    else:
        subscribers = load_subscribers()
        if subscribers:
            log.info("Enviando para %d assinantes...", len(subscribers))
            send_email(html, subscribers)
        else:
            log.warning("Nenhum assinante cadastrado! Adicione e-mails em subscribers.json")

    return html

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="All News Journal - Jornal digital automatizado"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo teste: coleta e monta o jornal sem enviar e-mail",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
