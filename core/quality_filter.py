"""
core/quality_filter.py — Quality Gate com Supressão Editorial Ativa
All News Journal (v2.2)

Responsável pela triagem cognitiva pré-redação:
1. Audita matérias candidatas via Google Gemini Flash (com fallback heurístico calibrado).
2. Aplica critérios de eliminação estritos:
   - Rejeição global: listas genéricas ("5 dicas", "exercícios para"), tutoriais triviais, boatos ou fofocas sem fonte.
   - Wellness: exige inovação de produto (tecnologia de tênis, bikes, wearables), negócios do esporte ou eventos internacionais.
   - IA: exige lançamentos de modelos, avanços de hardware/chips, arquitetura técnica ou casos reais corporativos.
   - Economia / Mundo / Política: densidade analítica, impacto macroeconômico, institucional ou diplomático.
3. Regra de Supressão:
   - Nota de corte de relevância: 8.0 / 10.0.
   - Se nenhuma matéria atingir score >= 8.0, o caderno é classificado como SUPPRESSED.
4. Registro de Auditoria:
   - Persiste os incidentes em logs/alertas_cadernos.json para visualização no painel administrativo.
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

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


BRT = timezone(timedelta(hours=-3))
ALERTAS_FILE = Path("logs") / "alertas_cadernos.json"

# =============================================================================
# --- CRITÉRIOS EDITORIALMENTE CODIFICADOS POR CADERNO ---
# =============================================================================
CRITERIOS_CADERNOS = {
    "Wellness": (
        "EXIGÊNCIAS: Inovação tecnológica de produto (engenharia de calçados/tênis de corrida, bikes de alto desempenho, wearables biométricos), "
        "negócios do esporte (contratos bilionários, direitos de mídia, mercado esportivo) ou grandes competições/eventos internacionais.\n"
        "REJEIÇÕES ESTRITAS: Dicas genéricas de treino caseiro, dietas para emagrecer, listas triviais ('5 exercícios para'), "
        "conselhos óbvios de saúde ou matérias de autoajuda sem base científica inovadora."
    ),
    "IA": (
        "EXIGÊNCIAS: Lançamentos de modelos de fronteira (pesos abertos/fechados), avanços de semicondutores e hardware (GPUs, NPUs), "
        "inovações de arquitetura técnica ou casos reais corporativos com métricas tangíveis de ROI.\n"
        "REJEIÇÕES ESTRITAS: Especulações filosóficas vazias, tutoriais de prompt genéricos, rumores de redes sociais ou opiniões sem anúncio oficial."
    ),
    "Economia": (
        "EXIGÊNCIAS: Decisões de política monetária (Copom, Fed, BCE), indicadores macroeconômicos (inflação, PIB, juros), "
        "balanços corporativos de peso, fusões/aquisições e movimentações estruturais de mercado.\n"
        "REJEIÇÕES ESTRITAS: Notícias de finanças pessoais triviais, promoções de varejo comuns, boatos sem números ou colunas opinativas rasas."
    ),
    "Mundo": (
        "EXIGÊNCIAS: Geopolítica de alto impacto, cúpulas internacionais (G20, Brics, ONU), acordos diplomáticos, "
        "conflitos armados estratégicos e eleições soberanas de impacto global.\n"
        "REJEIÇÕES ESTRITAS: Curiosidades bizarras internacionais, crimes comuns locais sem desdobramento institucional ou notas de tabloide."
    ),
    "Politica": (
        "EXIGÊNCIAS: Votações legislativas de impacto orçamentário/estrutural, decisões dos tribunais superiores (STF, STJ) e políticas públicas federais.\n"
        "REJEIÇÕES ESTRITAS: Declarações protocolares de políticos sem ação concreta, bate-bocas estéreis de redes sociais ou fofoca de bastidor partidário."
    ),
    "Ciencia": (
        "EXIGÊNCIAS: Descobertas científicas publicadas em periódicos revisados por pares, avanços de biotecnologia/medicina de ponta, astrofísica ou energia limpa.\n"
        "REJEIÇÕES ESTRITAS: Pseudosciência, estudos preliminares inconclusivos sem relevância ou curiosidades sensacionalistas."
    ),
    "Cinema": (
        "EXIGÊNCIAS: Movimentações financeiras de estúdios, marcos de bilheteria global, festivais internacionais de prestígio (Cannes, Veneza, Oscar) e direitos autorais/streaming.\n"
        "REJEIÇÕES ESTRITAS: Sinopses de novelas, fofocas de gravações sem impacto industrial ou listas genéricas de 'filmes para ver no fim de semana'."
    ),
    "Fofoca": (
        "EXIGÊNCIAS: Notícias com confirmação oficial, contratos milionários de celebridades na indústria de entretenimento ou impactos de reputação corporativa.\n"
        "REJEIÇÕES ESTRITAS: Suposições de namoro não confirmadas, especulações vazias de paparazzi ou posts irrelevantes de stories."
    )
}

# Padrões regex que disparam descarte imediato (Score 1.0 a 3.0)
PADROES_ELIMINACAO_GLOBAL = [
    r"\b\d+\s+(dicas|motivos|passos|alimentos|maneiras|truques|hábitos)\b",
    r"\b(como\s+emagrecer|perder\s+barriga|exercícios?\s+para)\b",
    r"\b(o\s+que\s+acontece\s+quando|você\s+não\s+vai\s+acreditar)\b",
    r"\b(veja\s+o\s+antes\s+e\s+depois|choca\s+a\s+web)\b",
    r"\b(confira\s+as\s+dicas|aprenda\s+a\s+fazer)\b",
]


# =============================================================================
# --- AVALIADOR HEURÍSTICO LOCAL (FALLBACK DETERMINÍSTICO) ---
# =============================================================================
def _avaliar_heuristica_local(caderno: str, titulo: str, snippet: str = "") -> Dict[str, Any]:
    """
    Avaliação determinística calibrada para operação offline ou sem chave de API.
    Aplica regras analíticas de corte estrito.
    """
    texto = f"{titulo} {snippet}".lower()
    
    # 1. Checa padrões de eliminação imediata
    for padrao in PADROES_ELIMINACAO_GLOBAL:
        if re.search(padrao, texto, re.IGNORECASE):
            return {
                "score": 3.0,
                "aprovado": False,
                "motivo": "Rejeitado: Padrão de lista genérica, tutorial trivial ou clickbait superficial."
            }

    # 2. Regras específicas para Wellness
    if caderno.lower() == "wellness":
        termos_inovacao = [
            "tênis", "tenis", "calçado", "tecnologia", "carbono", "bike", "bicicleta",
            "wearable", "biométrico", "smartwatch", "sensor", "patrocínio", "contrato",
            "milhões", "bilhões", "maratona", "olimpíada", "mundial", "wada", "ironman",
            "estudo clínico", "performance", "inovação"
        ]
        termos_rejeicao_wellness = [
            "emagrecer", "barriga", "dieta", "receita", "suco", "treino em casa",
            "alongamento", "postura", "dicas para dormir", "alimentação saudável", "beba água"
        ]
        if any(term in texto for term in termos_rejeicao_wellness):
            return {
                "score": 4.5,
                "aprovado": False,
                "motivo": "Rejeitado em Wellness: Conteúdo de dieta genérica ou treino trivial sem inovação de produto ou negócios."
            }
        if any(term in texto for term in termos_inovacao):
            return {
                "score": 8.8,
                "aprovado": True,
                "motivo": "Aprovado em Wellness: Notícia focada em tecnologia de equipamento esportivo ou negócios."
            }
        return {
            "score": 6.0,
            "aprovado": False,
            "motivo": "Rejeitado em Wellness: Ausência de produto tecnológico inovador ou evento de relevância comprovada."
        }

    # 3. Regras específicas para IA
    if caderno.lower() == "ia":
        termos_tecnicos_ia = [
            "modelo", "llm", "gemini", "gpt", "claude", "anthropic", "openai", "nvidia",
            "hardware", "chip", "semicondutor", "gpu", "parâmetros", "benchmark",
            "arquitetura", "datacenter", "infraestrutura", "investimento", "patente", "empresa"
        ]
        termos_rejeicao_ia = [
            "como usar", "prompts para", "vai roubar seu emprego?", "curiosidade", "ilusão"
        ]
        if any(term in texto for term in termos_rejeicao_ia):
            return {
                "score": 4.0,
                "aprovado": False,
                "motivo": "Rejeitado em IA: Tutorial trivial ou especulação sem avanço técnico comprovado."
            }
        if any(term in texto for term in termos_tecnicos_ia):
            return {
                "score": 9.0,
                "aprovado": True,
                "motivo": "Aprovado em IA: Lançamento de modelo, infraestrutura de hardware ou caso empresarial relevante."
            }
        return {
            "score": 6.5,
            "aprovado": False,
            "motivo": "Rejeitado em IA: Notícia sem densidade técnica ou institucional suficiente."
        }

    # 4. Regras gerais para outros cadernos
    if len(titulo.split()) < 5:
        return {
            "score": 5.0,
            "aprovado": False,
            "motivo": "Rejeitado: Título curto demais ou vago."
        }

    # Se passar sem gatilhos negativos e tiver extensão jornalística adequada
    return {
        "score": 8.2,
        "aprovado": True,
        "motivo": "Aprovado por conformidade com a pauta editorial analítica."
    }


# =============================================================================
# --- VALIDADOR COGNITIVO COM GEMINI FLASH ---
# =============================================================================
def _avaliar_com_gemini_flash(caderno: str, candidatas: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """
    Avalia em batch as matérias candidatas utilizando o Google Gemini Flash.
    Retorna lista de dicionários com 'indice', 'score', 'aprovado' e 'motivo'.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        return None

    criterios_especificos = CRITERIOS_CADERNOS.get(caderno, "Exija profundidade analítica, fatos verificáveis e alta densidade informativa.")

    bloco_materias = []
    for idx, c in enumerate(candidatas):
        t = c.get("title", "")
        s = c.get("summary") or c.get("snippet") or ""
        bloco_materias.append(f"[{idx}] Título: {t}\nTrecho/Contexto: {s[:250]}")

    prompt = (
        "Você é o Diretor Editorial Chefe do All News Journal, responsável pelo Quality Gate de admissão de pautas.\n"
        f"CADERNO: {caderno.upper()}\n\n"
        f"DIRETRIZES DE RELEVÂNCIA DO CADERNO:\n{criterios_especificos}\n\n"
        "CRITÉRIOS DE CORTE (Escala 0.0 a 10.0):\n"
        "- Score >= 8.0: Apenas fatos de alto impacto, lançamentos reais de produtos/tecnologias, negócios e dados substantivos.\n"
        "- Score < 8.0: Listas genéricas ('5 dicas'), treinos/dietas triviais, tutoriais comuns, fofocas vazias ou notícias sem densidade analítica.\n\n"
        "AVALIE CADA MATÉRIA ABAIXO:\n"
        + "\n\n".join(bloco_materias)
        + "\n\nResponda ESTRITAMENTE em formato JSON com o array 'avaliacoes', contendo:\n"
        "[\n"
        "  {\n"
        "    \"indice\": 0,\n"
        "    \"score\": 8.5,\n"
        "    \"aprovado\": true,\n"
        "    \"motivo\": \"Justificativa concisa em 1 frase\"\n"
        "  }\n"
        "]"
    )

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash-latest",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        resp = None
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                resp = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.15,
                        response_mime_type="application/json"
                    ),
                    request_options={"timeout": 15}
                )
                if resp and resp.text:
                    break
            except Exception:
                continue

        if resp and resp.text:
            dados = json.loads(resp.text)
            if isinstance(dados, dict) and "avaliacoes" in dados:
                return dados["avaliacoes"]
            if isinstance(dados, list):
                return dados
    except Exception as e:
        print(f"   ⚠️ [quality_filter] Falha no Gemini Flash ({e}). Acionando fallback heurístico...")

    return None


# =============================================================================
# --- FUNÇÃO PRINCIPAL DE TRIAGEM ---
# =============================================================================
def triar_caderno_com_ia(caderno: str, candidatas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executa a triagem de relevância no caderno:
    - Retorna dict com status 'APPROVED' ou 'SUPPRESSED'.
    - Se nenhuma matéria atingir score >= 8.0/10, classifica o caderno como SUPPRESSED
      e grava o alerta em logs/alertas_cadernos.json.
    """
    if not candidatas:
        motivo = f"Nenhuma matéria bruta foi coletada para o caderno '{caderno}'."
        registrar_alerta_caderno(caderno, motivo, [])
        return {
            "caderno": caderno,
            "status": "SUPPRESSED",
            "motivo_supressao": motivo,
            "materias_aprovadas": [],
            "materias_descartadas": []
        }

    # 1. Tenta avaliação cognitiva via Gemini Flash
    avaliacoes = _avaliar_com_gemini_flash(caderno, candidatas)

    # 2. Se falhar ou indisponível, recorre ao avaliador heurístico calibrado
    if not avaliacoes or len(avaliacoes) != len(candidatas):
        avaliacoes = []
        for idx, c in enumerate(candidatas):
            res_heur = _avaliar_heuristica_local(
                caderno=caderno,
                titulo=c.get("title", ""),
                snippet=c.get("summary") or c.get("snippet") or ""
            )
            avaliacoes.append({
                "indice": idx,
                "score": res_heur["score"],
                "aprovado": res_heur["aprovado"],
                "motivo": res_heur["motivo"]
            })

    materias_aprovadas = []
    materias_descartadas = []

    for av in avaliacoes:
        idx = av.get("indice", 0)
        if 0 <= idx < len(candidatas):
            item = candidatas[idx]
            item["quality_score"] = float(av.get("score", 0.0))
            item["quality_motivo"] = av.get("motivo", "")
            
            # Regra de corte estrita: score >= 8.0
            if item["quality_score"] >= 8.0:
                materias_aprovadas.append(item)
            else:
                materias_descartadas.append(item)

    # Ordena as aprovadas pelo score decrescente
    materias_aprovadas.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)

    # 3. REGRA DE SUPRESSÃO ATIVA: Se nenhuma matéria atingiu nota >= 8.0
    if not materias_aprovadas:
        titulos_descartados = [m.get("title", "Sem título") for m in materias_descartadas[:5]]
        motivo_supressao = (
            f"Nenhuma das {len(candidatas)} matérias coletadas atingiu o padrão de relevância analítica "
            f"(nota de corte 8.0/10). Maior nota alcançada: "
            f"{max([m.get('quality_score', 0.0) for m in materias_descartadas], default=0.0):.1f}/10."
        )
        # Registra alerta no log
        registrar_alerta_caderno(caderno, motivo_supressao, titulos_descartados)
        print(f"      🛑 [Quality Gate] Caderno '{caderno}' SUPRIMIDO. Motivo: {motivo_supressao}")

        return {
            "caderno": caderno,
            "status": "SUPPRESSED",
            "motivo_supressao": motivo_supressao,
            "materias_aprovadas": [],
            "materias_descartadas": materias_descartadas
        }

    print(f"      ✨ [Quality Gate] Caderno '{caderno}' APROVADO: {len(materias_aprovadas)} matéria(s) com score >= 8.0.")
    return {
        "caderno": caderno,
        "status": "APPROVED",
        "motivo_supressao": None,
        "materias_aprovadas": materias_aprovadas,
        "materias_descartadas": materias_descartadas
    }


# =============================================================================
# --- PERSISTÊNCIA DE ALERTAS EM logs/alertas_cadernos.json ---
# =============================================================================
def registrar_alerta_caderno(caderno: str, motivo: str, descartados: List[str], data_str: Optional[str] = None) -> None:
    """Registra um incidente de supressão no arquivo logs/alertas_cadernos.json."""
    if data_str is None:
        data_str = datetime.now(BRT).strftime("%Y-%m-%d")

    ALERTAS_FILE.parent.mkdir(parents=True, exist_ok=True)

    historico = []
    if ALERTAS_FILE.exists():
        try:
            with open(ALERTAS_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    historico = dados
        except Exception:
            historico = []

    novo_registro = {
        "data": data_str,
        "caderno": caderno,
        "status": "SUPPRESSED",
        "motivo": motivo,
        "exemplos_descartados": descartados,
        "timestamp": datetime.now(BRT).isoformat()
    }

    # Substitui se já houver um registro do mesmo caderno na mesma data ou adiciona novo
    substituido = False
    for i, item in enumerate(historico):
        if item.get("data") == data_str and item.get("caderno") == caderno:
            historico[i] = novo_registro
            substituido = True
            break

    if not substituido:
        historico.append(novo_registro)

    try:
        temp_file = ALERTAS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
        temp_file.replace(ALERTAS_FILE)
    except Exception as e:
        print(f"   ⚠️ [quality_filter] Erro ao salvar alerta de caderno: {e}")


def obter_alertas_cadernos(data_filtro: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna os alertas de cadernos suprimidos, opcionalmente filtrados por data."""
    if not ALERTAS_FILE.exists():
        return []
    try:
        with open(ALERTAS_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if not isinstance(dados, list):
                return []
            if data_filtro:
                return [item for item in dados if item.get("data") == data_filtro]
            return sorted(dados, key=lambda x: x.get("data", ""), reverse=True)
    except Exception as e:
        print(f"   ⚠️ [quality_filter] Erro ao ler alertas de cadernos: {e}")
        return []


def remover_alerta_caderno(caderno: str, data_str: Optional[str] = None) -> bool:
    """Remove o alerta de supressão de um caderno após contingência manual."""
    if data_str is None:
        data_str = datetime.now(BRT).strftime("%Y-%m-%d")

    if not ALERTAS_FILE.exists():
        return False

    try:
        with open(ALERTAS_FILE, "r", encoding="utf-8") as f:
            historico = json.load(f)
            if not isinstance(historico, list):
                return False

        filtrado = [
            item for item in historico
            if not (item.get("data") == data_str and item.get("caderno") == caderno)
        ]

        with open(ALERTAS_FILE, "w", encoding="utf-8") as f:
            json.dump(filtrado, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"   ⚠️ [quality_filter] Erro ao remover alerta de caderno: {e}")
        return False
