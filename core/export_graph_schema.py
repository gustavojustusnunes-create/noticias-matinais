"""
core/export_graph_schema.py — Exportador Dinâmico de Schema do Grafo & Infraestrutura
All News Journal & Finance

Inspeciona em tempo de execução:
1. A topologia real do StateGraph compilado (via LangGraph get_graph().nodes e edges).
2. O estado ativo mais recente em logs/graph_state.json (determinando o nó ativo, status e retries).
3. Os metadados físicos dos submódulos satélites (mtime, existência, tamanho).
4. Exporta landing/public/system_schema.json (Astro/Vercel) e logs/system_schema.json (Streamlit).
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Garante que a raiz do repositório esteja no sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Suporte a Unicode seguro no terminal Windows
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

# Timezone de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

LOGS_DIR = ROOT_DIR / "logs"
LANDING_PUBLIC_DIR = ROOT_DIR / "landing" / "public"
STATE_FILE = LOGS_DIR / "graph_state.json"
EXPORT_PUBLIC_FILE = LANDING_PUBLIC_DIR / "system_schema.json"
EXPORT_LOGS_FILE = LOGS_DIR / "system_schema.json"

# =============================================================================
# --- 1. CATÁLOGO DE METADADOS ENRIQUECIDOS PARA OS NÓS DO LANGGRAPH ---
# =============================================================================
METADATA_LANGGRAPH_NODES = {
    "planner": {
        "label": "Planner",
        "sublabel": "node_planner",
        "category": "Orquestração",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "🎯",
        "color": "#2563EB",
        "type": "executor",
        "file": "core/graph_engine.py",
        "func": "node_planner(state: GraphState)",
        "model": "Algoritmo de Priorização & Curadoria",
        "desc": "Analisa o pool de notícias do dia (ou snapshot de edicoes/) e elege a pauta de maior densidade nos cadernos nobres ('IA' ou 'Economia').",
        "inputs": ["raw_news: List[Dict]"],
        "outputs": ["selected_story: Dict", "status: 'PLANNER_DONE'"],
        "resilience": "Fallback sintético nobre de alta disponibilidade caso o pool esteja vazio.",
        "pos": {"x": 170, "y": 140}
    },
    "writer": {
        "label": "Writer",
        "sublabel": "node_writer",
        "category": "Orquestração",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "✍️",
        "color": "#2563EB",
        "type": "executor",
        "file": "core/graph_engine.py",
        "func": "node_writer(state: GraphState)",
        "model": "Google Gemini 1.5 Flash (temp: 0.25, max_tokens: 250)",
        "desc": "Redige rascunho de alta densidade analítica no tom executivo, estruturado em exatamente 2 parágrafos com fatos e desdobramentos de mercado.",
        "inputs": ["selected_story: Dict", "critique_feedback: Optional[str]", "retry_count: int"],
        "outputs": ["draft_text: str", "word_count: int", "status: 'DRAFT_GENERATED'"],
        "resilience": "Reescrita reativa orientada pelas correções do Critic. Fallback local calibrado para 85-105 palavras se a API oscilar.",
        "pos": {"x": 390, "y": 140}
    },
    "critic": {
        "label": "Critic (Quality Gate)",
        "sublabel": "node_critic",
        "category": "Quality Gate",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "⚖️",
        "color": "#A855F7",
        "type": "gate",
        "file": "core/graph_engine.py",
        "func": "node_critic(state: GraphState)",
        "model": "Auditoria Determinística de Conformidade",
        "desc": "Valida rigidamente a margem de 85 a 105 palavras (tolerância 82-108) e proíbe interrogações finais ou clickbaits. Aciona loop de autocura.",
        "inputs": ["draft_text: str", "retry_count: int"],
        "outputs": ["is_approved: bool", "word_count: int", "critique_feedback: str", "status: 'CRITIC_APPROVED' | 'CRITIC_REJECTED'"],
        "resilience": "Teto de 3 tentativas para evitar loops infinitos. Na 3ª tentativa esgotada, avança com o melhor draft para garantir o SLA.",
        "pos": {"x": 610, "y": 140}
    },
    "media_generator": {
        "label": "Media Generator",
        "sublabel": "node_media_gen",
        "category": "Mídia & Design",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "🎨",
        "color": "#10B981",
        "type": "executor",
        "file": "core/graph_engine.py",
        "func": "node_media_generator(state: GraphState)",
        "model": "Edge-TTS (pt-BR-AntonioNeural) + Pillow Renderer",
        "desc": "Sintetiza áudio neural do podcast em landing/public/audio/latest.mp3 e renderiza a Capa Editorial Clássica Slide 1 (1080x1350) em tons preto e dourado.",
        "inputs": ["draft_text: str", "selected_story: Dict"],
        "outputs": ["audio_path: str", "image_path: str", "status: 'AWAITING_FOUNDER_APPROVAL'"],
        "resilience": "Fallback para gradiente e moldura pura se o download da foto da notícia falhar.",
        "pos": {"x": 170, "y": 390}
    },
    "hitl_gate": {
        "label": "HITL Founder Gate",
        "sublabel": "interrupt_before",
        "category": "Governança & HITL",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "🔒",
        "color": "#F59E0B",
        "type": "gate",
        "file": "core/graph_engine.py",
        "func": "checkpointer.interrupt_before=['dispatcher']",
        "model": "Controle Human-In-The-Loop",
        "desc": "Ponto de suspensão determinístico do StateGraph. Exige aprovação manual do fundador no Streamlit para liberar o envio público.",
        "inputs": ["status: 'AWAITING_FOUNDER_APPROVAL'"],
        "outputs": ["status: 'APPROVED_BY_FOUNDER'", "hitl_approved: True"],
        "resilience": "Bloqueia o despacho externo se a aprovação não estiver confirmada.",
        "pos": {"x": 400, "y": 390}
    },
    "dispatcher": {
        "label": "Dispatcher",
        "sublabel": "node_dispatcher",
        "category": "Distribuição",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "🚀",
        "color": "#F43F5E",
        "type": "executor",
        "file": "core/graph_engine.py",
        "func": "node_dispatcher(state: GraphState)",
        "model": "Playwright Bot + Resend Dispatcher",
        "desc": "Ponto de disparo externo. Executa postagem no X via robô headless e dispara a newsletter por e-mail quando aprovado pelo fundador.",
        "inputs": ["status: 'APPROVED_BY_FOUNDER'", "image_path: str", "audio_path: str"],
        "outputs": ["status: 'DISPATCHED'", "execution_log: List"],
        "resilience": "Isolamento de canais: se o X falhar, os e-mails e a landing page continuam sendo publicados.",
        "pos": {"x": 620, "y": 390}
    },
    "__start__": {
        "label": "START",
        "sublabel": "Início do Grafo",
        "category": "Terminal",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "▶️",
        "color": "#64748B",
        "type": "terminal",
        "file": "core/graph_engine.py",
        "func": "START",
        "model": "LangGraph Runtime",
        "desc": "Ponto de entrada do pipeline diário acionado via scheduler ou manual.",
        "inputs": [],
        "outputs": ["GraphState inicializado"],
        "resilience": "Inicialização segura do estado.",
        "pos": {"x": 60, "y": 155}
    },
    "__end__": {
        "label": "END",
        "sublabel": "Fim do Grafo",
        "category": "Terminal",
        "cluster": "langgraph",
        "cluster_label": "1. Orquestração LangGraph Core",
        "icon": "⏹️",
        "color": "#64748B",
        "type": "terminal",
        "file": "core/graph_engine.py",
        "func": "END",
        "model": "LangGraph Runtime",
        "desc": "Ciclo completado com sucesso e logs persistidos.",
        "inputs": ["status: 'DISPATCHED'"],
        "outputs": ["Pipeline finalizado"],
        "resilience": "Persistência em logs/graph_state.json.",
        "pos": {"x": 820, "y": 435}
    }
}

# =============================================================================
# --- 2. CATÁLOGO DOS SUBMÓDULOS DE INFRAESTRUTURA & SATÉLITES ---
# =============================================================================
METADATA_INFRA_NODES = {
    "ai_supervisor": {
        "id": "ai_supervisor",
        "label": "AI Supervisor",
        "sublabel": "ai_supervisor.py",
        "category": "Observabilidade & Auditoria",
        "cluster": "observability",
        "cluster_label": "2. Observabilidade, Memória & Sentinelas",
        "icon": "🕵️",
        "color": "#38BDF8",
        "type": "auditor",
        "file": "ai_supervisor.py",
        "func": "revisar_edicao_diaria(cache_global)",
        "model": "Auditor Cognitivo Global",
        "desc": "Audita os 8 cadernos do Journal e 4 do Finance. Aplica deduplicação semântica multi-veículo (>55%) e garante profundidade de 200 a 400 palavras.",
        "inputs": ["cache_global com notícias coletadas"],
        "outputs": ["cache_global auditado e aprofundado"],
        "resilience": "Execução isolada em try/catch para nunca interromper o fluxo principal.",
        "pos": {"x": 890, "y": 185}
    },
    "supervisor_memory": {
        "id": "supervisor_memory",
        "label": "Memória Cognitiva IA",
        "sublabel": "supervisor_memory.json",
        "category": "Memória Contínua",
        "cluster": "observability",
        "cluster_label": "2. Observabilidade, Memória & Sentinelas",
        "icon": "🧠",
        "color": "#38BDF8",
        "type": "database",
        "file": "logs/supervisor_memory.json",
        "func": "carregar_memoria() / salvar_memoria()",
        "model": "Histórico de Aprendizado JSON",
        "desc": "Armazena lições aprendidas de erros anteriores para guiar os prompts seguintes e mantém blacklist de fotos usadas para evitar repetição por 90 dias.",
        "inputs": ["novos_erros: List", "novas_fotos: List"],
        "outputs": ["lições formatadas para injeção em prompts"],
        "resilience": "Criação automática caso o arquivo não exista.",
        "pos": {"x": 1150, "y": 185}
    },
    "agent_watchdog": {
        "id": "agent_watchdog",
        "label": "Watchdog Sentinela",
        "sublabel": "agent_watchdog.py",
        "category": "Auto-Cura & SLAs",
        "cluster": "observability",
        "cluster_label": "2. Observabilidade, Memória & Sentinelas",
        "icon": "🛡️",
        "color": "#10B981",
        "type": "sentinel",
        "file": "agent_watchdog.py",
        "func": "inspecionar_agentes()",
        "model": "Monitoramento Horário & GitHub Actions CLI",
        "desc": "Vigia continuamente os SLAs de entrega das edições, notifica incidentes via Resend e aciona auto-recuperação com 'gh workflow run'.",
        "inputs": ["Verificação de arquivos em edicoes/ e status de serviços"],
        "outputs": ["logs/agent_health.json & Alertas E-mail"],
        "resilience": "Reinicia workflows falhados em background sem intervenção humana.",
        "pos": {"x": 1360, "y": 185}
    },
    "telemetry_logs": {
        "id": "telemetry_logs",
        "label": "Telemetria & Logs",
        "sublabel": "graph_state.json",
        "category": "Observabilidade",
        "cluster": "observability",
        "cluster_label": "2. Observabilidade, Memória & Sentinelas",
        "icon": "📊",
        "color": "#64748B",
        "type": "logs",
        "file": "logs/graph_state.json",
        "func": "salvar_estado_disco(estado)",
        "model": "JSON Telemetry Stream",
        "desc": "Persiste o snapshot integral do estado do grafo e logs de execução para visualização no Streamlit e monitoramento de falhas.",
        "inputs": ["Transições de estado do StateGraph"],
        "outputs": ["JSON Schema para React Flow e Streamlit"],
        "resilience": "I/O atômico em disco.",
        "pos": {"x": 1160, "y": 380}
    },
    "x_robot": {
        "id": "x_robot",
        "label": "Robô do X (Zero-Custo)",
        "sublabel": "postar_x_diario.py",
        "category": "Distribuição Social",
        "cluster": "delivery",
        "cluster_label": "3. Motores de Distribuição Multicanal",
        "icon": "🐦",
        "color": "#F43F5E",
        "type": "robot",
        "file": "postar_x_diario.py",
        "func": "postar_x_via_playwright()",
        "model": "Playwright Headless + Stealth Session",
        "desc": "Publica no perfil @allnews_journal sem consumir créditos de API paga. Injeta cookies 'auth_token' e 'ct0', anexa a Capa e cria auto-reply com link para a Vercel.",
        "inputs": ["Snapshot diário e Capa Clássica 1080x1350"],
        "outputs": ["Tweet publicado + thread encadeada após 12s"],
        "resilience": "Bypass de Cloudflare Turnstile, captura de screenshots de depuração e retry de navegação.",
        "pos": {"x": 70, "y": 710}
    },
    "instagram_poster": {
        "id": "instagram_poster",
        "label": "Instagram Carrossel Bot",
        "sublabel": "instagram_poster.py",
        "category": "Distribuição Social",
        "cluster": "delivery",
        "cluster_label": "3. Motores de Distribuição Multicanal",
        "icon": "📸",
        "color": "#F43F5E",
        "type": "robot",
        "file": "instagram_poster.py",
        "func": "publicar_carrossel_instagram()",
        "model": "Instagrapi Mobile Session + Pillow Mask",
        "desc": "Compõe carrosséis verticais com máscara tipográfica recortando a foto nas letras da palavra-chave e publica via sessão mobile com intervalo de 3min.",
        "inputs": ["edicoes/YYYY-MM-DD.json"],
        "outputs": ["Post Carrossel publicado no feed"],
        "resilience": "Fallback com envio automático das peças prontas por e-mail se a sessão mobile expirar.",
        "pos": {"x": 290, "y": 710}
    },
    "email_builder": {
        "id": "email_builder",
        "label": "E-mail Assinantes",
        "sublabel": "email_builder.py",
        "category": "Distribuição Transacional",
        "cluster": "delivery",
        "cluster_label": "3. Motores de Distribuição Multicanal",
        "icon": "✉️",
        "color": "#F43F5E",
        "type": "email",
        "file": "email_builder.py",
        "func": "gerar_html_final() / enviar_email()",
        "model": "HTML Responsivo Inline + Resend API / SMTP",
        "desc": "Monta a newsletter executiva personalizada respeitando a ordem de cadernos de cada leitor na planilha do Google Sheets.",
        "inputs": ["Assinantes Google Sheets + Pacote de Notícias do Dia"],
        "outputs": ["Disparo em lote com tolerância a falhas individuais"],
        "resilience": "Falha no e-mail de um leitor nunca interrompe a fila dos outros assinantes.",
        "pos": {"x": 510, "y": 710}
    },
    "podcast_builder": {
        "id": "podcast_builder",
        "label": "Podcast Bancada (Leo & Ana)",
        "sublabel": "podcast_builder.py",
        "category": "Mídia & Áudio",
        "cluster": "delivery",
        "cluster_label": "3. Motores de Distribuição Multicanal",
        "icon": "🎙️",
        "color": "#10B981",
        "type": "audio",
        "file": "podcast_builder.py",
        "func": "compilar_podcast(edicao)",
        "model": "Edge-TTS Neural Duo (Leo & Ana) + Pydub",
        "desc": "Roteiriza e grava o diálogo matinal estilo NotebookLM com âncoras virtuais, gera áudio para o site e compila o feed RSS de podcast.",
        "inputs": ["Snapshot de notícias da edição"],
        "outputs": ["landing/public/audio/latest.mp3 e podcast.xml"],
        "resilience": "Roteiro conversacional de fallback que garante o podcast completo mesmo sem API de LLM.",
        "pos": {"x": 730, "y": 710}
    },
    "site_publisher": {
        "id": "site_publisher",
        "label": "Site Publisher (Sync Web)",
        "sublabel": "site_publisher.py",
        "category": "Sincronização",
        "cluster": "delivery",
        "cluster_label": "3. Motores de Distribuição Multicanal",
        "icon": "🌐",
        "color": "#D1BA73",
        "type": "sync",
        "file": "site_publisher.py",
        "func": "publicar_edicao()",
        "model": "Snapshot Hydration Bridge",
        "desc": "Grava o snapshot histórico imutável em edicoes/ e atualiza em tempo real o arquivo landing/src/data/edicao_atual.json para a Vercel.",
        "inputs": ["CACHE_GLOBAL de notícias"],
        "outputs": ["landing/src/data/edicao_atual.json e edicoes/index.json"],
        "resilience": "Envelopado em try/catch para jamais afetar os disparos de e-mail.",
        "pos": {"x": 950, "y": 710}
    },
    "astro_vercel": {
        "id": "astro_vercel",
        "label": "Vitrine dos Leitores (Vercel)",
        "sublabel": "Astro v4+ SSG",
        "category": "Interface Pública",
        "cluster": "interfaces",
        "cluster_label": "4. Camada de Interfaces & Portais",
        "icon": "🚀",
        "color": "#D1BA73",
        "type": "frontend",
        "file": "landing/src/pages/index.astro",
        "func": "Astro SSG Static Build",
        "model": "Astro v4 + Tailwind Dark Executivo",
        "desc": "Portal oficial dos leitores (noticias-matinais.vercel.app). Carregamento veloz (< 0.5s), player de áudio integrado e captura de assinantes.",
        "inputs": ["landing/src/data/edicao_atual.json", "audio/latest.mp3"],
        "outputs": ["Experiência do leitor em alta performance"],
        "resilience": "100% estático e desacoplado do Streamlit: permanece sempre online no edge.",
        "pos": {"x": 1215, "y": 715}
    },
    "streamlit_admin": {
        "id": "streamlit_admin",
        "label": "Control Center (Streamlit)",
        "sublabel": "app.py",
        "category": "Interface de Gestão",
        "cluster": "interfaces",
        "cluster_label": "4. Camada de Interfaces & Portais",
        "icon": "⚙️",
        "color": "#38BDF8",
        "type": "backoffice",
        "file": "app.py",
        "func": "Streamlit Backoffice (app.py, agentic_graph.py, cpo_cockpit.py)",
        "model": "Streamlit Multi-Page Studio",
        "desc": "Painel de controle interno do fundador com Graph Studio, liberação do HITL Gate, monitoramento dos sentinelas e métricas do CPO (RICE).",
        "inputs": ["logs/graph_state.json", "logs/supervisor_memory.json", "Google Sheets"],
        "outputs": ["Governança, disparo forçado e telemetria de agentes"],
        "resilience": "Painel isolado em ambiente privado com autenticação.",
        "pos": {"x": 1460, "y": 715}
    }
}

# =============================================================================
# --- 3. EXTRAÇÃO DINÂMICA DO STATEGRAPH DO LANGGRAPH ---
# =============================================================================
def extrair_topologia_langgraph() -> Dict[str, Any]:
    """
    Importa o grafo compilado oficial e extrai os nós e arestas reais via get_graph().
    """
    try:
        from core.graph_engine import graph as compiled_graph
        graph_repr = compiled_graph.get_graph()
    except Exception as e:
        print(f"⚠️ [export_graph_schema] Erro ao importar graph de core.graph_engine: {e}")
        return {"nodes": {}, "edges": []}

    nodes_dict = {}
    edges_list = []

    # Extrai nós reais do StateGraph
    for node_id, node_obj in graph_repr.nodes.items():
        base_meta = METADATA_LANGGRAPH_NODES.get(node_id, {
            "label": node_id.replace("_", " ").title(),
            "sublabel": node_id,
            "category": "Orquestração",
            "cluster": "langgraph",
            "cluster_label": "1. Orquestração LangGraph Core",
            "icon": "⚙️",
            "color": "#2563EB",
            "type": "executor",
            "file": "core/graph_engine.py",
            "func": f"{node_id}()",
            "model": "LangGraph Runnable",
            "desc": f"Nó executor '{node_id}' do StateGraph.",
            "inputs": [],
            "outputs": [],
            "resilience": "Tratamento padrão do StateGraph.",
            "pos": {"x": 200, "y": 200}
        })
        
        node_meta = dict(base_meta)
        node_meta["id"] = node_id
        node_meta["is_hitl_gate"] = (node_id == "dispatcher") # Interrupt before dispatcher
        nodes_dict[node_id] = node_meta

    # Adiciona HITL Gate como nó explícito no visual se o dispatcher tiver interrupção
    if "dispatcher" in nodes_dict and "hitl_gate" not in nodes_dict:
        nodes_dict["hitl_gate"] = dict(METADATA_LANGGRAPH_NODES["hitl_gate"])
        nodes_dict["hitl_gate"]["id"] = "hitl_gate"

    # Extrai arestas reais do StateGraph
    for edge in graph_repr.edges:
        source = edge.source
        target = edge.target
        is_conditional = getattr(edge, "conditional", False)

        # Se for entre media_generator e dispatcher, intercala o HITL Gate visual
        if source == "media_generator" and target == "dispatcher":
            edges_list.append({
                "id": "edge_media_to_hitl",
                "source": "media_generator",
                "target": "hitl_gate",
                "conditional": False,
                "label": "Mídias Prontas",
                "color": "#F59E0B"
            })
            edges_list.append({
                "id": "edge_hitl_to_dispatcher",
                "source": "hitl_gate",
                "target": "dispatcher",
                "conditional": True,
                "label": "APPROVED_BY_FOUNDER",
                "color": "#F43F5E",
                "is_hitl_edge": True
            })
            continue

        edge_label = ""
        edge_color = "#38BDF8"
        
        if is_conditional:
            if target == "writer":
                edge_label = "RETRY (tries < 3)"
                edge_color = "#F59E0B"
            elif target == "media_generator":
                edge_label = "APPROVED (85-105w)"
                edge_color = "#10B981"
            else:
                edge_label = "CONDITIONAL"
                edge_color = "#A855F7"

        edges_list.append({
            "id": f"edge_{source}_{target}",
            "source": source,
            "target": target,
            "conditional": is_conditional,
            "label": edge_label,
            "color": edge_color
        })

    return {"nodes": nodes_dict, "edges": edges_list}


# =============================================================================
# --- 4. INSPEÇÃO DOS MÓDULOS DE INFRAESTRUTURA & STATUS ATIVO ---
# =============================================================================
def inspecionar_arquivos_infra() -> Dict[str, Any]:
    """Coleta mtime e status de existência de arquivos da infraestrutura."""
    status_arquivos = {}
    
    arquivos_para_checar = [
        "core/graph_engine.py",
        "ai_supervisor.py",
        "agent_watchdog.py",
        "postar_x_diario.py",
        "instagram_poster.py",
        "email_builder.py",
        "podcast_builder.py",
        "site_publisher.py",
        "main.py",
        "finance_main.py",
        "app.py",
        "logs/graph_state.json",
        "logs/supervisor_memory.json",
        "logs/agent_health.json",
        "landing/src/pages/index.astro"
    ]

    for rel_path in arquivos_para_checar:
        p = ROOT_DIR / rel_path
        if p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=BRT).isoformat()
            status_arquivos[rel_path] = {
                "exists": True,
                "size_bytes": p.stat().st_size,
                "mtime": mtime
            }
        else:
            status_arquivos[rel_path] = {
                "exists": False,
                "size_bytes": 0,
                "mtime": None
            }

    return status_arquivos


def obter_estado_ativo_runtime() -> Dict[str, Any]:
    """Lê logs/graph_state.json para determinar nó ativo e status operacional."""
    padrao = {
        "status": "IDLE",
        "current_active_node": "planner",
        "is_approved": False,
        "word_count": 0,
        "retry_count": 0,
        "hitl_approved": False,
        "last_updated": datetime.now(BRT).isoformat(),
        "selected_story_title": None
    }

    if not STATE_FILE.exists():
        return padrao

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        status = data.get("status", "IDLE")
        retry_count = data.get("retry_count", 0)
        is_approved = data.get("is_approved", False)
        word_count = data.get("word_count", 0)
        hitl_approved = data.get("hitl_approved", False)
        
        # Mapeamento do nó atualmente ativo
        node_ativo = "planner"
        if status == "PLANNER_DONE":
            node_ativo = "writer"
        elif status == "DRAFT_GENERATED":
            node_ativo = "critic"
        elif status in ["CRITIC_REJECTED", "CRITIQUE_RETRY"]:
            node_ativo = "writer"
        elif status in ["CRITIC_APPROVED", "MEDIA_READY"]:
            node_ativo = "media_generator"
        elif status in ["AWAITING_FOUNDER_APPROVAL", "SUSPENDED_WAITING_APPROVAL"]:
            node_ativo = "hitl_gate"
        elif status in ["APPROVED_BY_FOUNDER", "DISPATCHING"]:
            node_ativo = "dispatcher"
        elif status == "DISPATCHED":
            node_ativo = "__end__"

        story = data.get("selected_story", {})
        
        return {
            "status": status,
            "current_active_node": node_ativo,
            "is_approved": is_approved,
            "word_count": word_count,
            "retry_count": retry_count,
            "hitl_approved": hitl_approved,
            "selected_story_title": story.get("titulo"),
            "last_updated": datetime.now(BRT).isoformat(),
            "execution_log_count": len(data.get("execution_log", []))
        }
    except Exception as e:
        print(f"⚠️ [export_graph_schema] Erro ao ler graph_state.json: {e}")
        return padrao


# =============================================================================
# --- 5. COMPILAÇÃO DO SCHEMA COMPLETO E EXPORTAÇÃO ---
# =============================================================================
def compilar_schema_completo() -> Dict[str, Any]:
    """Compila o grafo do LangGraph, os satélites de infraestrutura e a telemetria."""
    langgraph_data = extrair_topologia_langgraph()
    infra_status = inspecionar_arquivos_infra()
    runtime_state = obter_estado_ativo_runtime()

    todos_nos = []
    
    # 1. Nós do LangGraph Core
    for node_id, node_meta in langgraph_data["nodes"].items():
        node_copy = dict(node_meta)
        node_copy["is_active"] = (runtime_state["current_active_node"] == node_id)
        
        # Injeta mtime do core/graph_engine.py
        file_info = infra_status.get(node_copy.get("file", ""), {})
        node_copy["file_mtime"] = file_info.get("mtime")
        node_copy["file_exists"] = file_info.get("exists", True)
        
        # Enriquecimento de estado ativo
        if node_id == "critic":
            node_copy["runtime_word_count"] = runtime_state.get("word_count", 0)
            node_copy["runtime_is_approved"] = runtime_state.get("is_approved", False)
        elif node_id == "hitl_gate":
            node_copy["runtime_hitl_approved"] = runtime_state.get("hitl_approved", False)
            node_copy["is_locked"] = not runtime_state.get("hitl_approved", False)
        elif node_id == "writer":
            node_copy["runtime_retry_count"] = runtime_state.get("retry_count", 0)

        todos_nos.append(node_copy)

    # 2. Nós Satélites da Infraestrutura
    for node_id, node_meta in METADATA_INFRA_NODES.items():
        node_copy = dict(node_meta)
        file_info = infra_status.get(node_copy.get("file", ""), {})
        node_copy["file_mtime"] = file_info.get("mtime")
        node_copy["file_exists"] = file_info.get("exists", True)
        node_copy["is_active"] = False
        todos_nos.append(node_copy)

    # 3. Arestas do LangGraph + Arestas de Integração da Infraestrutura
    todas_arestas = list(langgraph_data["edges"])

    arestas_infra = [
        # LangGraph ➔ Motores de Entrega
        {"id": "edge_disp_to_x", "source": "dispatcher", "target": "x_robot", "conditional": False, "label": "Disparo Headless", "color": "#F43F5E"},
        {"id": "edge_disp_to_email", "source": "dispatcher", "target": "email_builder", "conditional": False, "label": "Resend API", "color": "#F43F5E"},
        {"id": "edge_disp_to_insta", "source": "dispatcher", "target": "instagram_poster", "conditional": False, "label": "Carrossel Mobile", "color": "#F43F5E"},
        {"id": "edge_media_to_podcast", "source": "media_generator", "target": "podcast_builder", "conditional": False, "label": "Síntese Edge-TTS", "color": "#10B981"},
        {"id": "edge_disp_to_publisher", "source": "dispatcher", "target": "site_publisher", "conditional": False, "label": "Sync edicao.json", "color": "#D1BA73"},
        
        # Sincronizador ➔ Vitrine Astro Vercel
        {"id": "edge_pub_to_astro", "source": "site_publisher", "target": "astro_vercel", "conditional": False, "label": "Deploy SSG", "color": "#D1BA73"},
        {"id": "edge_pod_to_astro", "source": "podcast_builder", "target": "astro_vercel", "conditional": False, "label": "Player Áudio", "color": "#10B981"},
        {"id": "edge_x_to_astro", "source": "x_robot", "target": "astro_vercel", "conditional": True, "label": "Auto-Reply Link", "color": "#60A5FA", "is_dashed": True},
        
        # Observabilidade & Memória
        {"id": "edge_sup_to_mem", "source": "ai_supervisor", "target": "supervisor_memory", "conditional": False, "label": "Persiste Lições", "color": "#38BDF8"},
        {"id": "edge_watch_to_telemetry", "source": "agent_watchdog", "target": "telemetry_logs", "conditional": False, "label": "SLA & Alertas", "color": "#10B981"},
        {"id": "edge_telemetry_to_admin", "source": "telemetry_logs", "target": "streamlit_admin", "conditional": False, "label": "Live Stream", "color": "#D1BA73"}
    ]
    todas_arestas.extend(arestas_infra)

    clusters = [
        {"id": "langgraph", "title": "1. ORQUESTRAÇÃO LANGGRAPH (core/graph_engine.py)", "color": "#2563EB", "rect": {"x": 40, "y": 40, "width": 790, "height": 540}},
        {"id": "observability", "title": "2. OBSERVABILIDADE, MEMÓRIA & SENTINELAS", "color": "#38BDF8", "rect": {"x": 860, "y": 40, "width": 840, "height": 540}},
        {"id": "delivery", "title": "3. MOTORES DE DISTRIBUIÇÃO MULTICANAL", "color": "#F43F5E", "rect": {"x": 40, "y": 620, "width": 1120, "height": 360}},
        {"id": "interfaces", "title": "4. CAMADA DE INTERFACES & PORTAIS", "color": "#D1BA73", "rect": {"x": 1190, "y": 620, "width": 510, "height": 360}}
    ]

    schema = {
        "version": "2.0.0",
        "last_updated": datetime.now(BRT).isoformat(),
        "active_run_state": runtime_state,
        "clusters": clusters,
        "nodes": todos_nos,
        "edges": todas_arestas,
        "stats": {
            "total_nodes": len(todos_nos),
            "langgraph_nodes": len(langgraph_data["nodes"]),
            "infrastructure_nodes": len(METADATA_INFRA_NODES),
            "total_edges": len(todas_arestas),
            "current_status": runtime_state["status"],
            "current_active_node": runtime_state["current_active_node"]
        }
    }

    return schema


def exportar_schema_completo() -> Dict[str, Any]:
    """Compila e salva o schema em landing/public/system_schema.json e logs/system_schema.json."""
    schema = compilar_schema_completo()
    
    # 1. Salva em landing/public/system_schema.json
    try:
        LANDING_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        with open(EXPORT_PUBLIC_FILE, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"✅ [export_graph_schema] Schema salvo em: {EXPORT_PUBLIC_FILE}")
    except Exception as e:
        print(f"⚠️ [export_graph_schema] Falha ao salvar em landing/public: {e}")

    # 2. Salva em logs/system_schema.json
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EXPORT_LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"✅ [export_graph_schema] Schema salvo em: {EXPORT_LOGS_FILE}")
    except Exception as e:
        print(f"⚠️ [export_graph_schema] Falha ao salvar em logs/: {e}")

    return schema


if __name__ == "__main__":
    print("🚀 Disparando exportação dinâmica do schema do sistema...")
    resultado = exportar_schema_completo()
    print(f"✨ Concluído! {resultado['stats']['total_nodes']} nós e {resultado['stats']['total_edges']} arestas mapeadas.")
    print(f"   Status Ativo: [{resultado['stats']['current_status']}] ➔ Nó em Foco: '{resultado['stats']['current_active_node']}'")
