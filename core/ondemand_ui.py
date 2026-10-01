"""
core/ondemand_ui.py — Interface HITL e Dispatcher de Pautas On-Demand
All News Journal (v2.2)

Renderiza o painel "⚡ Pauta Express / On-Demand":
1. Formulário de inserção da pauta bruta, caderno e formato visual.
2. Acionador do pipeline LangGraph assíncrono.
3. Fila de moderação HITL com countdown de 60 minutos para auto-publicação.
4. Preview visual dos slides (1080x1350) e legenda completa para o Instagram.
5. Botões de aprovação manual imediata e rejeição.
6. Histórico auditável de pautas processadas.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import streamlit as st

BRT = timezone(timedelta(hours=-3))

from core.ondemand_watchdog import (
    iniciar_watchdog_daemon,
    obter_fila,
    aprovar_tarefa,
    rejeitar_tarefa,
    verificar_timeouts
)
from core.ondemand_graph import executar_pipeline_ondemand


def render_ondemand_tab() -> None:
    """Função principal que renderiza a aba On-Demand no Streamlit."""
    # Garante que o watchdog em segundo plano esteja ativo
    iniciar_watchdog_daemon(intervalo_segundos=30)

    # ── CABEÇALHO EDITORIAL ──
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0B0F14 0%, #161F2E 100%); border: 1px solid #1E293B; border-radius: 12px; padding: 22px 26px; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.35);">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                    <span style="font-family: 'Newsreader', serif; font-size: 1.6rem; font-weight: 700; color: #FFFFFF; letter-spacing: 0.02em;">⚡ PAUTA EXPRESS & BREAKING NEWS</span>
                    <span style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #FBBF24; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.06em;">On-Demand LangGraph</span>
                </div>
                <p style="margin: 0; color: #94A3B8; font-size: 0.90rem;">
                    Pesquisa autônoma em tempo real, redação analítica sob rigor editorial (85-105 palavras), Jev Quality Gate e geração de arte 1080x1350 com aprovação em 1 clique ou publicação autônoma em 60 min.
                </p>
            </div>
            <div>
                <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #38BDF8; background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.25); padding: 6px 14px; border-radius: 8px; font-weight: 600;">
                    🛡️ Watchdog Autônomo Ativo (60 min timeout)
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── FORMULÁRIO DE DISPARO DA PAUTA ──
    with st.container():
        st.markdown("<h3 style='color: #F8FAFC; font-size: 1.15rem; margin-bottom: 12px;'>📝 Inserir Nova Pauta Quente</h3>", unsafe_allow_html=True)
        
        col_topic, col_opts = st.columns([3, 2])
        
        with col_topic:
            topic_raw = st.text_area(
                "Pauta Bruta / Fato / Notícia",
                placeholder="Ex: Banco Central Europeu corta juros após queda histórica da inflação ou Nova IA da Anthropic atinge marca inédita em matemática...",
                height=110,
                help="Descreva o acontecimento em poucas frases ou insira uma manchete bruta. O agente Researcher buscará fontes complementares."
            )

        with col_opts:
            tema_selecionado = st.selectbox(
                "Caderno / Tema Editorial",
                options=["IA", "Economia", "Mundo", "Politica", "Wellness", "Ciencia", "Cinema", "Fofoca"],
                index=0
            )

            formato_selecionado = st.selectbox(
                "Formato Visual do Post",
                options=[
                    "Carrossel Editorial (3 slides 1080x1350)",
                    "Card Único de Destaque (1 slide 1080x1350)"
                ],
                index=0
            )
            formato_key = "unico" if "Único" in formato_selecionado else "carrossel"

        btn_disparar = st.button("🚀 Processar Pauta com LangGraph", type="primary", use_container_width=True)

        if btn_disparar:
            if not topic_raw or len(topic_raw.strip()) < 5:
                st.warning("⚠️ Por favor, insira uma descrição ou manchete com ao menos 5 caracteres.")
            else:
                with st.spinner("🤖 Executando pipeline: pesquisando fontes, redigindo, auditando no Jev Gate e renderizando slides..."):
                    try:
                        resultado = executar_pipeline_ondemand(
                            topic_raw=topic_raw.strip(),
                            tema=tema_selecionado,
                            formato=formato_key
                        )
                        st.success("✅ Pauta processada com sucesso e enviada para a fila de moderação HITL!")
                        st.rerun()
                    except Exception as e_proc:
                        st.error(f"❌ Erro ao executar pipeline on-demand: {e_proc}")

    st.markdown("---")

    # ── FILA HITL (MODERAÇÃO E AUTO-DISPATCH) ──
    fila = obter_fila()
    pendentes = [t for t in fila if t.get("hitl_status") == "PENDING_APPROVAL"]
    historico = [t for t in fila if t.get("hitl_status") != "PENDING_APPROVAL"]

    st.markdown(f"<h3 style='color: #F8FAFC; font-size: 1.2rem; display: flex; align-items: center; gap: 8px;'>⏳ Fila de Moderação HITL ({len(pendentes)} pendente{'s' if len(pendentes) != 1 else ''})</h3>", unsafe_allow_html=True)

    if not pendentes:
        st.info("ℹ️ Nenhuma pauta pendente de aprovação no momento. Dispare uma nova pauta acima para iniciar o fluxo.")
    else:
        agora = datetime.now(BRT)
        for tarefa in pendentes:
            task_id = tarefa.get("task_id", "")
            tema = tarefa.get("tema", "Geral")
            headline = tarefa.get("headline", "Sem título")
            subtitulo = tarefa.get("subtitulo", "")
            caption = tarefa.get("caption", "")
            slide_paths = tarefa.get("slide_paths", [])
            expires_at_str = tarefa.get("expires_at", "")
            created_at_str = tarefa.get("created_at", "")

            # Cálculo do tempo restante
            try:
                exp_dt = datetime.fromisoformat(expires_at_str)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=BRT)
                tempo_restante_seg = int((exp_dt - agora).total_seconds())
            except Exception:
                tempo_restante_seg = 3600

            minutos_restantes = max(0, tempo_restante_seg // 60)
            segundos_restantes = max(0, tempo_restante_seg % 60)

            cor_timer = "#EF4444" if minutos_restantes < 15 else "#F59E0B" if minutos_restantes < 35 else "#10B981"

            with st.container():
                st.markdown(f"""
                <div style="background: #111827; border: 1px solid #1F2937; border-left: 5px solid {cor_timer}; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="background: #374151; color: #F3F4F6; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">{tema}</span>
                            <span style="color: #9CA3AF; font-size: 12px; font-family: monospace;">ID: {task_id}</span>
                        </div>
                        <div>
                            <span style="background: rgba(245,158,11,0.15); color: {cor_timer}; border: 1px solid rgba(245,158,11,0.3); font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 6px;">
                                ⏱️ Auto-publicação em: {minutos_restantes:02d}m {segundos_restantes:02d}s
                            </span>
                        </div>
                    </div>
                    <h4 style="margin: 0 0 6px 0; color: #FFFFFF; font-family: 'Newsreader', serif; font-size: 1.35rem;">{headline}</h4>
                    <p style="margin: 0 0 14px 0; color: #94A3B8; font-size: 0.92rem; font-style: italic;">{subtitulo}</p>
                </div>
                """, unsafe_allow_html=True)

                col_preview, col_detalhes = st.columns([1, 1])

                with col_preview:
                    st.markdown("**🖼️ Preview dos Slides Renderizados (1080x1350):**")
                    if slide_paths:
                        existentes = [p for p in slide_paths if os.path.exists(p)]
                        if existentes:
                            tab_slides = st.tabs([f"Slide {i+1}" for i in range(len(existentes))])
                            for idx_s, s_path in enumerate(existentes):
                                with tab_slides[idx_s]:
                                    st.image(s_path, caption=f"Slide {idx_s+1} de {len(existentes)}", use_container_width=True)
                        else:
                            st.warning("Arquivos de slide não encontrados no disco.")
                    else:
                        st.info("Nenhum slide gerado.")

                with col_detalhes:
                    st.markdown("**📱 Legenda Proposta para o Instagram:**")
                    st.text_area(
                        label="Legenda",
                        value=caption,
                        height=240,
                        key=f"cap_{task_id}",
                        disabled=True
                    )

                    # Botões de Ação HITL
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    btn_col_aprov, btn_col_rej = st.columns(2)

                    with btn_col_aprov:
                        if st.button("✅ Aprovar & Publicar Agora", key=f"aprov_{task_id}", type="primary", use_container_width=True):
                            with st.spinner("Publicando no Instagram..."):
                                res = aprovar_tarefa(task_id)
                                if res.get("success"):
                                    st.success("🎉 Pauta aprovada e publicada no Instagram!")
                                else:
                                    st.warning(f"Aprovado, mas houve aviso na publicação: {res.get('publish_result', {}).get('message', res.get('error'))}")
                                st.rerun()

                    with btn_col_rej:
                        if st.button("❌ Rejeitar Pauta", key=f"rej_{task_id}", use_container_width=True):
                            rejeitar_tarefa(task_id, motivo="Rejeição manual via painel do fundador")
                            st.info("Pauta rejeitada e cancelada.")
                            st.rerun()

    # ── HISTÓRICO DE PAUTAS ON-DEMAND ──
    if historico:
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        with st.expander(f"📜 Histórico de Pautas Processadas ({len(historico)})", expanded=False):
            for t_hist in historico:
                st_badge = t_hist.get("hitl_status", "UNKNOWN")
                if st_badge == "PUBLISHED":
                    badge_color = "#10B981"
                    badge_label = "✅ PUBLICADO"
                    if t_hist.get("auto_published"):
                        badge_label += " (AUTO 60M)"
                elif st_badge == "REJECTED":
                    badge_color = "#EF4444"
                    badge_label = "❌ REJEITADO"
                else:
                    badge_color = "#6B7280"
                    badge_label = st_badge

                st.markdown(f"""
                <div style="background: #0D1117; border: 1px solid #21262D; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="font-weight: 600; color: #F0F6FC;">{t_hist.get('headline', 'Sem título')}</span>
                        <div style="color: #8B949E; font-size: 0.8rem; margin-top: 4px;">
                            Criado em: {t_hist.get('created_at', '')[:19]} | Formato: {t_hist.get('formato', 'carrossel')}
                        </div>
                    </div>
                    <div>
                        <span style="background: rgba(16,185,129,0.1); color: {badge_color}; border: 1px solid {badge_color}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                            {badge_label}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
