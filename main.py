"""
main.py — Motor principal do All News Journal v15.1 (Sem IA Externa)
Orquestra: coleta RSS → email.
Para detalhes de cada etapa, veja os módulos especializados.
"""
import re
import random # Adicionado para rotacionar as aberturas

# Importações limpas: CLAUDE_KEY e claude_api removidos
from config import RSS_FEEDS, EMAIL_SENDER, EMAIL_PASSWORD, GCP_JSON, MAPEAMENTO_LEGADO
from sheets_db import conectar_banco, carregar_historico, salvar_no_historico, registrar_log, obter_coluna_editorial
from feeds import processar_tema, FEEDS_STATUS
from email_builder import obter_indicadores, gerar_html_final, enviar_email, montar_subject
from claude_api import gerar_keyword_imagem

def validar_ambiente():
    variaveis = {
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
    Gera a frase de abertura editorial do dia.
    Refatorado: Substitui a chamada de API (Claude) por saudações dinâmicas pré-definidas 
    para zerar custos e aumentar a velocidade de execução.
    """
    # Verifica se há qualquer notícia hoje antes de gerar a abertura
    tem_noticias = any(items for items in cache_global.values() if items)
    
    if not tem_noticias:
        return ""

    aberturas = [
        "Aqui estão os principais destaques selecionados para você hoje.",
        "Fique por dentro do que está movimentando o mercado com nossa seleção diária.",
        "Sua dose diária de informação essencial, direto ao ponto.",
        "As notícias que vão ditar o ritmo do seu dia já estão aqui.",
        "Uma curadoria exclusiva com os temas que mais importam para você hoje."
    ]
    
    return random.choice(aberturas)

def main():
    print("🚀 All News Journal — Motor v15.1 (Lean Edition)")
    print("   Módulos: config | feeds | email_builder | sheets_db")
    print("─" * 65)

    if not validar_ambiente():
        return

    planilha, sheet_usuarios, sheet_historico, sheet_logs = conectar_banco()
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
    titulos_selecionados = []

    for tema in temas_demandados:
        resultado = processar_tema(tema, historico_hashes, titulos_selecionados)
        if resultado:
            CACHE_GLOBAL[tema] = resultado
            novas.extend(resultado)
            print(f"      ✅ {tema}: {len(resultado)} notícias prontas.")
        else:
            print(f"      ⚠️ {tema}: nenhuma notícia disponível hoje.")

    if novas:
        salvar_no_historico(sheet_historico, novas)
        print(f"   💾 {len(novas)} notícias salvas no histórico.")

    # Busca coluna do autor (se houver agendada para hoje)
    print("   ✍️  Verificando Coluna do Autor (Editorial) no banco…")
    coluna_autor = obter_coluna_editorial(planilha)
    
    # Frase de abertura padrão
    abertura_padrao = gerar_editorial(CACHE_GLOBAL)

    if coluna_autor:
        print(f"   📝 Editorial encontrado: {coluna_autor['titulo']}")
        keyword = gerar_keyword_imagem(coluna_autor['texto'])
        coluna_autor["imagem"] = f"https://images.unsplash.com/featured/600x300/?{keyword}&sig=editorial"
    else:
        print("   ℹ️  Nenhum editorial para hoje.")

    # Resumo de status dos feeds
    feeds_ok     = sum(1 for s in FEEDS_STATUS.values() if s.startswith("ok"))
    feeds_falhas = [(url, s) for url, s in FEEDS_STATUS.items() if not s.startswith("ok")]
    print(f"   📡 Status dos feeds: {feeds_ok} OK | {len(feeds_falhas)} falha(s)")
    if feeds_falhas:
        for url, status in feeds_falhas[:5]:  # mostra só as 5 primeiras
            print(f"      ⚠️ {url[:60]}: {status}")

    # Distribui para cada assinante
    print("\n🚚 Iniciando distribuição…")
    print(f"   👥 {len(usuarios)} assinante(s) na planilha.")
    enviados = falhas = pulados = erros = 0

    for usr in usuarios:
        # IMPORTANTE: cada assinante é processado de forma isolada. Se UM der
        # erro (HTML, envio, log, etc.), capturamos e seguimos para o próximo —
        # um problema com um assinante NUNCA pode impedir os demais de receber.
        nome = email = ""
        try:
            nome  = usr.get("Nome",  "").strip()
            email = usr.get("Email", "").strip()

            if not nome or not email:
                pulados += 1
                continue
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                print(f"   ⚠️ E-mail inválido: '{email}' — pulando.")
                pulados += 1
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
                print(f"   ⚠️ {nome}: nenhum tema disponível hoje — pulando.")
                pulados += 1
                continue

            subject = montar_subject(pacote)
            print(f"   ✉️  {nome} <{email}> → {list(pacote.keys())}")
            html = gerar_html_final(nome, pacote, painel, editorial=abertura_padrao, coluna_autor=coluna_autor)
            ok   = enviar_email(email, html, subject=subject)
            registrar_log(sheet_logs, nome, email, ok, list(pacote.keys()))

            if ok:
                enviados += 1
            else:
                falhas += 1

        except Exception as e:
            # Não deixa o erro de um assinante derrubar o restante da fila.
            erros += 1
            print(f"   ❌ Erro ao processar {nome or '?'} <{email or '?'}>: {e}")
            continue

    print(f"\n{'─'*65}")
    print(f"✅ Concluído — Enviados: {enviados} | Falhas: {falhas} | "
          f"Pulados: {pulados} | Erros: {erros}")

    # ── [NOVO] Publica a edição do dia no site (não afeta o e-mail) ──
    try:
        from site_publisher import publicar_edicao
        print("\n🌐 Publicando edição no site…")
        publicar_edicao(CACHE_GLOBAL, painel, abertura_padrao, coluna_autor)
    except Exception as e:
        print(f"   ⚠️ Falha ao publicar no site (e-mail não afetado): {e}")

    # ── [NOVO] Gera Podcast da Edição (Estilo NotebookLM) ──
    try:
        from podcast_builder import compilar_podcast
        print("\n🎙️  Gerando Podcast Diário...")
        # Usa o mesmo CACHE_GLOBAL. Adiciona a data para a função compilar_podcast
        edicao_podcast = CACHE_GLOBAL.copy()
        edicao_podcast["data"] = datetime.now().strftime("%Y-%m-%d")
        compilar_podcast(edicao_podcast)
    except Exception as e:
        print(f"   ⚠️ Falha ao gerar podcast: {e}")

if __name__ == "__main__":
    main()
