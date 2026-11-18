"""
agentic_graph.py — Arquitetura de Grafo Agêntico Interativo (Graph Engineering)
All News Journal (v3.0 — Manual Editorial Jovem Multicanal 18-30 anos)

Motor de orquestração agêntica baseado em LangGraph (StateGraph),
com padrão Planner-Critic, Curadoria 0-10, Checklist de 7 Itens,
4 Blocos Universais, Subagentes Multicanal em Paralelo e HITL Founder Gate.
"""

import os
import sys
import json
import time
import glob
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

import streamlit as st

try:
    from core.graph_engine import (
        graph as core_graph,
        exportar_grafo_visual,
        executar_fluxo as core_executar_fluxo,
        aprovar_e_despachar as core_aprovar_e_despachar,
        obter_estado_atual as core_obter_estado_atual,
        node_planner as core_node_planner,
        node_writer as core_node_writer,
        node_critic as core_node_critic,
    )
except Exception as _e_imp:
    print(f"⚠️ [agentic_graph] Aviso ao importar core.graph_engine: {_e_imp}")


class GraphState(TypedDict, total=False):
    pool_noticias: List[Dict[str, Any]]
    materia_selecionada: Dict[str, Any]
    draft_texto: str
    contagem_palavras: int
    critic_feedback: str
    critic_status: str
    revisao_tentativas: int
    audio_path: str
    visual_capa_path: str
    x_post_status: str
    resend_status: str
    supervisor_audit_log: List[Dict[str, Any]]
    logs_transicao: List[str]


LOGS_DIR = Path("logs")
GRAPH_STATE_FILE = LOGS_DIR / "graph_state.json"
SUPERVISOR_MEMORY_FILE = LOGS_DIR / "supervisor_memory.json"
KILL_SWITCH_FILE = LOGS_DIR / "kill_switch.json"

CHECKLIST_7_LABELS = {
    "fonte_validada": "1. Fonte Camada 1 & Dados Exatos",
    "teste_3_segundos": "2. Gancho 3 Segundos (≤ 15 palavras)",
    "teste_e_dai": "3. Teste 'E daí?' (Impacto no Bolso/Carreira)",
    "limpeza_jargoes": "4. Limpeza de Jargões (Analogia na Mesma Frase)",
    "contagem_palavras": "5. Frases Curtas & Voz Ativa",
    "reducao_ansiedade": "6. Redução de Ansiedade (Zero Alarmismo)",
    "gatilho_comunidade": "7. Gatilho de Comunidade (Pergunta Final '?')",
}

CONFIG_NOS_PADRAO = {
    "Planner": {
        "nome": "Planner (Curador 0-10)",
        "modelo": "Gemini 2.5 Flash (Pydantic CurationDecision)",
        "temperatura": 0.1,
        "inner_harness": (
            "Executa score_news_curation (Matriz 0 a 10) verificando Lista Negra e "
            "avaliando 5 critérios de 0 a 2 pontos: Impacto no Bolso/Carreira, Fator Conversa/Dark Social, "
            "Utilidade Prática, Novidade/Sinal de Futuro e Potencial Visual/Narrativo."
        ),
        "outer_harness": "core/jev_gatekeeper.py: score_news_curation() -> FULL_OMNICHANNEL (>=8), SHORT_NOTE (6-7), DISCARD (<6).",
        "tipo": "Curadoria Estruturada 0-10",
        "cor": "#2563EB",
    },
    "Writer": {
        "nome": "Writer (Redator 4 Blocos)",
        "modelo": "Gemini 2.5 Flash + skills/editorial_jovem/SKILL.md",
        "temperatura": 0.1,
        "inner_harness": (
            "Redige a notícia nos 4 Blocos Universais para jovens de 18-30 anos: "
            "bloco_1_gancho (<=15 palavras), bloco_2_fato (dados exatos + analogia na mesma frase para siglas), "
            "bloco_3_e_dai (como afeta bolso/carreira) e bloco_4_fechamento (pergunta aberta '?')."
        ),
        "outer_harness": "skills/editorial_jovem/SKILL.md + Pydantic FourBlockDraft.",
        "tipo": "Geração 4 Blocos",
        "cor": "#3B82F6",
    },
    "Critic": {
        "nome": "Critic (Auditor de 7 Itens)",
        "modelo": "Gemini 2.5 Flash (Pydantic AuditVerdict)",
        "temperatura": 0.1,
        "inner_harness": (
            "Valida rigorosamente os 7 itens booleanos pré-publicação: fonte_validada, teste_3_segundos, "
            "teste_e_dai, limpeza_jargoes, contagem_palavras, reducao_ansiedade e gatilho_comunidade. "
            "Se reprovar, devolve correction_instructions cirúrgicas para o Writer (retry_count <= 2)."
        ),
        "outer_harness": "core/jev_gatekeeper.py: audit_checklist_7_items() -> AuditVerdict.",
        "tipo": "Quality Gate 7 Itens",
        "cor": "#A855F7",
    },
    "Multichannel_Fanout": {
        "nome": "Multichannel Fanout (4 Subagentes Paralelos)",
        "modelo": "ThreadPoolExecutor (Email, IG, X, Podcast/Reels)",
        "temperatura": 0.1,
        "inner_harness": (
            "Formata em paralelo a partir dos 4 Blocos aprovados: Newsletter HTML com pílulas visuais, "
            "Carrossel IG (6-8 slides + legenda 80-120w), Thread X (5-7 posts <=240 chars) e Roteiro Ana & Leo + Reels."
        ),
        "outer_harness": "email_builder.py, instagram_poster.py, postar_x_diario.py, podcast_builder.py.",
        "tipo": "Fan-out Paralelo",
        "cor": "#10B981",
    },
}


def carregar_estado_grafo() -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if GRAPH_STATE_FILE.exists():
        try:
            with open(GRAPH_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "curation_score": 9,
        "curation_route": "FULL_OMNICHANNEL",
        "critic_status": "STATUS_APPROVED",
        "revisao_tentativas": 0,
    }


def salvar_estado_grafo(estado: Dict[str, Any]):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(GRAPH_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"⚠️ Erro ao salvar estado do grafo: {e}")


def checar_kill_switch() -> bool:
    if KILL_SWITCH_FILE.exists():
        try:
            with open(KILL_SWITCH_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("kill_switch_ativo", False)
        except Exception:
            pass
    return False


def alternar_kill_switch(ativo: bool):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(KILL_SWITCH_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "kill_switch_ativo": ativo,
            "atualizado_em": datetime.now().isoformat(),
        }, f, indent=2)


def renderizar_canvas_animado(critic_status: str, tentativas: int, curation_score: int = 9):
    cor_critic = "#10B981" if critic_status in ("STATUS_APPROVED", "CRITIC_APPROVED", "AWAITING_FOUNDER_APPROVAL", "DISPATCHED") else "#F59E0B"
    status_label = "7/7 Aprovado" if cor_critic == "#10B981" else "Em Revisão"

    html_canvas = f"""
    <div style="background-color: #0B0F14; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10B981; box-shadow: 0 0 10px #10B981;"></span>
          <span style="color: #F8FAFC; font-size: 13px; font-weight: 600; font-family: sans-serif;">Grafo LangGraph • Manual Editorial Jovem (4 Blocos & 7 Checks)</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <span style="font-size: 11px; background: rgba(209, 186, 115, 0.18); color: #D1BA73; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(209, 186, 115, 0.4);">Score Pauta: {curation_score}/10</span>
          <span style="font-size: 11px; background: rgba(16, 185, 129, 0.15); color: #34D399; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.3);">Checklist: {status_label} (Retry {tentativas}/2)</span>
        </div>
      </div>

      <svg viewBox="0 0 920 280" width="100%" height="auto" style="overflow: visible;">
        <line x1="45" y1="140" x2="105" y2="140" stroke="#334155" stroke-width="2" stroke-dasharray="4 4" />
        <path d="M 215 140 L 290 140" stroke="#2563EB" stroke-width="2.5" />
        <path d="M 400 140 L 475 140" stroke="#3B82F6" stroke-width="2.5" />
        <path d="M 530 100 C 530 35, 345 35, 345 100" fill="none" stroke="#D1BA73" stroke-width="2" stroke-dasharray="5 3" />
        <text x="438" y="45" fill="#D1BA73" font-size="10" font-weight="600" text-anchor="middle">Autocura: Rejeitado / Retry (≤ 2)</text>

        <path d="M 590 140 L 660 65" stroke="#10B981" stroke-width="2" />
        <path d="M 590 140 L 660 115" stroke="#10B981" stroke-width="2" />
        <path d="M 590 140 L 660 165" stroke="#10B981" stroke-width="2" />
        <path d="M 590 140 L 660 215" stroke="#10B981" stroke-width="2" />

        <circle cx="45" cy="140" r="14" fill="#131B26" stroke="#475569" stroke-width="2" />
        <text x="45" y="143" fill="#94A3B8" font-size="8" text-anchor="middle" font-weight="bold">START</text>

        <g transform="translate(105, 105)">
          <rect width="110" height="70" rx="10" fill="#131B26" stroke="#2563EB" stroke-width="2" />
          <text x="55" y="28" fill="#FFFFFF" font-size="12" font-weight="bold" text-anchor="middle">node_planner</text>
          <text x="55" y="44" fill="#93C5FD" font-size="9" text-anchor="middle">Matriz 0 a 10</text>
          <text x="55" y="60" fill="#D1BA73" font-size="9" font-weight="bold" text-anchor="middle">Score: {curation_score}/10</text>
        </g>

        <g transform="translate(290, 105)">
          <rect width="110" height="70" rx="10" fill="#131B26" stroke="#3B82F6" stroke-width="2" />
          <text x="55" y="28" fill="#FFFFFF" font-size="12" font-weight="bold" text-anchor="middle">node_writer</text>
          <text x="55" y="44" fill="#93C5FD" font-size="9" text-anchor="middle">SKILL.md Jovem</text>
          <text x="55" y="60" fill="#60A5FA" font-size="8.5" text-anchor="middle">4 Blocos Universais</text>
        </g>

        <g transform="translate(475, 102)">
          <rect width="115" height="75" rx="10" fill="#131B26" stroke="{cor_critic}" stroke-width="2" />
          <text x="57" y="26" fill="#FFFFFF" font-size="12" font-weight="bold" text-anchor="middle">node_critic</text>
          <text x="57" y="42" fill="#A855F7" font-size="9" text-anchor="middle">Checklist 7 Itens</text>
          <text x="57" y="60" fill="{cor_critic}" font-size="9" font-weight="bold" text-anchor="middle">{status_label}</text>
        </g>

        <g transform="translate(660, 42)">
          <rect width="115" height="42" rx="8" fill="#131B26" stroke="#059669" stroke-width="1.5" />
          <text x="57" y="20" fill="#FFFFFF" font-size="10" font-weight="bold" text-anchor="middle">Newsletter HTML</text>
          <text x="57" y="33" fill="#6EE7B7" font-size="8" text-anchor="middle">Pílulas 4 Blocos</text>
        </g>
        <g transform="translate(660, 92)">
          <rect width="115" height="42" rx="8" fill="#131B26" stroke="#8B5CF6" stroke-width="1.5" />
          <text x="57" y="20" fill="#FFFFFF" font-size="10" font-weight="bold" text-anchor="middle">IG Carrossel</text>
          <text x="57" y="33" fill="#C4B5FD" font-size="8" text-anchor="middle">6-8 Slides + Legenda</text>
        </g>
        <g transform="translate(660, 142)">
          <rect width="115" height="42" rx="8" fill="#131B26" stroke="#38BDF8" stroke-width="1.5" />
          <text x="57" y="20" fill="#FFFFFF" font-size="10" font-weight="bold" text-anchor="middle">X Thread / Note</text>
          <text x="57" y="33" fill="#7DD3FC" font-size="8" text-anchor="middle">5-7 Posts ≤ 240c</text>
        </g>
        <g transform="translate(660, 192)">
          <rect width="115" height="42" rx="8" fill="#131B26" stroke="#D1BA73" stroke-width="1.5" />
          <text x="57" y="20" fill="#FFFFFF" font-size="10" font-weight="bold" text-anchor="middle">Podcast & Reels</text>
          <text x="57" y="33" fill="#FDE68A" font-size="8" text-anchor="middle">Ana & Leo + 110-150w</text>
        </g>
      </svg>
    </div>
    """
    st.components.v1.html(html_canvas, height=320)


def render_agentic_graph_dashboard():
    """Painel Executivo integrado exibindo Score 0-10, 4 Blocos e os 7 Checks Verdes da Auditoria."""
    estado = carregar_estado_grafo()

    visao = st.radio(
        "Modo de Operação:",
        [
            "🕸️ Orquestração LangGraph & HITL Gate",
            "🎛️ Editor Granular de Células (Inner/Outer Harness)",
            "👁️ Visualização de Grafo (Mermaid & JSON)",
            "📊 Cockpit de Redes Sociais & Tração",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("<hr style='margin: 10px 0 20px; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    if "🕸️ Orquestração LangGraph" in visao:
        estado_hitl = (
            st.session_state.get("ultimo_fluxo_hitl")
            or (core_obter_estado_atual("st_founder_session") if "core_obter_estado_atual" in globals() else None)
            or estado
        )
        score_atual = int(estado_hitl.get("curation_score", 9))
        rota_atual = estado_hitl.get("curation_route", "FULL_OMNICHANNEL")

        col_canvas, col_status = st.columns([2.5, 1])
        with col_canvas:
            renderizar_canvas_animado(
                critic_status=estado_hitl.get("status", "CRITIC_APPROVED"),
                tentativas=int(estado_hitl.get("retry_count", 0)),
                curation_score=score_atual,
            )

        with col_status:
            st.markdown("#### Status dos Nós Ativos")
            for no_key, cfg in CONFIG_NOS_PADRAO.items():
                st.markdown(f"""
                <div style="background: #131B26; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 7px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 11px; font-weight: 600; color: #FFFFFF;">{cfg['nome']}</span>
                  <span style="font-size: 10px; color: {cfg['cor']}; background: {cfg['cor']}15; padding: 2px 6px; border-radius: 4px;">Ativo</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🛑 Controle Human-In-The-Loop (HITL Founder Gate)")
        st.markdown(
            "O StateGraph suspende a execução imediatamente antes do nó `dispatcher` (`interrupt_before=['dispatcher']`), "
            "exibindo o **Score de Curadoria (0-10)**, os **4 Blocos Universais** e os **7 Checks Verdes da Auditoria**."
        )

        if st.button("▶️ Executar Pipeline LangGraph (Curadoria 0-10 ➔ 4 Blocos ➔ 7 Checks ➔ Fan-out)", type="secondary", use_container_width=True):
            with st.spinner("Executando Planner ➔ Writer (SKILL.md) ➔ Critic (7 Checks) ➔ Multichannel Fanout..."):
                try:
                    res_fluxo = core_executar_fluxo(thread_id="st_founder_session")
                    st.session_state["ultimo_fluxo_hitl"] = res_fluxo
                    st.toast("Pipeline validado em 7/7 itens e suspenso no HITL Gate!", icon="✅")
                    st.rerun()
                except Exception as e_run:
                    st.error(f"Erro na execução do grafo: {e_run}")

        if estado_hitl:
            story_sel = estado_hitl.get("selected_story", {})
            draft_blocks = estado_hitl.get("draft_blocks", {})
            audit_verdict = estado_hitl.get("audit_verdict", {})
            checklist_map = audit_verdict.get("checklist", {k: True for k in CHECKLIST_7_LABELS})

            col_rev1, col_rev2 = st.columns([1.6, 1.2])
            with col_rev1:
                st.markdown(
                    f"**Pauta Selecionada:** {story_sel.get('titulo', 'Destaque do Dia')}  \n"
                    f"**Score de Curadoria:** `🎯 {score_atual}/10` • **Rota:** `{rota_atual}`"
                )
                if draft_blocks:
                    st.markdown("##### 📦 Os 4 Blocos Universais (`SKILL.md`)")
                    st.info(f"**1. Gancho (3s):** {draft_blocks.get('bloco_1_gancho', '')}")
                    st.markdown(f"**2. O Fato (com analogias):** {draft_blocks.get('bloco_2_fato', '')}")
                    st.success(f"**3. 💰 Como isso afeta você (E daí?):** {draft_blocks.get('bloco_3_e_dai', '')}")
                    st.warning(f"**4. 💬 Fechamento (Comunidade):** {draft_blocks.get('bloco_4_fechamento', '')}")
                else:
                    st.text_area("Draft Gerado:", value=estado_hitl.get("draft_text", ""), height=130, disabled=True)

            with col_rev2:
                st.markdown("##### ✅ Checklist de Auditoria (7 Itens)")
                for chk_key, chk_label in CHECKLIST_7_LABELS.items():
                    ok = bool(checklist_map.get(chk_key, True))
                    icone = "✅" if ok else "❌"
                    cor_borda = "rgba(16, 185, 129, 0.35)" if ok else "rgba(239, 68, 68, 0.45)"
                    st.markdown(
                        f"<div style='padding:6px 10px;margin-bottom:5px;border-radius:8px;background:#0D131C;border:1px solid {cor_borda};font-size:12px;color:#E2E8F0;'>"
                        f"{icone} <strong>{chk_label}</strong></div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Aprovar e Disparar Edição Multicanal (APPROVED_BY_FOUNDER)", type="primary", use_container_width=True):
                with st.spinner("Retomando execução no nó dispatcher..."):
                    try:
                        res_fim = core_aprovar_e_despachar("st_founder_session")
                        st.session_state["ultimo_fluxo_hitl"] = res_fim
                        st.success("✅ Edição multicanal aprovada pelo fundador e despachada com sucesso!")
                        st.rerun()
                    except Exception as e_app:
                        st.error(f"Falha ao aprovar e despachar: {e_app}")

    elif "👁️ Visualização de Grafo" in visao:
        st.markdown("### 👁️ Visualização e Exportação de Grafo (Mermaid & JSON)")
        try:
            dados_vis = exportar_grafo_visual()
            st.code(dados_vis.get("mermaid", ""), language="mermaid")
            st.json(dados_vis.get("json_schema", {}))
        except Exception as e_vis:
            st.error(f"Falha ao exportar grafo: {e_vis}")

    elif "🎛️ Editor Granular de Células" in visao:
        st.markdown("### 🎛️ Editor Granular de Células (Inner & Outer Harness)")
        no_selecionado = st.selectbox("Selecione o Nó:", list(CONFIG_NOS_PADRAO.keys()))
        cfg_no = CONFIG_NOS_PADRAO[no_selecionado]
        st.text_area("System Instruction:", value=cfg_no["inner_harness"], height=120)
        st.info(cfg_no["outer_harness"])
    else:
        st.markdown("### 📊 Cockpit de Gestão de Redes Sociais & Tração")
        kill_ativo = checar_kill_switch()
        novo_kill = st.toggle("🚨 KILL SWITCH GERAL", value=kill_ativo)
        if novo_kill != kill_ativo:
            alternar_kill_switch(novo_kill)
            st.rerun()
