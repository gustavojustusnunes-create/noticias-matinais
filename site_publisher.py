"""
site_publisher.py — Publica a edição diária no site (v17.0)

Chamado pelo main.py ao final do envio de e-mails. Salva em edicoes/:
  • AAAA-MM-DD.json  → snapshot das notícias (fonte da verdade p/ Instagram)
  • AAAA-MM-DD.html  → edição pública (reusa o template do e-mail)
  • index.json       → índice das edições (lido pelo portal)

Tudo em try/except: uma falha aqui NUNCA afeta o envio do e-mail.
"""
import json
from datetime import datetime
from pathlib import Path

from config import ORDEM_CADERNOS, EDICOES_DIR

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]


def _data_extenso(dt):
    """Ex.: 'Quarta-feira, 10 de Junho de 2026' (mesmo formato do e-mail)."""
    return f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def _html_publico(dados, painel, editorial):
    """Gera o HTML da edição reusando gerar_html_final e neutraliza o rodapé
    de assinatura (a edição pública não é personalizada). Import tardio para
    que `import site_publisher` funcione sem as dependências do e-mail."""
    from email_builder import gerar_html_final

    html = gerar_html_final("Leitor", dados, painel, editorial=editorial)

    # Neutraliza o bloco de cancelamento (substituições simples de string;
    # se o template mudar, a edição sai com o rodapé original — sem quebrar)
    try:
        html = html.replace(
            "Você recebe este email porque é assinante do All News Journal.<br/>",
            "Edição pública do All News Journal.<br/>",
        )
        ini = html.find("Para cancelar sua assinatura,")
        if ini != -1:
            fim = html.find("clique aqui</a>.", ini)
            if fim != -1:
                html = html[:ini] + "Assine para receber no seu e-mail." + html[fim + len("clique aqui</a>."):]
        html = html.replace(
            "Recebeu esta edição porque é assinante do nosso serviço.",
            "Edição pública — assine para receber todas as manhãs no seu e-mail.",
        )
    except Exception as e:
        print(f"   ⚠️ Não foi possível neutralizar o rodapé ({e}) — seguindo com o HTML original.")
    return html


def publicar_edicao(cache_global, painel, editorial):
    """Salva snapshot JSON + HTML público + índice. Retorna dict de status."""
    status = {"ok": False, "json": None, "html": None, "index": None}
    try:
        ed_dir = Path(EDICOES_DIR)
        ed_dir.mkdir(exist_ok=True)

        hoje        = datetime.now()
        data_iso    = hoje.strftime("%Y-%m-%d")
        data_ext    = _data_extenso(hoje)

        # Cadernos na ordem editorial (só os presentes no cache do dia)
        dados = {t: cache_global[t] for t in ORDEM_CADERNOS if cache_global.get(t)}
        if not dados:
            print("   ⚠️ Nenhuma notícia no cache — nada a publicar no site.")
            return status

        manchete = dados[next(iter(dados))][0].get("titulo", "")

        # 1) Snapshot JSON (fonte da verdade para carrossel/reel)
        snapshot = {
            "data":         data_iso,
            "data_extenso": data_ext,
            "editorial":    editorial or "",
            "manchete":     manchete,
            "cadernos": {
                tema: [
                    {
                        "titulo": n.get("titulo", ""),
                        "link":   n.get("link", ""),
                        "imagem": n.get("imagem", ""),
                        "resumo": n.get("resumo", ""),
                    }
                    for n in noticias
                ]
                for tema, noticias in dados.items()
            },
        }
        caminho_json = ed_dir / f"{data_iso}.json"
        caminho_json.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        status["json"] = str(caminho_json)
        print(f"   💾 Snapshot salvo: {caminho_json}")

        # 2) HTML público da edição
        try:
            html = _html_publico(dados, painel, editorial)
            caminho_html = ed_dir / f"{data_iso}.html"
            caminho_html.write_text(html, encoding="utf-8")
            status["html"] = str(caminho_html)
            print(f"   📰 Edição HTML salva: {caminho_html}")
        except Exception as e:
            print(f"   ⚠️ HTML da edição não gerado ({e}) — snapshot JSON preservado.")

        # 3) Índice (mais novo primeiro, sem duplicar a data, máx. 60 itens)
        caminho_idx = ed_dir / "index.json"
        indice = []
        if caminho_idx.exists():
            try:
                indice = json.loads(caminho_idx.read_text(encoding="utf-8"))
            except Exception:
                indice = []
        indice = [e for e in indice if e.get("data") != data_iso]
        indice.insert(0, {
            "data":         data_iso,
            "data_extenso": data_ext,
            "manchete":     manchete[:120],
            "arquivo_html": f"{data_iso}.html",
        })
        indice = indice[:60]
        caminho_idx.write_text(
            json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        status["index"] = str(caminho_idx)
        print(f"   🗂️  Índice atualizado: {len(indice)} edição(ões).")

        status["ok"] = True
    except Exception as e:
        print(f"   ⚠️ Erro ao publicar edição no site: {e}")
    return status
