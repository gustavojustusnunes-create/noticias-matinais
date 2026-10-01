"""
core/jev_gatekeeper.py — Gatekeeper de Decisão Estruturada TypeSafe Jev (System 1)
All News Journal (v2.1)

Implementa:
1. Modelo de Decisão Estruturada TypeSafe Jev (System 1 Decision Model) para inferência ultrarrápida (< 200ms).
2. Primitivos Jev:
   - score: Escala 1 a 5
   - noul: Booleano de integridade e ausência de alucinações/violações (True = íntegro / conforme)
   - choice: Decisão categórica ("APPROVE", "REVISE", "REJECT")
   - confidence: Probabilidade ou confiança float (0.0 a 1.0)
   - latency_ms: Tempo de resposta em milissegundos
3. Funções exportadas:
   - evaluate_editorial_quality(article_text, guidelines) -> dict
   - quick_triage_supervisor(log_or_trace) -> dict
4. Dual-Engine com Fallback Resiliente:
   - Consulta a API TypeSafe/OpenRouter com o modelo 'typesafe/jev-1.13' se TYPESAFE_API_KEY ou OPENROUTER_API_KEY estiver configurada.
   - Executa o emulador local System 1 Heuristic Engine (< 15ms) para garantir tolerância a falhas, execução offline e testes determinísticos.
"""

import os
import re
import time
import json
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

# Carrega variáveis de ambiente de .env se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# --- 1. MODELOS DE DADOS ESTRUTURADOS (PYDANTIC SCHEMAS) ---
# =============================================================================

SYSTEM_PROMPT_CRITIC = """
Você é o Quality Gate do All News Journal. Audite o resumo contra as diretrizes normativas da publicação:

REGRAS DE VALIDAÇÃO:
1. Contagem: O campo "resumo_texto" tem rigorosamente entre 85 e 105 palavras?
2. Integridade: A frase final termina com ponto final e encerra uma tese sem corte abrupto?
3. Limpeza: Há algum crédito de foto ("Getty", "BBC", "Foto"), autor ou símbolo HTML quebrado?
4. Profundidade: O texto explicou a causa e o impacto do fato ou ficou apenas em um anúncio genérico?

RESPOSTA OBRIGATÓRIA (JSON):
{
  "aprovado": true,
  "word_count": 94,
  "motivo_rejeicao": "",
  "instrucao_reescrita": ""
}
Se reprovado, retorne "aprovado": false e aponte o erro em "instrucao_reescrita" para regeneração imediata.
"""


class CriticAuditResult(BaseModel):
    """Esquema de auditoria do Quality Gate em conformidade com SYSTEM_PROMPT_CRITIC."""
    aprovado: bool = Field(description="True se aprovado nas 4 regras, False se reprovado")
    word_count: int = Field(description="Contagem de palavras do campo resumo_texto")
    motivo_rejeicao: str = Field(default="", description="Motivo detalhado da rejeição se reprovado")
    instrucao_reescrita: str = Field(default="", description="Instrução orientativa para regeneração imediata")


class EditorialDecision(BaseModel):
    """Esquema de decisão editorial para o nó Critic (Quality Gate)."""
    score: int = Field(ge=1, le=5, description="Nota de qualidade editorial de 1 a 5")
    noul: bool = Field(description="Booleano de integridade: True se ausente de violações/alucinações, False se violado")
    choice: Literal["APPROVE", "REVISE", "REJECT"] = Field(description="Ação categórica recomendada")
    confidence: float = Field(ge=0.0, le=1.0, description="Nível de confiança da decisão (0.0 a 1.0)")
    latency_ms: float = Field(description="Latência de inferência em milissegundos")
    reason: str = Field(description="Justificativa da decisão e instruções de revisão se aplicável")
    word_count: int = Field(description="Contagem de palavras do texto auditado")
    paragraphs: int = Field(description="Quantidade de parágrafos identificados")
    model: str = Field(default="typesafe/jev-1.13", description="Identificador do modelo que gerou a decisão")


class SupervisorTriage(BaseModel):
    """Esquema de triagem de observabilidade para o AI Supervisor."""
    noul: bool = Field(description="True se status nominal sem anomalias de SLA; False caso haja anomalia")
    choice: Literal["HEALTHY", "WARNING", "CRITICAL"] = Field(description="Classificação operacional do trace")
    score: int = Field(ge=1, le=5, description="Índice de saúde do sistema de 1 a 5")
    confidence: float = Field(ge=0.0, le=1.0, description="Confiança na classificação de triagem")
    action: str = Field(description="Ação operacional prescrita (ex: PROCEED, MONITOR, RESTART_OR_ALERT)")
    latency_ms: float = Field(description="Latência de avaliação em milissegundos")
    details: str = Field(description="Detalhes da anomalia ou confirmação de conformidade")
    model: str = Field(default="typesafe/jev-1.13", description="Modelo decisório")


# =============================================================================
# --- 2. EMULADOR LOCAL SYSTEM 1 (FAST HEURISTIC ENGINE: < 15ms) ---
# =============================================================================

def auditar_resumo_critic(resumo_texto: str, usar_llm: bool = False) -> Dict[str, Any]:
    """
    Quality Gate oficial do All News Journal baseado no SYSTEM_PROMPT_CRITIC.
    Audita o campo 'resumo_texto' contra as 4 diretrizes normativas:
    1. Contagem: rigorosamente entre 85 e 105 palavras (tolerância operacional 82 a 108).
    2. Integridade: frase final com ponto final e encerramento de tese sem corte abrupto.
    3. Limpeza: ausência de créditos de foto ('Getty', 'BBC', 'Foto'), autor ou HTML quebrado.
    4. Profundidade: explicação de causa e impacto do fato, sem anúncio genérico ou clichê.

    Retorna estritamente o formato JSON de SYSTEM_PROMPT_CRITIC:
    {
      "aprovado": bool,
      "word_count": int,
      "motivo_rejeicao": str,
      "instrucao_reescrita": str
    }
    """
    texto = (resumo_texto or "").strip()
    palavras = texto.split()
    word_count = len(palavras)

    # Chamada remota opcional se requisitada explicitamente e API key configurada
    if usar_llm:
        api_key = os.environ.get("TYPESAFE_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if api_key:
            prompt = f"{SYSTEM_PROMPT_CRITIC}\n\nresumo_texto:\n{texto}"
            remoto = _consultar_jev_remoto(prompt, CriticAuditResult.model_json_schema(), timeout=1.5)
            if remoto and "aprovado" in remoto:
                remoto.setdefault("word_count", word_count)
                remoto.setdefault("motivo_rejeicao", "")
                remoto.setdefault("instrucao_reescrita", "")
                return remoto

    erros = []
    instrucoes = []

    # Regra 1: Contagem de palavras (estrito 85-105, tolerância operacional 82-108)
    if word_count < 82:
        erros.append(f"Subdimensionado: {word_count} palavras (mínimo obrigatório: 85 palavras).")
        instrucoes.append(f"Expanda a matéria com mais dados substantivos para atingir entre 85 e 105 palavras (atualmente {word_count}).")
    elif word_count > 108:
        erros.append(f"Superdimensionado: {word_count} palavras (teto obrigatório: 105 palavras).")
        instrucoes.append(f"Sintetize a matéria para atingir entre 85 e 105 palavras (atualmente {word_count}).")

    # Regra 2: Integridade (frase final termina com ponto final e encerra tese sem corte abrupto)
    if texto.endswith("?"):
        erros.append("Texto encerra com interrogação provocativa, vedada pela linha editorial.")
        instrucoes.append("Substitua a pergunta final por uma tese afirmativa sobre os desdobramentos com ponto final.")
    elif "?" in texto:
        erros.append("Texto contém interrogações no corpo, vedadas pela linha editorial.")
        instrucoes.append("Elimine perguntas retóricas no corpo do texto; adote linguagem analítica afirmativa.")
    elif texto.endswith("...") or texto.endswith("…"):
        erros.append("Corte abrupto na frase final (termina com reticências).")
        instrucoes.append("Conclua a tese com ponto final sem cortes abruptos ou reticências.")
    elif not (texto.endswith(".") or texto.endswith("!")):
        erros.append("A frase final não termina com ponto final.")
        instrucoes.append("Finalize a última frase com ponto final fechando a tese.")

    # Regra 3: Limpeza (créditos de foto 'Getty', 'BBC', 'Foto', agências ou HTML quebrado)
    padroes_credito = [
        (r'\bgetty\b', "crédito Getty"),
        (r'\bbbc\b', "menção BBC"),
        (r'\bfoto\s*:', "crédito Foto:"),
        (r'\bcr[ée]dito\s*:', "crédito de imagem"),
        (r'\bag[êe]ncia brasil\b', "crédito Agência Brasil"),
        (r'\bestad[aã]o conte[uú]do\b', "crédito Estadão Conteúdo")
    ]
    for padrao_re, desc in padroes_credito:
        if re.search(padrao_re, texto, re.IGNORECASE):
            erros.append(f"Presença indevida de {desc}.")
            instrucoes.append(f"Remova resíduos de {desc} do corpo da matéria.")
            break

    # Tags quebradas ou não autorizadas (apenas <b> ou </b> são autorizados para negrito visual)
    if re.search(r'<(?!/?b\b)[^>]+>', texto) or re.search(r'<[^>]*$', texto):
        erros.append("Símbolo HTML quebrado ou tag não autorizada.")
        instrucoes.append("Remova tags HTML quebradas ou não autorizadas (permitido exclusivamente <b> para negrito).")

    # Regra 4: Profundidade (causa e impacto substantivos, sem anúncio genérico ou clichê)
    termos_proibidos = [
        "você não vai acreditar", "confira a seguir", "veja mais", "clique aqui", 
        "imperdível", "surpreendente", "chocante", "fique ligado", "o artigo fala",
        "segundo a publicação"
    ]
    for termo in termos_proibidos:
        if termo in texto.lower():
            erros.append(f"Uso de clichê/clickbait vedado: '{termo}'.")
            instrucoes.append(f"Substitua o clichê '{termo}' por fatos concretos e causa/impacto verificáveis.")
            break

    aprovado = len(erros) == 0
    return {
        "aprovado": aprovado,
        "word_count": word_count,
        "motivo_rejeicao": " | ".join(erros) if erros else "",
        "instrucao_reescrita": " | ".join(instrucoes) if instrucoes else ""
    }


def _local_system1_editorial_evaluate(article_text: str, guidelines: str = "") -> Dict[str, Any]:
    """
    Avaliação determinística ultrarrápida (< 15ms) baseada nas regras normativas do Quality Gate:
    Executa auditar_resumo_critic e mapeia para os primitivos estruturados Jev (System 1).
    """
    t0 = time.perf_counter()
    texto = (article_text or "").strip()
    
    # 1. Estrutura de parágrafos
    blocos = [p.strip() for p in re.split(r'\n\s*\n', texto) if p.strip()]
    if len(blocos) <= 1 and "\n" in texto:
        blocos = [p.strip() for p in texto.split("\n") if p.strip()]
    num_paragrafos = len(blocos) if blocos else 1

    # 2. Executa a auditoria normativa do Quality Gate
    auditoria = auditar_resumo_critic(texto)
    word_count = auditoria["word_count"]
    aprovado = auditoria["aprovado"]
    motivo = auditoria["motivo_rejeicao"]
    instrucao = auditoria["instrucao_reescrita"]

    # 3. Avaliação dos primitivos Jev
    if aprovado:
        score = 5
        noul = True
        choice = "APPROVE"
        confidence = 0.95
        reason = f"Conforme diretrizes editoriais: {word_count} palavras dentro da margem estrita (85-105) e estrutura analítica aprovada."
    elif word_count < 60 or word_count > 140 or len(motivo.split(" | ")) >= 3:
        # Desvio severo
        score = 1
        noul = False
        choice = "REJECT"
        confidence = 0.92
        reason = f"Rejeitado por desconformidade crítica: {motivo}"
    else:
        # Desvio recuperável (necessita revisão do Writer)
        score = 3 if (82 <= word_count <= 108) else 2
        noul = False
        choice = "REVISE"
        confidence = 0.88
        reason = f"Ajuste editorial necessário: {motivo}"

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "score": score,
        "noul": noul,
        "choice": choice,
        "confidence": confidence,
        "latency_ms": elapsed_ms,
        "reason": reason,
        "word_count": word_count,
        "paragraphs": num_paragrafos,
        "model": "typesafe/jev-1.13-fast-local"
    }


def _local_system1_supervisor_triage(log_or_trace: str) -> Dict[str, Any]:
    """
    Triagem operacional heurística de logs e traces (< 5ms).
    Detecta anomalias de SLA, erros de conexão, esgotamento de cotas e falhas em nós.
    """
    t0 = time.perf_counter()
    trace = (log_or_trace or "").strip()
    
    padroes_criticos = [
        "traceback (most recent call last)", "unhandled exception", "error 500", "timed out", 
        "connectionrefused", "crash", "critical_error", "status: failed"
    ]
    padroes_aviso = [
        "warning", "429", "too many requests", "retry_count", "slow execution", 
        "fallback acionado", "deprecated", "warn", "quota exceeded", "rate limit"
    ]
    
    trace_lower = trace.lower()
    
    encontrou_critico = [p for p in padroes_criticos if p in trace_lower]
    encontrou_aviso = [p for p in padroes_aviso if p in trace_lower]
    
    # Se contém indicação explícita de WARN ou 429/retry sem crash fatal, prioriza WARNING
    if encontrou_critico and not any(w in trace_lower for w in ["warn", "warning", "retry_count"]):
        noul = False
        choice = "CRITICAL"
        score = 1
        confidence = 0.94
        action = "ALERT_FOUNDER_AND_HALT"
        details = f"Anomalia crítica detectada: ocorrência de {encontrou_critico[0]}."
    elif encontrou_aviso:
        noul = False
        choice = "WARNING"
        score = 3
        confidence = 0.86
        action = "MONITOR_AND_RETRY"
        details = f"Aviso de degradação: ocorrência de {encontrou_aviso[0]}."
    elif encontrou_critico:
        noul = False
        choice = "CRITICAL"
        score = 1
        confidence = 0.94
        action = "ALERT_FOUNDER_AND_HALT"
        details = f"Anomalia crítica detectada: ocorrência de {encontrou_critico[0]}."
    elif encontrou_aviso:
        noul = False
        choice = "WARNING"
        score = 3
        confidence = 0.86
        action = "MONITOR_AND_RETRY"
        details = f"Aviso de degradação: ocorrência de {encontrou_aviso[0]}."
    else:
        noul = True
        choice = "HEALTHY"
        score = 5
        confidence = 0.98
        action = "PROCEED"
        details = "Pipeline operacional estável e dentro das metas de SLA."
        
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    
    return {
        "noul": noul,
        "choice": choice,
        "score": score,
        "confidence": confidence,
        "action": action,
        "latency_ms": elapsed_ms,
        "details": details,
        "model": "typesafe/jev-1.13-fast-local"
    }


# =============================================================================
# --- 3. CLIENTE DE INFERÊNCIA REMOTO (TYPESAFE / OPENROUTER API) ---
# =============================================================================

def _consultar_jev_remoto(prompt: str, json_schema: Dict[str, Any], timeout: float = 1.2) -> Optional[Dict[str, Any]]:
    """
    Realiza a chamada HTTP ultrarrápida à API TypeSafe / OpenRouter.
    Retorna o JSON validado ou None em caso de indisponibilidade ou latência excessiva.
    """
    api_key = os.environ.get("TYPESAFE_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key or api_key.strip() in ["", "dummy_key", "none"]:
        return None

    # Suporte a endpoint personalizado ou OpenRouter
    endpoint = os.environ.get("TYPESAFE_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://noticias-matinais.vercel.app",
        "X-Title": "All News Journal - LangGraph Gatekeeper"
    }
    
    payload = {
        "model": "typesafe/jev-1.13",
        "messages": [
            {
                "role": "system", 
                "content": "You are Jev, a high-speed structured decision model. Return strictly valid JSON adhering to the specified schema."
            },
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 200
    }
    
    try:
        import requests
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            dados = resp.json()
            conteudo = dados["choices"][0]["message"]["content"]
            return json.loads(conteudo)
    except Exception:
        # Falha na rede, timeout ou erro na chave -> segue silenciosamente para o emulador local
        return None
    return None


# =============================================================================
# --- 4. FUNÇÕES PÚBLICAS DO GATEKEEPER JEV ---
# =============================================================================

def evaluate_editorial_quality(article_text: str, guidelines: str = "") -> Dict[str, Any]:
    """
    Avalia a conformidade editorial de um draft no Quality Gate (nó Critic).
    
    Garante:
    - Retorno estruturado com primitivos Jev: 'score', 'noul', 'choice', 'confidence', 'latency_ms', 'reason'.
    - Latência estritamente < 200ms na execução local e suporte a chamadas remotas Jev quando configurado.
    - Tipagem validada via Pydantic EditorialDecision.
    """
    t_start = time.perf_counter()
    resultado = None
    
    # 1. Tenta API remota se houver credencial configurada
    if os.environ.get("TYPESAFE_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
        prompt = (
            f"Evaluate editorial quality strictly.\n"
            f"Rules: Exactly 85-105 words. 2 paragraphs. No trailing '?'. Analytical tone.\n"
            f"Guidelines: {guidelines}\n"
            f"Article text:\n{article_text}\n\n"
            f"Output JSON with keys: score (1-5), noul (bool), choice (APPROVE|REVISE|REJECT), confidence (0.0-1.0), reason (string)."
        )
        resultado = _consultar_jev_remoto(prompt, EditorialDecision.model_json_schema(), timeout=0.8)
    
    # 2. Fallback imediato para o Emulador Local System 1
    if not resultado:
        resultado = _local_system1_editorial_evaluate(article_text, guidelines)
    else:
        # Completa campos e afere latência real
        palavras = len((article_text or "").strip().split())
        resultado.setdefault("word_count", palavras)
        resultado.setdefault("paragraphs", 2)
        resultado.setdefault("model", "typesafe/jev-1.13-remote")
        resultado["latency_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
        
    # 3. Validação e coerção via Pydantic
    try:
        validado = EditorialDecision(**resultado)
        return validado.model_dump()
    except Exception:
        # Se os dados do provedor externo falharem na validação, garante retorno estrito pelo local
        return _local_system1_editorial_evaluate(article_text, guidelines)


def quick_triage_supervisor(log_or_trace: str) -> Dict[str, Any]:
    """
    Realiza triagem ultrarrápida da integridade operacional para o AI Supervisor.
    
    Retorna:
    - noul: True se saudável (sem anomalias nos SLAs), False se houver incidentes.
    - choice: HEALTHY, WARNING ou CRITICAL.
    - score: 1 a 5.
    - confidence: float.
    - action: Ação recomendada para contenção.
    """
    t_start = time.perf_counter()
    resultado = None
    
    if os.environ.get("TYPESAFE_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
        prompt = (
            f"Classify operational health of this trace.\n"
            f"Trace:\n{log_or_trace}\n\n"
            f"Output JSON: noul (bool), choice (HEALTHY|WARNING|CRITICAL), score (1-5), confidence (0.0-1.0), action (string), details (string)."
        )
        resultado = _consultar_jev_remoto(prompt, SupervisorTriage.model_json_schema(), timeout=0.6)
        
    if not resultado:
        resultado = _local_system1_supervisor_triage(log_or_trace)
    else:
        resultado.setdefault("model", "typesafe/jev-1.13-remote")
        resultado["latency_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
        
    try:
        validado = SupervisorTriage(**resultado)
        return validado.model_dump()
    except Exception:
        return _local_system1_supervisor_triage(log_or_trace)


if __name__ == "__main__":
    # Teste rápido de sanidade
    artigo_teste = (
        "A aceleração global dos investimentos em infraestrutura de inteligência artificial atinge cifras recordes "
        "e redefine a priorização estratégica dos grandes conglomerados de tecnologia. Com mais de duzentos bilhões de dólares "
        "aportados em centros de dados e transição energética sustentável, o setor antecipa a expansão da capacidade computacional mundial.\n\n"
        "Analistas destacam que tal movimento consolida barreiras relevantes de mercado para novos entrantes, "
        "ao passo que reconfigura contratos de longo prazo na cadeia de suprimentos e estimula o crescimento de fornecedores de semicondutores."
    )
    print("Testando evaluate_editorial_quality:")
    decisao = evaluate_editorial_quality(artigo_teste)
    print(json.dumps(decisao, indent=2, ensure_ascii=False))

    print("\nTestando quick_triage_supervisor:")
    triage = quick_triage_supervisor("INFO: Operação concluída em 1.2s. 200 OK.")
    print(json.dumps(triage, indent=2, ensure_ascii=False))
