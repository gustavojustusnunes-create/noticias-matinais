import os
import json
import time
from datetime import datetime
from claude_api import chamar_supervisor_api

# Integração do modelo de decisão estruturada TypeSafe Jev (System 1)
try:
    from core.jev_gatekeeper import quick_triage_supervisor, auditar_resumo_critic
except ImportError:
    from jev_gatekeeper import quick_triage_supervisor, auditar_resumo_critic

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "supervisor_memory.json")

def carregar_memoria():
    if not os.path.exists(MEMORY_FILE):
        return {"erros": [], "imagens_recentes": []}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"erros": data, "imagens_recentes": []}
            if "erros" not in data:
                data["erros"] = []
            return data
    except Exception as e:
        print(f"      ⚠️ Erro ao carregar memória do supervisor: {e}")
        return {"erros": [], "imagens_recentes": []}

def salvar_memoria(memoria):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"      ⚠️ Erro ao salvar memória do supervisor: {e}")

def obter_licoes_aprendidas(memoria, limite=10):
    """
    Retorna as lições aprendidas formatadas para o prompt, pegando os erros mais recentes.
    """
    erros = memoria.get("erros", [])
    if not erros:
        return "Nenhuma lição anterior."
    
    licoes = []
    # Pegar os últimos 'limite' erros para não poluir muito o prompt
    for m in erros[-limite:]:
        licoes.append(f"- Evite: {m['motivo_falha']}. Exemplo de correção aplicada: {m.get('correcao_aplicada', '')}")
    
    return "\n".join(licoes)

def revisar_edicao_diaria(cache_global):
    """
    Audita e corrige as notícias geradas, atualizando a memória de aprendizado.
    """
    memoria = carregar_memoria()
    licoes = obter_licoes_aprendidas(memoria)
    
    novos_erros = []
    
    print("\n🕵️  Iniciando Supervisão e Auditoria de Qualidade da IA...")
    
    
    # --- NOVO: NÓ 3 - GUARDRALL ANTI-PLACEBO (VALIDADOR DE QUALIDADE) ---
    print("   🛡️ Executando NÓ 3: Guardrail Anti-Placebo...")
    todas_noticias = []
    for tema, noticias in cache_global.items():
        for i, noti in enumerate(noticias):
            todas_noticias.append((tema, i, noti))
    
    # 1. Similaridade Lexical do Resumo > 40%
    para_remover = set()
    for idx1, (tema1, i1, noti1) in enumerate(todas_noticias):
        if (tema1, i1) in para_remover: continue
        resumo1 = noti1.get("resumo", "")
        if not resumo1 or resumo1.strip().upper() == "SKIP": continue
        p1 = set(w.lower() for w in resumo1.split() if len(w) > 3)
        
        for idx2, (tema2, i2, noti2) in enumerate(todas_noticias[idx1+1:], start=idx1+1):
            if (tema2, i2) in para_remover: continue
            resumo2 = noti2.get("resumo", "")
            if not resumo2 or resumo2.strip().upper() == "SKIP": continue
            p2 = set(w.lower() for w in resumo2.split() if len(w) > 3)
            
            if p1 and p2:
                intersecao = p1.intersection(p2)
                menor = min(len(p1), len(p2))
                if menor > 0 and (len(intersecao) / menor) > 0.40:
                    print(f"      🚫 Anti-Placebo: Similaridade de resumo > 40% detectada entre '{noti1.get('titulo')[:30]}' e '{noti2.get('titulo')[:30]}'. Abortando a segunda.")
                    para_remover.add((tema2, i2))

    # 2. Expressões proibidas & 3. Sujeira no Título
    for tema, i, noti in todas_noticias:
        if (tema, i) in para_remover: continue
        
        # Expressões proibidas
        resumo = noti.get("resumo", "")
        if "dinâmica competitiva nos mercados do caderno" in resumo or "alocação de capital das entidades envolvidas" in resumo:
            print(f"      🚫 Anti-Placebo: Expressões placebo detectadas em '{noti.get('titulo')[:30]}'. Abortando matéria.")
            para_remover.add((tema, i))
            continue
            
        # Limpeza de Título
        titulo = noti.get("titulo", "")
        if titulo:
            import re as re_mod
            titulo_limpo = re_mod.sub(r"\(Reprodução/.*?\)", "", titulo, flags=re_mod.IGNORECASE)
            titulo_limpo = re_mod.sub(r"Foto:.*?$", "", titulo_limpo, flags=re_mod.IGNORECASE)
            if titulo_limpo != titulo:
                print(f"      🧹 Anti-Placebo: Título limpo de metadados: '{titulo_limpo.strip()}'")
                cache_global[tema][i]["titulo"] = titulo_limpo.strip()

    # Reconstruindo o cache_global removendo as inválidas
    for tema in cache_global.keys():
        novas_noticias = [noti for i, noti in enumerate(cache_global[tema]) if (tema, i) not in para_remover]
        cache_global[tema] = novas_noticias

    # --- Passo Zero: Deduplicação Semântica de Notícias de Grande Impacto ---
    print("   🔍 Removendo notícias repetidas sobre o mesmo assunto...")
    for tema, noticias in cache_global.items():
        unicas = []
        for noti in noticias:
            duplicada = False
            # Conjunto de palavras significativas do título (ignorando preposições curtas)
            palavras_noti = set(w.lower() for w in noti.get("titulo", "").split() if len(w) > 3)
            for u in unicas:
                palavras_u = set(w.lower() for w in u.get("titulo", "").split() if len(w) > 3)
                if palavras_noti and palavras_u:
                    intersecao = palavras_noti.intersection(palavras_u)
                    menor_conjunto = min(len(palavras_noti), len(palavras_u))
                    # Se mais de 55% das palavras da menor frase forem iguais, é a mesma notícia
                    if menor_conjunto > 0 and len(intersecao) / menor_conjunto > 0.55:
                        duplicada = True
                        break
            if not duplicada:
                unicas.append(noti)
        cache_global[tema] = unicas

    for tema, noticias in cache_global.items():
        if not noticias:
            continue
            
        print(f"   🔎 Auditando {tema} ({len(noticias)} notícias)...")
        
        for i, noticia in enumerate(noticias):
            resumo_original = noticia.get("resumo", "")
            if not resumo_original or resumo_original.strip().upper() == "SKIP":
                continue
                
            # --- Jev System 1: Auditoria Ultrarrápida (< 15ms) ---
            auditoria = auditar_resumo_critic(resumo_original)
            if auditoria.get("aprovado") is True:
                # Notícia aprovada pelo Quality Gate oficial: conformidade perfeita com 60-90 palavras
                continue

            motivo_audit = auditoria.get("motivo_rejeicao", "")
            instrucao_audit = auditoria.get("instrucao_reescrita", "")

            prompt = (
                "Você é o Editor-Chefe e Supervisor de Qualidade do All News Journal e All News Finance.\n"
                "Sua tarefa é auditar a notícia abaixo e garantir que ela esteja impecável e no padrão oficial do SYSTEM_PROMPT_WRITER (Padrão The Economist).\n\n"
                "DIRETRIZES RÍGIDAS DE REDAÇÃO:\n"
                "1. EXTENSÃO OBRIGATÓRIA: O texto DEVE conter rigorosamente entre 60 e 90 palavras (tolerância operacional 58 a 92).\n"
                "2. ESTRUTURA DOS TRÊS PASSOS (THE ECONOMIST):\n"
                "   - Passo 1 (O Fato): 1 frase direta com sujeito da ação, dados quantitativos e o evento central sem rodeios.\n"
                "   - Passo 2 (Contexto & Mecânica): 1 ou 2 frases explicando as forças estruturais (pressão de custos, regulação, incentivos geopolíticos).\n"
                "   - Passo 3 (O Desdobramento Crítico / So What?): 1 frase apontando quem ganha, quem perde e qual o risco imediato a ser monitorado.\n"
                "3. PROIBIÇÃO ABSOLUTA: NUNCA gere frases como 'estabelecem uma nova dinâmica competitiva', 'impactos substanciais na cadeia operacional', 'acompanhado de perto por analistas'.\n"
                "4. LIMPEZA TOTAL: Remova imediatamente créditos de imagens (ex: 'Foto: Getty'), legendas e nomes de agências (Reuters, BBC, G1).\n"
                "5. PONTUAÇÃO FINAL: O texto DEVE obrigatoriamente terminar com ponto final (.) e ter sentido completo.\n\n"
                f"APONTAMENTO DO QUALITY GATE:\n{motivo_audit} | {instrucao_audit}\n\n"
                "LIÇÕES APRENDIDAS DE ERROS ANTERIORES:\n"
                f"{licoes}\n\n"
                "NOTÍCIA A SER REAVALIADA E CORRIGIDA:\n"
                f"Título: {noticia.get('titulo', '')}\n"
                f"Texto Original: {resumo_original}\n\n"
                "Forneça a versão corrigida em 3 passos com rigorosamente entre 60 e 90 palavras.\n"
                "Responda ESTRITAMENTE em formato JSON com os seguintes campos:\n"
                "- \"status\": \"PASS\" se estiver perfeita, ou \"FAIL\" se tiver problemas.\n"
                "- \"motivo\": se FAIL, descreva brevemente o que estava errado.\n"
                "- \"texto_corrigido\": se FAIL, forneça o texto completo reescrito e perfeito (entre 60 e 90 palavras).\n"
            )
            
            resposta_json_str = chamar_supervisor_api(prompt, max_tokens=2048)
            time.sleep(2.5)  # Pausa essencial para respeitar a cota RPM da API e evitar 429
            
            if not resposta_json_str:
                continue
                
            try:
                # O modelo às vezes retorna Markdown code blocks mesmo em JSON mode
                if resposta_json_str.startswith("```json"):
                    resposta_json_str = resposta_json_str[7:]
                if resposta_json_str.endswith("```"):
                    resposta_json_str = resposta_json_str[:-3]
                    
                avaliacao = json.loads(resposta_json_str)
                
                if avaliacao.get("status") == "FAIL" and avaliacao.get("texto_corrigido"):
                    print(f"      ⚠️  Corrigido: {noticia.get('titulo')[:40]}... -> Motivo: {avaliacao.get('motivo')}")
                    # Aplica a correção
                    cache_global[tema][i]["resumo"] = avaliacao["texto_corrigido"]
                    
                    # Salva o aprendizado
                    novos_erros.append({
                        "data": datetime.now().isoformat(),
                        "tema": tema,
                        "texto_original": resumo_original,
                        "motivo_falha": avaliacao.get("motivo"),
                        "correcao_aplicada": avaliacao.get("texto_corrigido")[:100] + "..." # Salva só um trecho para não explodir o JSON
                    })
            except json.JSONDecodeError:
                print(f"      ⚠️  Erro ao decodificar JSON do supervisor para a notícia: {noticia.get('titulo')[:40]}")
            except Exception as e:
                print(f"      ⚠️  Erro inesperado no supervisor: {e}")

    if novos_erros:
        print(f"   🧠 O Supervisor aprendeu {len(novos_erros)} nova(s) lição(ões) hoje.")
        erros = memoria.get("erros", [])
        erros.extend(novos_erros)
        memoria["erros"] = erros
        salvar_memoria(memoria)
    else:
        print("   ✅ Todas as notícias passaram na auditoria com perfeição.")
        
    return cache_global
