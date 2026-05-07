"""
main.py — Motor principal do All News Journal v15.0
Orquestra: coleta RSS → IA → email.
Para detalhes de cada etapa, veja os módulos especializados.
"""
import re

from config import RSS_FEEDS, CLAUDE_KEY, EMAIL_SENDER, EMAIL_PASSWORD, GCP_JSON, MAPEAMENTO_LEGADO
from sheets_db import conectar_banco, carregar_historico, salvar_no_historico, registrar_log
from feeds import processar_tema, FEEDS_STATUS
from email_builder import obter_indicadores, gerar_html_final, enviar_email, montar_subject
from claude_api import chamar_claude_api


def validar_ambiente():
    variaveis = {
        "ANTHROPIC_API_KEY / CLAUDE_KEY": CLAUDE_KEY,
        "GCP_JSON":                       GCP_JSON,
        "EMAIL_USER":                     EMAIL_SENDER,
        "EMAIL_PASS / EMAIL_PASSWORD":    EMAIL_PASSWORD,
    }
    erros = [nome for nome, val in variaveis.items() if not val]
    if erros:
        print(f"❌ ERRO CRÍTICO: Variáveis faltando: {', '.join(erros)}")
        return False
    print("✅ Ambiente validado.")
    return True


def gerar_editorial(cache_global):
    """
    Gera a frase de abertura editorial do dia conectando os destaques.
    Usa Claude Haiku para ser rápido e barato.
    """
    titulos = []
    for tema, items in cache_global.items():
        if items:
            titulos.append(items[0].get("titulo", ""))
        if len(titulos) >= 6:
            break

    if not titulos:
        return ""

    manchetes_str = "\n".join(f"- {t}" for t in titulos)
    prompt = (
        f"Dadas as manchetes do dia:\n{manchetes_str}\n\n"
        f"Escreva uma FRASE DE ABERTURA de 20 a 30 palavras que conecte os destaques "
        f"do dia num tom elegante de editor-chefe. "
        f"Português brasileiro. Retorne APENAS a frase, sem aspas."
    )
    resultado = chamar_claude_api(prompt, max_tokens=100)
    if resultado:
        return resultado.strip().strip('"\'')
    return ""


def main():
    print("🚀 All News Journal — Motor v15.0")
    print("   Módulos: config | feeds | claude_api | email_builder | sheets_db")
    print("─" * 65)

    if not validar_ambiente():
        return

    sheet_usuarios, sheet_historico, sheet_logs = conectar_banco()
    if not sheet_usuarios:
        return

    historico_hashes = carregar_historico(sheet_historico)
    usuarios_raw     = sheet_usuarios.get_all_records()
    # Compatibilidade com colunas legadas da planilha (Mercado→Economia, Fitness→Wellness)
    usuarios = []
    for usr in usuarios_raw:
        for legado, novo in MAPEAMENTO_LEGADO.items():
            if legado in usr and novo not in usr:
                usr[novo] = usr.pop(legado)
        usuarios.append(usr)
    if any(MAPEAMENTO_LEGADO.keys() & set(usuarios_raw[0].keys() if usuarios_raw else [])):
        print("⚠️  AVISO: A planilha ainda tem colunas com nomes antigos.")
        print("   Por favor, renomeie no Google Sheets:")
        for legado, novo in MAPEAMENTO_LEGADO.items():
            print(f"   '{legado}' → '{novo}'")
        print("   Adicione também a coluna 'IA' e remova 'Tech', 'Esportes', 'Motos'.")
    print(f"   👥 {len(usuarios)} assinantes encontrados.")

    # Descobre temas necessários
    temas_demandados = {
        tema
        for usr in usuarios
        for tema in RSS_FEEDS
        if str(usr.get(tema, "")).strip().lower() in {"sim"}
        or str(usr.get(tema, "")).strip().isdigit()
    }
    print(f"   📰 Temas a processar: {', '.join(sorted(temas_demandados))}")

    # Processa cada tema uma vez (cache global)
    painel       = obter_indicadores()
    CACHE_GLOBAL = {}
    novas        = []

    for tema in temas_demandados:
        resultado = processar_tema(tema, historico_hashes)
        if resultado:
            CACHE_GLOBAL[tema] = resultado
            novas.extend(resultado)
            print(f"      ✅ {tema}: {len(resultado)} notícias prontas.")
        else:
            print(f"      ⚠️ {tema}: nenhuma notícia disponível hoje.")

    if novas:
        salvar_no_historico(sheet_historico, novas)
        print(f"   💾 {len(novas)} notícias salvas no histórico.")

    # Gera editorial do dia (frase de abertura compartilhada por todos)
    print("   ✍️  Gerando editorial do dia…")
    editorial = gerar_editorial(CACHE_GLOBAL)
    if editorial:
        print(f"   📝 Editorial: {editorial[:80]}…")

    # Resumo de status dos feeds
    feeds_ok     = sum(1 for s in FEEDS_STATUS.values() if s.startswith("ok"))
    feeds_falhas = [(url, s) for url, s in FEEDS_STATUS.items() if not s.startswith("ok")]
    print(f"   📡 Status dos feeds: {feeds_ok} OK | {len(feeds_falhas)} falha(s)")
    if feeds_falhas:
        for url, status in feeds_falhas[:5]:  # mostra só as 5 primeiras
            print(f"      ⚠️ {url[:60]}: {status}")

    # Distribui para cada assinante
    print("\n🚚 Iniciando distribuição…")
    enviados = falhas = 0

    for usr in usuarios:
        nome  = usr.get("Nome",  "").strip()
        email = usr.get("Email", "").strip()

        if not nome or not email:
            continue
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            print(f"   ⚠️ E-mail inválido: '{email}' — pulando.")
            continue

        # Monta pacote respeitando a ordem personalizada do assinante
        temas_com_ordem = []
        for tema in RSS_FEEDS:
            val = str(usr.get(tema, "")).strip()
            if val.lower() in {"", "não"}:
                continue
            if tema not in CACHE_GLOBAL:
                continue
            ordem = int(val) if val.isdigit() else 999
            temas_com_ordem.append((ordem, tema))

        temas_com_ordem.sort(key=lambda x: x[0])
        pacote = {tema: CACHE_GLOBAL[tema] for _, tema in temas_com_ordem}

        if not pacote:
            print(f"   ⚠️ {nome}: nenhum tema disponível.")
            continue

        subject = montar_subject(pacote)
        print(f"   ✉️  {nome} → {list(pacote.keys())}")
        html = gerar_html_final(nome, pacote, painel, editorial=editorial)
        ok   = enviar_email(email, html, subject=subject)
        registrar_log(sheet_logs, nome, email, ok, list(pacote.keys()))

        if ok:
            enviados += 1
        else:
            falhas += 1

    print(f"\n{'─'*65}")
    print(f"✅ Concluído — Enviados: {enviados}  |  Falhas: {falhas}")


if __name__ == "__main__":
    main()
