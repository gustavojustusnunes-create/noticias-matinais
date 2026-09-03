import os
import json
from datetime import datetime
from claude_api import chamar_supervisor_api

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
                
            prompt = (
                "Você é o Editor-Chefe e Supervisor de Qualidade do All News Journal e All News Finance.\n"
                "Sua tarefa é auditar a notícia abaixo e garantir que ela esteja impecável.\n\n"
                "REGRAS DE QUALIDADE:\n"
                "1. O texto deve ser autossuficiente e ter profundidade.\n"
                "2. NÃO deve conter 'clickbait', listicles vazios, ou cortes bruscos.\n"
                "3. NÃO deve terminar com perguntas ou convites para o leitor (CTAs).\n"
                "4. NÃO deve conter emojis.\n"
                "5. NÃO deve ter linguagem robótica ou clichês excessivos.\n"
                "6. A primeira frase NÃO deve ser uma cópia exata do título.\n"
                "7. Para notícias financeiras, evite promessas exageradas de lucros e mantenha o rigor jornalístico.\n\n"
                "LIÇÕES APRENDIDAS DE ERROS ANTERIORES (O QUE NÃO REPETIR):\n"
                f"{licoes}\n\n"
                "NOTÍCIA A SER AVALIADA:\n"
                f"Título: {noticia.get('titulo', '')}\n"
                f"Texto: {resumo_original}\n\n"
                "Analise a notícia. Se ela violar qualquer regra ou lição, forneça uma versão corrigida.\n"
                "Responda ESTRITAMENTE em formato JSON com os seguintes campos:\n"
                "- \"status\": \"PASS\" se estiver perfeita, ou \"FAIL\" se tiver problemas.\n"
                "- \"motivo\": se FAIL, descreva brevemente o que estava errado.\n"
                "- \"texto_corrigido\": se FAIL, forneça o texto completo reescrito e perfeito.\n"
            )
            
            resposta_json_str = chamar_supervisor_api(prompt, max_tokens=1000)
            
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
