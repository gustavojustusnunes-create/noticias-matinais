"""
finance_main.py — Orquestrador diário do All News Finance (Segunda a Sexta-feira)
Executado pelo GitHub Actions ou manualmente via CLI.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

from finance_feeds import coletar_noticias_finance, ORDEM_CADERNOS_FINANCE
from finance_email_builder import construir_html_finance, enviar_email_finance
from sheets_db import listar_assinantes_finance


def salvar_edicao_finance_web(edicao):
    """Salva a edição gerada na pasta edicoes_finance/ para o portal web (app.py)."""
    pasta = Path("edicoes_finance")
    pasta.mkdir(parents=True, exist_ok=True)

    hoje = edicao.get("data", datetime.now().strftime("%Y-%m-%d"))
    arquivo_html = pasta / f"{hoje}.html"
    arquivo_json = pasta / f"{hoje}.json"

    # Salva HTML publico (sem saudações customizadas)
    html_publico = construir_html_finance(edicao, nome_destinatario="Leitor(a)")
    with open(arquivo_html, "w", encoding="utf-8") as f:
        f.write(html_publico)

    # Salva JSON puro
    with open(arquivo_json, "w", encoding="utf-8") as f:
        json.dump(edicao, f, ensure_ascii=False, indent=2)

    # Atualiza index.json para o menu do Streamlit
    index_path = pasta / "index.json"
    indice = []
    if index_path.exists():
        try:
            with open(index_path, encoding="utf-8") as f:
                indice = json.load(f)
        except Exception:
            indice = []

    # Conta total de notícias na edição
    total_noticias = sum(len(noticias) for k, noticias in edicao.items() if isinstance(noticias, list))
    
    # Atualiza ou insere o dia atual no topo do index
    indice = [item for item in indice if item.get("data") != hoje]
    indice.insert(0, {
        "data": hoje,
        "titulo": f"All News Finance — Edição {hoje}",
        "noticias_count": total_noticias,
    })

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    print(f"   📂 Edição de finanças arquivada para web: {hoje} ({total_noticias} notícias).")


def main():
    print(f"{'═'*65}")
    print("📈 ALL NEWS FINANCE — Orquestrador Diário")
    print(f"{'═'*65}")

    # Verifica se é dia útil (Segunda=0 a Sexta=4) salvo se passar --force
    dia_semana = datetime.now().weekday()
    if dia_semana >= 5 and "--force" not in sys.argv:
        print("ℹ️ Hoje é fim de semana (Sábado/Domingo).")
        print("   O All News Finance circula de Segunda a Sexta-feira.")
        print("   Encerrando execução normalmente (use --force para testar no fim de semana).")
        return

    # 1. Coleta e resumo por IA
    edicao = coletar_noticias_finance()

    # 1.5. Agente Supervisor de Qualidade da IA
    try:
        from ai_supervisor import revisar_edicao_diaria
        edicao = revisar_edicao_diaria(edicao)
    except Exception as e:
        print(f"   ⚠️ Falha ao rodar o Supervisor de IA (ignorando e seguindo): {e}")

    total = sum(len(n) for n in edicao.values() if isinstance(n, list))
    if total == 0:
        print("❌ Nenhuma notícia financeira foi coletada ou resumida. Abortando envio.")
        return

    edicao["data"] = datetime.now().strftime("%Y-%m-%d")

    # 2. Salva para o portal web (edicoes_finance/)
    salvar_edicao_finance_web(edicao)

    # 3. Leitura do banco de assinantes da aba "all news finance"
    print("\n👥 Carregando assinantes do All News Finance...")
    assinantes = listar_assinantes_finance()
    if not assinantes:
        print("   ℹ️ Nenhum assinante ativo cadastrado no All News Finance ainda.")
        return

    print(f"   🚀 Enviando edição para {len(assinantes)} leitores de finanças...")
    hoje_str = datetime.now().strftime("%d/%m")
    assunto = f"📈 All News Finance: O mercado nesta manhã ({hoje_str})"

    enviados = 0
    falhas = 0

    for idx, ass in enumerate(assinantes, start=1):
        nome = ass.get("nome", "Leitor(a)")
        email = ass.get("email", "").strip()
        if not email:
            continue

        html = construir_html_finance(edicao, nome_destinatario=nome)
        print(f"      ✉️ [{idx}/{len(assinantes)}] Enviando para {nome} ({email})...", end=" ")
        sucesso = enviar_email_finance(email, assunto, html)
        if sucesso:
            print("✅ OK")
            enviados += 1
        else:
            print("❌ Falha")
            falhas += 1

    print(f"\n{'─'*65}")
    print(f"✅ All News Finance Concluído — Enviados: {enviados} | Falhas: {falhas}")
    print(f"{'═'*65}")


if __name__ == "__main__":
    main()
