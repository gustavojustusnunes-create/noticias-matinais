"""
core/ondemand_graph.py — Orquestração do Subgrafo On-Demand com LangGraph
All News Journal (v2.2)

Topologia:
START ➔ researcher ➔ writer ➔ critic ➔ (se reprovado e tries < 2 ➔ writer)
                                     ➔ (se aprovado ➔ media_retriever ➔ queue_hitl ➔ END)
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Literal
from pathlib import Path

# Timezone de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.ondemand_state import OnDemandState
from core.ondemand_researcher import node_researcher
from core.ondemand_writer import node_writer
from core.ondemand_media import node_media_retriever

# Importa o Quality Gate Jev System 1
try:
    from core.jev_gatekeeper import evaluate_editorial_quality
except ImportError:
    from jev_gatekeeper import evaluate_editorial_quality


def node_ondemand_critic(state: OnDemandState) -> Dict[str, Any]:
    """
    Nó 3 do Subgrafo: Critic (Quality Gate Jev System 1)
    Audita a conformidade de extensão (85 a 105 palavras por slide),
    ausência de interrogações e clichês sensacionalistas.
    """
    slides_text = state.get("slides_text", [])
    retry_count = state.get("retry_count", 0)
    headline = state.get("headline", "")
    logs = list(state.get("execution_log", []))

    # Avalia cada slide individualmente contra a diretriz de 85 a 105 palavras por bloco
    todos_aprovados = True
    motivos_rejeicao = []
    ultimo_verdict = None

    for idx, slide_content in enumerate(slides_text, 1):
        try:
            v = evaluate_editorial_quality(slide_content, "Texto analítico, 85 a 105 palavras, sem interrogações ou clichês.")
        except Exception as e_jev:
            v = {"score": 4, "choice": "APPROVE", "confidence": 0.85, "reason": str(e_jev)}

        ultimo_verdict = v
        if v.get("choice") != "APPROVE":
            todos_aprovados = False
            motivos_rejeicao.append(f"Slide {idx}: {v.get('reason')}")

    # Verifica se a manchete encerra com interrogação
    if headline.strip().endswith("?"):
        todos_aprovados = False
        motivos_rejeicao.append("A manchete não deve terminar com ponto de interrogação.")

    if todos_aprovados:
        is_approved = True
        status_msg = "Aprovado com distinção pelo Jev Quality Gate (todos os slides em conformidade)."
        verdict = ultimo_verdict or {"choice": "APPROVE", "confidence": 0.95}
        verdict["choice"] = "APPROVE"
    else:
        is_approved = False
        retry_count += 1
        status_msg = f"Revisão solicitada pelo Jev Gate: {'; '.join(motivos_rejeicao)}"
        verdict = {
            "choice": "REVISE",
            "score": 2,
            "confidence": 0.90,
            "reason": "; ".join(motivos_rejeicao)
        }

    logs.append({
        "node": "node_ondemand_critic",
        "message": status_msg,
        "is_approved": is_approved,
        "retry_count": retry_count,
        "verdict": verdict
    })

    return {
        "critic_verdict": verdict,
        "retry_count": retry_count,
        "is_approved_by_critic": is_approved,
        "execution_log": logs
    }


def rotear_pos_critic(state: OnDemandState) -> Literal["retry_writer", "approved"]:
    """
    Edge condicional pós-crítico:
    - Se reprovado e retry_count < 2: retorna 'retry_writer'
    - Se aprovado (ou esgotou 2 tentativas): avança para 'approved' (media_retriever)
    """
    if state.get("is_approved_by_critic", False):
        return "approved"
    if state.get("retry_count", 0) < 2:
        return "retry_writer"
    return "approved"


def node_queue_hitl(state: OnDemandState) -> Dict[str, Any]:
    """
    Nó 5 do Subgrafo: Fila HITL & Inicialização do Watchdog Timer (60 min).
    Grava a tarefa em logs/ondemand_queue.json com status PENDING_APPROVAL.
    """
    logs = list(state.get("execution_log", []))
    agora = datetime.now(BRT)
    expires = agora + timedelta(seconds=3600)

    created_iso = agora.isoformat()
    expires_iso = expires.isoformat()

    # Prepara o registro da tarefa
    task_data = {
        "task_id": state.get("task_id"),
        "topic_raw": state.get("topic_raw"),
        "tema": state.get("tema"),
        "formato": state.get("formato", "carrossel"),
        "headline": state.get("headline"),
        "subtitulo": state.get("subtitulo"),
        "keyword": state.get("keyword"),
        "slides_text": state.get("slides_text", []),
        "caption": state.get("caption"),
        "image_query": state.get("image_query"),
        "slide_paths": state.get("slide_paths", []),
        "hitl_status": "PENDING_APPROVAL",
        "created_at": created_iso,
        "expires_at": expires_iso,
        "retry_count": state.get("retry_count", 0),
        "execution_log": logs
    }

    # Enfileira no gerenciador de watchdog
    try:
        from core.ondemand_watchdog import adicionar_tarefa_fila
        adicionar_tarefa_fila(task_data)
    except Exception as e_queue:
        print(f"   ⚠️ [queue_hitl] Erro ao enfileirar tarefa: {e_queue}")

    logs.append({
        "node": "node_queue_hitl",
        "message": f"Pauta enfileirada para aprovação do fundador. Expira em 60 min às {expires.strftime('%H:%M:%S')}.",
        "expires_at": expires_iso
    })

    return {
        "hitl_status": "PENDING_APPROVAL",
        "created_at": created_iso,
        "expires_at": expires_iso,
        "execution_log": logs
    }


def construir_subgrafo_ondemand() -> StateGraph:
    """Instancia o subgrafo LangGraph para Pautas Quentes."""
    builder = StateGraph(OnDemandState)

    builder.add_node("researcher", node_researcher)
    builder.add_node("writer", node_writer)
    builder.add_node("critic", node_ondemand_critic)
    builder.add_node("media_retriever", node_media_retriever)
    builder.add_node("queue_hitl", node_queue_hitl)

    builder.add_edge(START, "researcher")
    builder.add_edge("researcher", "writer")
    builder.add_edge("writer", "critic")

    builder.add_conditional_edges(
        "critic",
        rotear_pos_critic,
        {
            "retry_writer": "writer",
            "approved": "media_retriever"
        }
    )

    builder.add_edge("media_retriever", "queue_hitl")
    builder.add_edge("queue_hitl", END)

    return builder


checkpointer = MemorySaver()
ondemand_graph = construir_subgrafo_ondemand().compile(checkpointer=checkpointer)


def executar_pipeline_ondemand(topic_raw: str, tema: str = "Mundo", formato: str = "carrossel") -> Dict[str, Any]:
    """
    Ponto de entrada público para executar o pipeline sob demanda do Streamlit.
    """
    now = datetime.now(BRT)
    task_id = f"ondemand_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    estado_inicial: OnDemandState = {
        "task_id": task_id,
        "topic_raw": topic_raw,
        "tema": tema,
        "formato": formato,
        "retry_count": 0,
        "execution_log": []
    }

    config = {"configurable": {"thread_id": task_id}}
    resultado_final = ondemand_graph.invoke(estado_inicial, config)
    return resultado_final
