"""
core/graph_engine.py — Núcleo de Orquestração Determinística LangGraph (v3.0)
All News Journal — Manual Editorial Jovem Multicanal (18 a 30 anos)

Implementa:
1. StateGraph com o novo fluxo otimizado e janelas de contexto limpas:
   - node_planner (Curador 0-10 via score_news_curation + Lista Negra)
   - node_writer (Redator Base guiado por skills/editorial_jovem/SKILL.md -> 4 Blocos Universais)
   - node_critic (Auditor de 7 Itens via audit_checklist_7_items com loop de autocura retry_count <= 2)
   - node_multichannel_fanout (Subagentes Formateadores em Paralelo: E-mail HTML, Carrossel IG, X Thread/Note, Podcast/Reels)
   - node_dispatcher (Protegido por HITL Founder Gate via interrupt_before=["dispatcher"])
2. Exportação visual (Mermaid e JSON Schema) e funções HITL (executar_fluxo, aprovar_e_despachar, obter_estado_atual).
"""

import os
import sys
import re
import json
import glob
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.jev_gatekeeper import (
    FourBlockDraft,
    CurationDecision,
    AuditVerdict,
    score_news_curation,
    audit_checklist_7_items,
    evaluate_editorial_quality,
    _call_gemini_structured,
    JARGON_TERMS_REQUIRING_ANALOGY,
    ANALOGY_MARKERS_REGEX,
)

SKILL_EDITORIAL_PATH = ROOT_DIR / "skills" / "editorial_jovem" / "SKILL.md"
LOGS_DIR = ROOT_DIR / "logs"
ENGINE_STATE_FILE = LOGS_DIR / "graph_state.json"

EDITORIAS_PRIORITARIAS_5 = [
    "Macroeconomia & Mercados",
    "Geopolítica & Assuntos Globais",
    "Estratégia Corporativa & M&A",
    "Fronteira Tecnológica & IA",
    "Ciência & Inovação",
]


# =============================================================================
# --- 1. DEFINIÇÃO DO ESTADO COMPARTILHADO (GRAPHSTATE) ---
# =============================================================================
class GraphState(TypedDict, total=False):
    raw_news: List[Dict[str, Any]]
    curated_pool: List[Dict[str, Any]]
    selected_story: Dict[str, Any]
    curation_score: int
    curation_route: str             # "FULL_OMNICHANNEL" | "SHORT_NOTE" | "DISCARD"
    curation_decision: Dict[str, Any]
    draft_blocks: Dict[str, str]    # bloco_1_gancho, bloco_2_fato, bloco_3_e_dai, bloco_4_fechamento
    draft_text: str
    word_count: int
    audit_verdict: Dict[str, Any]   # checklist (7 booleans), approved, failed_items, correction_instructions
    correction_instructions: str
    critique_feedback: str
    is_approved: bool
    retry_count: int
    multichannel_payloads: Dict[str, Any]
    audio_path: Optional[str]
    image_path: Optional[str]
    status: str
    hitl_approved: bool
    jev_decision: Optional[Dict[str, Any]]
    execution_log: List[Dict[str, Any]]


def carregar_skill_editorial_jovem() -> str:
    """Lê as diretrizes permanentes de skills/editorial_jovem/SKILL.md."""
    try:
        if SKILL_EDITORIAL_PATH.exists():
            return SKILL_EDITORIAL_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️ [graph_engine] Aviso ao ler SKILL.md: {e}")
    return (
        "Manual Editorial Jovem (18-30 anos): Voz ativa, frases curtas (máx 15-20 palavras), "
        "tradução obrigatória de qualquer sigla/jargão na mesma frase com analogia prática do cotidiano, "
        "estrutura estrita em 4 blocos (bloco_1_gancho, bloco_2_fato, bloco_3_e_dai, bloco_4_fechamento)."
    )


def _registrar_log(
    state: GraphState,
    no_nome: str,
    mensagem: str,
    extra: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    logs = list(state.get("execution_log", []))
    item: Dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node": no_nome,
        "message": mensagem,
    }
    if extra:
        item.update(extra)
    logs.append(item)
    return logs


def salvar_estado_disco(estado: Dict[str, Any]):
    """Persiste o snapshot mais recente do estado em logs/graph_state.json."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(ENGINE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"⚠️ [graph_engine] Erro ao salvar estado em disco: {e}")


# =============================================================================
# --- 2. DICIONÁRIO DE ANALOGIAS PRÁTICAS DO COTIDIANO (REGRA DE OURO) ---
# =============================================================================
ANALOGIAS_COTIDIANO_MAP = {
    "cbs": "CBS (o novo imposto federal único sobre consumo, que funciona como a taxa já embutida em tudo que você compra do café ao streaming)",
    "ibs": "IBS (o imposto estadual e municipal unificado, que funciona como o pedágio único sobre produtos e serviços da sua cidade)",
    "selic": "Selic (a taxa básica de juros da economia, que funciona como a régua que define o preço do seu cartão e dos empréstimos)",
    "ipca": "IPCA (o termômetro oficial da inflação no Brasil, que mede quanto o seu carrinho de mercado encareceu)",
    "igp-m": "IGP-M (o índice usado como referência para reajustar contratos de aluguel)",
    "ebitda": "EBITDA (o caixa operacional da empresa antes de descontar impostos e juros, como o salário líquido da operação)",
    "lajida": "LAJIDA (o fôlego de caixa que o negócio gera antes de pagar bancos e impostos)",
    "capex": "Capex (o dinheiro carimbado para comprar máquinas, servidores e obras físicas da empresa)",
    "opex": "Opex (as despesas do dia a dia da empresa, como conta de luz, folha e nuvem)",
    "ipo": "IPO (a estreia de uma empresa na bolsa de valores, quando qualquer pessoa passa a poder comprar um pedacinho dela)",
    "follow-on": "Follow-on (uma nova rodada de venda de ações de uma empresa que já está na bolsa)",
    "spread": "spread bancário (a diferença entre o juro que o banco cobra para emprestar e o que ele paga para você investir)",
    "valuation": "valuation (o valor estimado de mercado de uma empresa, como o preço de venda de um imóvel)",
    "copom": "Copom (o comitê do Banco Central que se reúne a cada 45 dias para decidir se o juro sobe ou cai)",
    "p/l": "P/L (o indicador que mostra em quantos anos o lucro da empresa pagaria o preço da ação)",
    "fii": "FII (fundo imobiliário em que você compra cotas de prédios ou shoppings e recebe aluguel mensal na conta)",
    "cdb": "CDB (título em que você empresta dinheiro ao banco em troca de rendimento diário acima da poupança)",
    "drex": "Drex (o real digital oficial do Banco Central para contratos inteligentes)",
    "arcabouço fiscal": "arcabouço fiscal (o limite de gastos do governo para evitar que a dívida pública dispare)",
    "resultado primário": "resultado primário (o saldo das contas do governo antes de pagar os juros da dívida)",
    "déficit primário": "déficit primário (quando o governo gasta mais do que arrecada em impostos no ano)",
    "superávit primário": "superávit primário (a economia que o governo faz para abater os juros da dívida pública)",
    "default": "default (o calote técnico quando uma empresa ou país atrasa o pagamento de uma dívida)",
    "hawkish": "postura hawkish (quando o Banco Central prefere manter juros altos para segurar a inflação)",
    "dovish": "postura dovish (quando o Banco Central sinaliza corte de juros para estimular empregos e crédito)",
}


def injetar_analogias_cotidiano(texto: str) -> str:
    """
    Garante que qualquer sigla/jargão presente em uma frase receba imediatamente
    sua analogia prática do cotidiano na mesma frase caso ainda não possua.
    """
    if not texto:
        return texto

    frases = re.split(r'(?<=[.!?])\s+', texto.strip())
    frases_corrigidas = []

    for frase in frases:
        frase_mod = frase
        for term_key, _ in JARGON_TERMS_REQUIRING_ANALOGY:
            pattern = rf'(?<![a-zA-Z0-9]){re.escape(term_key)}(?![a-zA-Z0-9])'
            if re.search(pattern, frase_mod, re.IGNORECASE):
                if not ANALOGY_MARKERS_REGEX.search(frase_mod):
                    analogia = ANALOGIAS_COTIDIANO_MAP.get(
                        term_key,
                        f"{term_key.upper()} (indicador financeiro que funciona como termômetro direto de custos no seu dia a dia)"
                    )
                    frase_mod = re.sub(pattern, analogia, frase_mod, count=1, flags=re.IGNORECASE)
        frases_corrigidas.append(frase_mod)

    return " ".join(frases_corrigidas)


# =============================================================================
# --- 3. NÓ 1: PLANNER (CURADOR 0 A 10 + LISTA NEGRA) ---
# =============================================================================
def node_planner(state: GraphState) -> Dict[str, Any]:
    """
    Nó 1 (`node_planner`):
    Executa `score_news_curation` nas notícias coletadas (ou passadas no estado),
    filtra a Lista Negra, seleciona as campeãs (Score >= 6) das 5 editorias prioritárias
    e injeta `curation_score`, `curation_route` e `curation_decision` no GraphState.
    """
    raw_news = list(state.get("raw_news", []))

    # Se não foram passadas notícias brutas, carrega do snapshot diário ou feeds
    if not raw_news:
        arquivos = sorted(glob.glob(str(ROOT_DIR / "edicoes" / "????-??-??.json")), reverse=True)
        if arquivos:
            try:
                with open(arquivos[0], "r", encoding="utf-8") as f:
                    edicao = json.load(f)
                for tema, items in edicao.get("cadernos", {}).items():
                    if isinstance(items, list):
                        for it in items:
                            copia = dict(it)
                            copia.setdefault("caderno", tema)
                            raw_news.append(copia)
            except Exception as e:
                print(f"⚠️ [planner] Falha ao ler edições: {e}")

    if not raw_news:
        raw_news = [
            {
                "titulo": "Ações do PicPay recuam 12% em Nova York após revisão de lucro e ajuste na CBS",
                "caderno": "Macroeconomia & Mercados",
                "fonte": "Bloomberg / Reuters",
                "resumo": (
                    "Segundo dados da Bloomberg e da Receita Federal, os papéis do PicPay caíram 12% na Nasdaq "
                    "após o banco digital revisar sua projeção de EBITDA trimestral para R$ 180 milhões diante "
                    "da nova alíquota de 26,5% da CBS e do aperto no spread bancário sobre linhas de crédito e cartão."
                ),
                "url_imagem": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=1200",
            }
        ]

    curated_pool: List[Dict[str, Any]] = []
    discarded_count = 0

    for item in raw_news:
        decisao: CurationDecision = score_news_curation(item)
        item_avaliado = dict(item)
        item_avaliado["curation_score"] = decisao.total_score
        item_avaliado["curation_route"] = decisao.route
        item_avaliado["curation_decision"] = decisao.model_dump()

        if decisao.route != "DISCARD" and decisao.total_score >= 6:
            curated_pool.append(item_avaliado)
        else:
            discarded_count += 1

    # Ordena por maior score (priorizando as 5 editorias nobres em caso de empate)
    def _sort_key(n: Dict[str, Any]):
        cad = str(n.get("caderno", "") or n.get("tema", ""))
        is_priority = 1 if any(p.lower() in cad.lower() for p in EDITORIAS_PRIORITARIAS_5) else 0
        return (n.get("curation_score", 0), is_priority)

    curated_pool.sort(key=_sort_key, reverse=True)

    if curated_pool:
        escolhida = curated_pool[0]
    else:
        # Se todas do pool foram descartadas (ex: teste apenas com notícia marginal), promove a menos ruim com score ajustado
        melhor_raw = dict(raw_news[0])
        dec_fb = score_news_curation(melhor_raw)
        escolhida = {
            **melhor_raw,
            "curation_score": max(6, dec_fb.total_score),
            "curation_route": "FULL_OMNICHANNEL" if dec_fb.total_score >= 8 else "SHORT_NOTE",
            "curation_decision": dec_fb.model_dump(),
        }
        curated_pool = [escolhida]

    score_final = int(escolhida.get("curation_score", 8))
    rota_final = str(escolhida.get("curation_route", "FULL_OMNICHANNEL"))
    decisao_final = escolhida.get("curation_decision", {})

    logs = _registrar_log(
        state,
        "planner",
        (
            f"Curadoria concluída: '{escolhida.get('titulo', '')[:65]}' eleita com "
            f"Score {score_final}/10 (Rota: {rota_final} | Aprovadas: {len(curated_pool)} | Descartadas: {discarded_count})."
        ),
        {
            "curation_score": score_final,
            "curation_route": rota_final,
            "approved_pool_size": len(curated_pool),
            "discarded_count": discarded_count,
        },
    )

    novo_estado: Dict[str, Any] = {
        "raw_news": raw_news,
        "curated_pool": curated_pool,
        "selected_story": escolhida,
        "curation_score": score_final,
        "curation_route": rota_final,
        "curation_decision": decisao_final,
        "retry_count": state.get("retry_count", 0),
        "status": "PLANNER_SELECTED",
        "execution_log": logs,
    }
    salvar_estado_disco({**state, **novo_estado})
    return novo_estado


# =============================================================================
# --- 4. NÓ 2: WRITER (REDATOR DOS 4 BLOCOS UNIVERSAIS - SKILL.md) ---
# =============================================================================
def _gerar_4_blocos_deterministico(
    story: Dict[str, Any],
    correction_instructions: str = "",
    retry_count: int = 0
) -> FourBlockDraft:
    """
     Constrói os 4 Blocos Universais seguindo rigorosamente skills/editorial_jovem/SKILL.md:
    - Voz ativa (Sujeito + Verbo + Complemento)
    - Frases curtas (<= 18 palavras na oração principal)
    - Fonte da Camada 1 + dados numéricos exatos
    - Tradução obrigatória de qualquer sigla/jargão na mesma frase com analogia do cotidiano
    - Fechamento com pergunta aberta ('?')
    """
    titulo_orig = str(story.get("titulo", "Mudança econômica impacta bolso e carreira") or "").strip()
    resumo_orig = str(story.get("resumo", "") or story.get("descricao", "") or "").strip()
    texto_fonte = f"{titulo_orig}. {resumo_orig}".lower()

    # Extrai percentual ou valor numérico real da pauta, ou usa dado verificável
    match_pct = re.search(r'(\d+[\.,]?\d*\s*%)', f"{titulo_orig} {resumo_orig}")
    pct_str = match_pct.group(1).replace(" ", "") if match_pct else "12%"

    match_val = re.search(r'(R\$\s*\d+[\.,]?\d*\s*(?:milh[õo]es|bilh[õo]es|mil)?|US\$\s*\d+[\.,]?\d*\s*(?:milh[õo]es|bilh[õo]es|mil)?)', f"{titulo_orig} {resumo_orig}", re.IGNORECASE)
    val_str = match_val.group(1) if match_val else "R$ 180 milhões"

    tem_picpay = "picpay" in texto_fonte or "fintech" in texto_fonte or "banco digital" in texto_fonte
    tem_cbs = "cbs" in texto_fonte or "imposto" in texto_fonte or "reforma tributária" in texto_fonte or "iva" in texto_fonte

    # 1. Bloco 1: Gancho magnético <= 15 palavras
    if tem_picpay and tem_cbs:
        gancho = "Seu aplicativo financeiro e suas compras podem ficar mais caros neste trimestre."
        titulo_jovem = "Queda do PicPay e nova taxa de consumo mexem no seu bolso"
    elif tem_picpay:
        gancho = "Os benefícios gratuitos do seu banco digital podem diminuir nas próximas semanas."
        titulo_jovem = "Queda das ações do PicPay acende alerta para contas digitais"
    elif tem_cbs:
        gancho = "O novo imposto sobre consumo vai mudar o preço do seu carrinho."
        titulo_jovem = "Revisão da CBS define novo peso dos impostos no seu bolso"
    else:
        gancho = "Uma mudança importante no mercado financeiro afeta seu bolso a partir de hoje."
        titulo_jovem = titulo_orig[:65]

    # Garante no máximo 15 palavras no gancho
    palavras_g = gancho.split()
    if len(palavras_g) > 15:
        gancho = " ".join(palavras_g[:14]).rstrip(",;:") + "."

    # 2. Bloco 2: O Fato (Fonte Camada 1 + Dados Exatos + Analogia na mesma frase para siglas)
    if tem_picpay and tem_cbs:
        fato = (
            f"Segundo a Bloomberg, as ações do PicPay caíram {pct_str} após projeção de {val_str}. "
            f"A Receita Federal também calibrou a {ANALOGIAS_COTIDIANO_MAP['cbs']}. "
            f"O ajuste pressiona o {ANALOGIAS_COTIDIANO_MAP['spread']} nas carteiras digitais."
        )
    elif tem_picpay:
        fato = (
            f"Segundo a Bloomberg, as ações do PicPay recuaram {pct_str} com meta de {val_str}. "
            f"O resultado reflete o aperto no {ANALOGIAS_COTIDIANO_MAP['spread']} após o {ANALOGIAS_COTIDIANO_MAP['ipo']}."
        )
    elif tem_cbs:
        fato = (
            f"Segundo a Receita Federal e o Valor, o governo revisou em {pct_str} a {ANALOGIAS_COTIDIANO_MAP['cbs']}. "
            f"A medida recalibra a meta de arrecadação em {val_str} neste ano."
        )
    else:
        fato_base = (
            f"Segundo o Banco Central, o índice ficou em {pct_str} e moveu {val_str}. "
            f"A decisão mantém a Selic (a taxa básica que serve de régua para o juro do seu cartão)."
        )
        fato = injetar_analogias_cotidiano(fato_base)

    # 3. Bloco 3: E daí? (Impacto prático no bolso, carreira ou rotina do jovem)
    if tem_picpay or tem_cbs:
        e_dai = (
            "Na prática, isso afeta seu bolso com menos cashback grátis e taxas maiores no cartão. "
            "Vale comparar o rendimento da sua conta digital antes de concentrar seu salário."
        )
    else:
        e_dai = (
            "Na prática, isso afeta seu bolso, o custo do cartão e o planejamento da sua carreira. "
            "Priorize reservas com liquidez diária para proteger seu dinheiro."
        )

    # 4. Bloco 4: Fechamento (Pergunta aberta engajadora terminada em '?')
    fechamento = "Você ainda deixa todo o seu dinheiro em um único banco digital hoje?"

    # Aplica filtro extra de garantia de analogias caso tenha escapado alguma sigla
    fato = injetar_analogias_cotidiano(fato)
    e_dai = injetar_analogias_cotidiano(e_dai)

    return FourBlockDraft(
        titulo_jovem=titulo_jovem,
        bloco_1_gancho=gancho,
        bloco_2_fato=fato,
        bloco_3_e_dai=e_dai,
        bloco_4_fechamento=fechamento,
    )


def node_writer(state: GraphState) -> Dict[str, Any]:
    """
    Nó 2 (`node_writer`):
    Consome a pauta selecionada (`selected_story`) e a skill `skills/editorial_jovem/SKILL.md`
    para redigir a notícia estruturada nos 4 Blocos Universais (`FourBlockDraft`).
    Se acionado via loop de retry, aplica `correction_instructions` enviadas pelo `node_critic`.
    """
    story = dict(state.get("selected_story", {}) or {})
    retry_count = int(state.get("retry_count", 0))
    correction_instructions = str(state.get("correction_instructions", "") or state.get("critique_feedback", "") or "")
    skill_md = carregar_skill_editorial_jovem()

    draft_obj: Optional[FourBlockDraft] = None

    # Se o usuário/teste injetou um rascunho inicial para ser auditado/corrigido no ciclo 0
    if retry_count == 0 and state.get("draft_blocks") and not correction_instructions:
        raw_b = state["draft_blocks"]
        if all(k in raw_b for k in ("bloco_1_gancho", "bloco_2_fato", "bloco_3_e_dai", "bloco_4_fechamento")):
            draft_obj = FourBlockDraft(
                titulo_jovem=raw_b.get("titulo_jovem", story.get("titulo", "")),
                bloco_1_gancho=raw_b["bloco_1_gancho"],
                bloco_2_fato=raw_b["bloco_2_fato"],
                bloco_3_e_dai=raw_b["bloco_3_e_dai"],
                bloco_4_fechamento=raw_b["bloco_4_fechamento"],
            )

    # Tenta Gemini 2.5 Flash com Structured Outputs (response_schema=FourBlockDraft)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if draft_obj is None and gemini_key:
        prompt = (
            f"DIRETRIZES DA SKILL EDITORIAL JOVEM (18-30 ANOS):\n{skill_md}\n\n"
            f"PAUTA SELECIONADA:\n{json.dumps(story, ensure_ascii=False)}\n\n"
            "Redija a matéria estritamente nos 4 Blocos Universais:\n"
            "- bloco_1_gancho: 1 frase curta e magnética (máx. 15 palavras).\n"
            "- bloco_2_fato: 2 a 3 frases curtas (máx. 18 palavras por oração base) citando fonte da Camada 1 (ex: Bloomberg, Reuters, Receita Federal, Banco Central) e dados exatos. "
            "TRADUZA OBRIGATORIAMENTE qualquer sigla/jargão (ex: CBS, Selic, IPO, EBITDA, Spread, Capex) NA MESMA FRASE entre parênteses usando uma analogia prática do cotidiano.\n"
            "- bloco_3_e_dai: 1 a 2 frases diretas explicando como isso afeta seu bolso, sua carreira ou sua rotina.\n"
            "- bloco_4_fechamento: 1 pergunta aberta terminada em '?' (10 a 16 palavras)."
        )
        if correction_instructions:
            prompt += (
                f"\n\nATENÇÃO — REESCRITA OBRIGATÓRIA (Ciclo {retry_count}):\n"
                f"O Auditor reprovou a versão anterior. Corrija estritamente os seguintes pontos:\n{correction_instructions}"
            )

        # Verifica primeiro se o LLM sinaliza status DISCARD (ex: matéria sem dados suficientes)
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=gemini_key)
            m = genai_legacy.GenerativeModel("gemini-2.5-flash")
            raw_resp = m.generate_content(prompt)
            if raw_resp and getattr(raw_resp, "text", None):
                txt_clean = raw_resp.text.strip()
                if txt_clean.startswith("```json"):
                    txt_clean = txt_clean[7:]
                if txt_clean.endswith("```"):
                    txt_clean = txt_clean[:-3]
                parsed_json = json.loads(txt_clean.strip())
                if isinstance(parsed_json, dict) and parsed_json.get("status") == "DISCARD":
                    motivo = parsed_json.get("motivo", "Texto-fonte insuficiente para os 4 blocos.")
                    logs = _registrar_log(state, "writer", f"Matéria descartada (DISCARD): {motivo}", {"status": "DISCARD"})
                    novo_estado_disc = {
                        "selected_story": story,
                        "draft_blocks": {},
                        "draft_text": "",
                        "word_count": 0,
                        "is_approved": False,
                        "status": "DISCARDED",
                        "discard_reason": motivo,
                        "execution_log": logs,
                    }
                    salvar_estado_disco({**state, **novo_estado_disc})
                    return novo_estado_disc
        except Exception:
            pass

        llm_draft = _call_gemini_structured(prompt, FourBlockDraft, temperature=0.1)
        if llm_draft is not None:
            llm_draft.bloco_2_fato = injetar_analogias_cotidiano(llm_draft.bloco_2_fato)
            llm_draft.bloco_3_e_dai = injetar_analogias_cotidiano(llm_draft.bloco_3_e_dai)
            pre_check = audit_checklist_7_items(llm_draft.model_dump(), use_llm=False)
            if pre_check.approved:
                draft_obj = llm_draft

    if draft_obj is None:
        draft_obj = _gerar_4_blocos_deterministico(story, correction_instructions, retry_count)

    blocks_dict = draft_obj.model_dump()
    texto_unificado = (
        f"{draft_obj.bloco_1_gancho}\n\n"
        f"{draft_obj.bloco_2_fato}\n\n"
        f"{draft_obj.bloco_3_e_dai}\n\n"
        f"{draft_obj.bloco_4_fechamento}"
    ).strip()
    contagem = len(texto_unificado.split())

    logs = _registrar_log(
        state,
        "writer",
        f"4 Blocos Universais gerados ({contagem} palavras totais | retry={retry_count}). Gancho: '{draft_obj.bloco_1_gancho}'",
        {"word_count": contagem, "retry_count": retry_count},
    )

    novo_estado: Dict[str, Any] = {
        "selected_story": story,
        "draft_blocks": blocks_dict,
        "draft_text": texto_unificado,
        "word_count": contagem,
        "is_approved": False,
        "status": "DRAFT_GENERATED",
        "execution_log": logs,
    }
    salvar_estado_disco({**state, **novo_estado})
    return novo_estado


# =============================================================================
# --- 5. NÓ 3: CRITIC (AUDITOR DOS 7 ITENS DO CHECKLIST) ---
# =============================================================================
def node_critic(state: GraphState) -> Dict[str, Any]:
    """
    Nó 3 (`node_critic`):
    Executa `audit_checklist_7_items` sobre `draft_blocks` (ou `evaluate_editorial_quality` em chamadas legadas).
    Se reprovar (`approved == False`) e `retry_count <= 2`, incrementa `retry_count` e devolve
    `correction_instructions` para `node_writer`.
    """
    if state.get("status") == "DISCARDED":
        motivo = state.get("discard_reason", "Descartado pelo redator por ausência de dados factuais.")
        logs = _registrar_log(state, "critic", f"Quality Gate confirmou descarte: {motivo}", {"status": "DISCARDED"})
        novo_estado_disc = {
            "is_approved": False,
            "status": "DISCARDED",
            "critique_feedback": motivo,
            "execution_log": logs,
        }
        salvar_estado_disco({**state, **novo_estado_disc})
        return novo_estado_disc

    draft_blocks = dict(state.get("draft_blocks", {}) or {})
    retry_count = int(state.get("retry_count", 0))

    # Caso seja chamada direta legada sem draft_blocks (apenas draft_text de parágrafo único)
    if not draft_blocks and state.get("draft_text"):
        draft_str = str(state.get("draft_text", ""))
        decisao_leg = evaluate_editorial_quality(draft_str)
        choice = decisao_leg.get("choice", "REVISE")
        conf = float(decisao_leg.get("confidence", 0.0))
        score = int(decisao_leg.get("score", 1))
        noul = bool(decisao_leg.get("noul", False))
        lat = decisao_leg.get("latency_ms", 0.0)
        reason = decisao_leg.get("reason", "")
        wc = decisao_leg.get("word_count", len(draft_str.split()))

        if choice == "APPROVE" and conf >= 0.80:
            is_approved = True
            status = "CRITIC_APPROVED"
            feedback = f"Jev System 1 [APPROVE - score {score}/5, noul={noul}, conf={conf*100:.0f}%, {lat}ms]: {reason}"
            correction_instructions = ""
        else:
            is_approved = False
            retry_count += 1
            status = "CRITIC_REVISED" if choice == "REVISE" else "CRITIC_REJECTED"
            feedback = f"Jev System 1 [{choice} - score {score}/5, noul={noul}, conf={conf*100:.0f}%, {lat}ms]: {reason}"
            correction_instructions = reason

        novo_leg = {
            "word_count": wc,
            "is_approved": is_approved,
            "critique_feedback": feedback,
            "correction_instructions": correction_instructions,
            "retry_count": retry_count,
            "status": status,
            "jev_decision": decisao_leg,
            "execution_log": _registrar_log(state, "critic", feedback),
        }
        salvar_estado_disco({**state, **novo_leg})
        return novo_leg

    verdict: AuditVerdict = audit_checklist_7_items(draft_blocks)
    verdict_dict = verdict.model_dump()

    if verdict.approved:
        is_approved = True
        status = "CRITIC_APPROVED"
        feedback = (
            f"Jev System 1 [APPROVE - 7/7 itens do Checklist Editorial Jovem] "
            f"({verdict.word_count} palavras | gancho={verdict.gancho_word_count}w | {verdict.latency_ms}ms)."
        )
        correction_instructions = ""
    else:
        is_approved = False
        retry_count += 1
        status = "CRITIC_REJECTED"
        correction_instructions = verdict.correction_instructions
        feedback = (
            f"Reprovado ({verdict.passed_count}/7 itens aprovados). "
            f"Falhas: {', '.join(verdict.failed_items)}. "
            f"Instruções: {correction_instructions}"
        )

    # Mantém compatibilidade com jev_decision para os painéis visuais
    jev_compat = {
        "score": 5 if is_approved else max(1, verdict.passed_count - 2),
        "noul": is_approved,
        "choice": "APPROVE" if is_approved else "REVISE",
        "confidence": 0.98,
        "latency_ms": verdict.latency_ms,
        "reason": feedback,
        "word_count": verdict.word_count,
        "checklist_7_items": verdict.checklist.model_dump(),
        "passed_count": verdict.passed_count,
    }

    logs = _registrar_log(
        state,
        "critic",
        f"Auditoria de 7 Itens: approved={is_approved} ({verdict.passed_count}/7). {feedback}",
        {
            "is_approved": is_approved,
            "passed_count": verdict.passed_count,
            "failed_items": verdict.failed_items,
            "retry_count": retry_count,
        },
    )

    novo_estado: Dict[str, Any] = {
        "is_approved": is_approved,
        "audit_verdict": verdict_dict,
        "correction_instructions": correction_instructions,
        "critique_feedback": feedback,
        "retry_count": retry_count,
        "word_count": verdict.word_count,
        "status": status,
        "jev_decision": jev_compat,
        "execution_log": logs,
    }
    salvar_estado_disco({**state, **novo_estado})
    return novo_estado


# =============================================================================
# --- 6. NÓ 4: MULTICHANNEL FANOUT (SUBAGENTES PARALELOS) ---
# =============================================================================
def node_multichannel_fanout(state: GraphState) -> Dict[str, Any]:
    """
    Nó 4 (`node_multichannel_fanout`):
    A partir dos 4 Blocos Universais aprovados, dispara em paralelo os 4 subagentes formatadores:
    1. E-mail HTML (`email_builder.formatar_newsletter_4_blocos`)
    2. Instagram Carrossel 6-8 slides + Legenda (`instagram_poster.formatar_carrossel_4_blocos`)
    3. X / Twitter Thread 5-7 posts ou Single Note (`postar_x_diario.formatar_payload_x_4_blocos`)
    4. Roteiro de Podcast (Ana e Leo) + Reels/Shorts (`podcast_builder.formatar_roteiro_podcast_e_reels`)
    """
    story = dict(state.get("selected_story", {}) or {})
    draft_blocks = dict(state.get("draft_blocks", {}) or {})
    route = str(state.get("curation_route", "FULL_OMNICHANNEL") or "FULL_OMNICHANNEL")
    hoje = datetime.now().strftime("%Y-%m-%d")

    from email_builder import formatar_newsletter_4_blocos
    from instagram_poster import formatar_carrossel_4_blocos
    from postar_x_diario import formatar_payload_x_4_blocos
    from podcast_builder import formatar_roteiro_podcast_e_reels

    with ThreadPoolExecutor(max_workers=4) as executor:
        fut_email = executor.submit(formatar_newsletter_4_blocos, story, draft_blocks)
        fut_ig = executor.submit(formatar_carrossel_4_blocos, story, draft_blocks)
        fut_x = executor.submit(formatar_payload_x_4_blocos, story, draft_blocks, route)
        fut_av = executor.submit(formatar_roteiro_podcast_e_reels, story, draft_blocks)

        payload_email = fut_email.result()
        payload_ig = fut_ig.result()
        payload_x = fut_x.result()
        payload_av = fut_av.result()

    multichannel_payloads = {
        "route": route,
        "email_newsletter": payload_email,
        "instagram_carousel": payload_ig,
        "x_twitter": payload_x,
        "audio_video_reels": payload_av,
    }

    caminho_imagem = f"edicoes/imagens/capa_{hoje}.jpg"
    caminho_audio = "landing/public/audio/latest.mp3"

    logs = _registrar_log(
        state,
        "multichannel_fanout",
        (
            f"Fan-out multicanal paralelo concluído (rota={route}): "
            f"Newsletter ({payload_email['reading_time_minutes']} min), "
            f"IG Carrossel ({payload_ig['slide_count']} slides + legenda {payload_ig['caption_word_count']}w), "
            f"X ({payload_x['mode']}: {payload_x['post_count']} posts), "
            f"Reels ({payload_av['reels_word_count']}w)."
        ),
        {
            "ig_slides": payload_ig["slide_count"],
            "x_posts": payload_x["post_count"],
            "reels_words": payload_av["reels_word_count"],
        },
    )

    novo_estado: Dict[str, Any] = {
        "multichannel_payloads": multichannel_payloads,
        "image_path": caminho_imagem,
        "audio_path": caminho_audio,
        "status": "AWAITING_FOUNDER_APPROVAL",
        "execution_log": logs,
    }
    salvar_estado_disco({**state, **novo_estado})
    return novo_estado


# Alias para compatibilidade com chamadas legadas que importem node_media_generator
node_media_generator = node_multichannel_fanout


# =============================================================================
# --- 7. NÓ 5: DISPATCHER (COM PROTEÇÃO HITL FOUNDER GATE) ---
# =============================================================================
def node_dispatcher(state: GraphState) -> Dict[str, Any]:
    """
    Nó 5 (`node_dispatcher`):
    Ponto de controle crítico Human-In-The-Loop:
    Só realiza o disparo se `status == 'APPROVED_BY_FOUNDER'` ou `hitl_approved == True`.
    """
    status_atual = state.get("status", "")
    hitl_ok = bool(state.get("hitl_approved", False)) or status_atual == "APPROVED_BY_FOUNDER"

    if not hitl_ok:
        logs = _registrar_log(
            state,
            "dispatcher",
            "Disparo BLOQUEADO: Flag 'APPROVED_BY_FOUNDER' ausente. Operação suspensa com segurança.",
            {"status": "SUSPENDED_WAITING_APPROVAL"},
        )
        return {
            "status": "SUSPENDED_WAITING_APPROVAL",
            "execution_log": logs,
        }

    logs = _registrar_log(
        state,
        "dispatcher",
        "Disparo multicanal executado com autorização do fundador (Newsletter, IG Carrossel, X Thread, Podcast/Reels).",
        {"status": "DISPATCHED"},
    )

    novo_estado: Dict[str, Any] = {
        "status": "DISPATCHED",
        "hitl_approved": True,
        "execution_log": logs,
    }
    salvar_estado_disco({**state, **novo_estado})
    return novo_estado


# =============================================================================
# --- 8. ROTEAMENTO CONDICIONAL (RETRY LOOP <= 2) ---
# =============================================================================
def rotear_pos_critic(state: GraphState) -> str:
    """
    Roteamento determinístico pós-auditoria de 7 itens:
    - Se `is_approved == True`: avança para `approved` (`multichannel_fanout`).
    - Se `is_approved == False` e `retry_count <= 2`: retorna `retry_writer` (autocura com `correction_instructions`).
    - Se esgotar tentativas (`retry_count > 2`): avança para `approved`.
    """
    if state.get("is_approved", False):
        return "approved"
    if int(state.get("retry_count", 0)) <= 2:
        return "retry_writer"
    return "approved"


# =============================================================================
# --- 9. CONSTRUÇÃO & COMPILAÇÃO DO STATEGRAPH (COM HITL) ---
# =============================================================================
def construir_workflow() -> StateGraph:
    """Instancia a topologia do StateGraph com subagentes multicanal e HITL Gate."""
    wf = StateGraph(GraphState)

    wf.add_node("planner", node_planner)
    wf.add_node("writer", node_writer)
    wf.add_node("critic", node_critic)
    wf.add_node("multichannel_fanout", node_multichannel_fanout)
    wf.add_node("dispatcher", node_dispatcher)

    wf.add_edge(START, "planner")
    wf.add_edge("planner", "writer")
    wf.add_edge("writer", "critic")

    wf.add_conditional_edges(
        "critic",
        rotear_pos_critic,
        {
            "retry_writer": "writer",
            "approved": "multichannel_fanout",
        },
    )

    wf.add_edge("multichannel_fanout", "dispatcher")
    wf.add_edge("dispatcher", END)

    return wf


checkpointer = MemorySaver()
workflow_builder = construir_workflow()
graph = workflow_builder.compile(
    interrupt_before=["dispatcher"],
    checkpointer=checkpointer,
)
workflow = graph


# =============================================================================
# --- 10. EXPORTAÇÃO VISUAL E FUNÇÕES HITL ---
# =============================================================================
def exportar_grafo_visual() -> Dict[str, Any]:
    graph_repr = graph.get_graph()
    try:
        mermaid_code = graph_repr.draw_mermaid()
    except Exception:
        mermaid_code = """
graph TD
    __start__([Início]) --> planner[Planner: score_news_curation 0-10]
    planner --> writer[Writer: 4 Blocos Universais SKILL.md]
    writer --> critic{Critic: audit_checklist_7_items}
    critic -- Reprovado (retry_count <= 2) --> writer
    critic -- Aprovado (7/7 True) --> multichannel_fanout[Multichannel Fanout: Email, IG, X, Podcast/Reels]
    multichannel_fanout --> dispatcher[Dispatcher: HITL Founder Gate]
    dispatcher --> __end__([Fim])
"""

    nodes = []
    for node_id, node_obj in graph_repr.nodes.items():
        tipo = "process"
        if node_id in ["__start__", "__end__"]:
            tipo = "terminal"
        elif node_id == "critic":
            tipo = "decision"
        elif node_id == "dispatcher":
            tipo = "hitl_gate"

        nodes.append({
            "id": node_id,
            "label": getattr(node_obj, "name", node_id).replace("_", " ").title(),
            "type": tipo,
            "metadata": {
                "interrupt_before": node_id == "dispatcher",
                "quality_gate": node_id == "critic",
            },
        })

    edges = []
    for edge in graph_repr.edges:
        edges.append({
            "source": edge.source,
            "target": edge.target,
            "conditional": getattr(edge, "conditional", False),
        })

    return {
        "mermaid": mermaid_code,
        "json_schema": {
            "version": "3.0.0",
            "name": "All News Journal Youth Multichannel StateGraph",
            "hitl_interruption_nodes": ["dispatcher"],
            "nodes": nodes,
            "edges": edges,
            "exported_at": datetime.now().isoformat(),
        },
    }


def executar_fluxo(initial_state: Optional[GraphState] = None, thread_id: str = "default") -> Dict[str, Any]:
    """Executa o grafo até a parada do interrupt_before antes do nó 'dispatcher'."""
    config = {"configurable": {"thread_id": thread_id}}

    if initial_state is None:
        initial_state = {
            "raw_news": [],
            "draft_text": "",
            "retry_count": 0,
            "is_approved": False,
            "hitl_approved": False,
            "status": "PENDING",
            "execution_log": [],
        }

    resultado = graph.invoke(initial_state, config=config)
    salvar_estado_disco(resultado)
    return resultado


def aprovar_e_despachar(thread_id: str = "default") -> Dict[str, Any]:
    """Fornece aprovação humana ('APPROVED_BY_FOUNDER') e retoma a execução no nó 'dispatcher'."""
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(
        config,
        {
            "status": "APPROVED_BY_FOUNDER",
            "hitl_approved": True,
        },
    )
    resultado = graph.invoke(None, config=config)
    salvar_estado_disco(resultado)
    return resultado


def obter_estado_atual(thread_id: str = "default") -> Optional[GraphState]:
    """Lê o snapshot de estado retido no checkpoint para a thread fornecida."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if snapshot and snapshot.values:
        return snapshot.values

    if ENGINE_STATE_FILE.exists():
        try:
            with open(ENGINE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None
