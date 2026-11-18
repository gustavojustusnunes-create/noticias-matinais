"""
core/jev_gatekeeper.py — Curador 0-10 & Gatekeeper de 7 Itens (Pydantic Structured Outputs + Gemini 2.5 Flash)
All News Journal (v3.0 — Manual Editorial Jovem Multicanal 18-30 anos)

Implementa:
1. score_news_curation(raw_news: dict) -> CurationDecision (Matriz 0 a 10 + Lista Negra):
   - Avalia de 0 a 2 pontos cada um dos 5 critérios editoriais:
     (1) Impacto no Bolso/Carreira, (2) Fator Conversa/Dark Social, (3) Utilidade Prática,
     (4) Novidade/Sinal de Futuro, (5) Potencial Visual/Narrativo.
   - Roteamento determinístico:
     * Score >= 8 -> "FULL_OMNICHANNEL"
     * Score 6 ou 7 -> "SHORT_NOTE"
     * Score < 6 ou Lista Negra -> "DISCARD"
2. audit_checklist_7_items(draft: dict, channel_specs: dict) -> AuditVerdict (Quality Gate):
   - Valida rigorosamente os 7 itens booleanos pré-publicação:
     (1) fonte_validada, (2) teste_3_segundos, (3) teste_e_dai, (4) limpeza_jargoes,
     (5) contagem_palavras, (6) reducao_ansiedade, (7) gatilho_comunidade.
   - Retorna approved (bool) e correction_instructions cirúrgicas para o loop de autocura (retry_count <= 2).
3. Compatibilidade retroativa completa com evaluate_editorial_quality, auditar_resumo_critic e quick_triage_supervisor.
"""

import os
import re
import time
import json
from pathlib import Path
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# --- 0. MIXIN DICT-COMPATÍVEL PARA PYDANTIC SCHEMAS ---
# =============================================================================
class DictCompatibleModel(BaseModel):
    """Permite acesso tanto por atributo (obj.campo) quanto por chave (obj['campo'] / obj.get('campo'))."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def keys(self):
        return self.__class__.model_fields.keys()


# =============================================================================
# --- 1. SCHEMAS PYDANTIC DO NOVO MANUAL EDITORIAL JOVEM (ETAPA 2) ---
# =============================================================================

class FourBlockDraft(DictCompatibleModel):
    """Anatomia Obrigatória de 4 Blocos Universais definida em skills/editorial_jovem/SKILL.md."""
    titulo_jovem: str = Field(
        default="",
        description="Título direto em voz ativa (máx. 12 palavras) focado no interesse de jovens de 18-30 anos."
    )
    bloco_1_gancho: str = Field(
        description="1 frase curta e magnética (máx. 15 palavras) que toca na dor, bolso ou curiosidade imediata do jovem."
    )
    bloco_2_fato: str = Field(
        description="Explicação limpa com dados exatos (quem, o quê, quanto, quando), fonte de Camada 1 e tradução imediata de qualquer sigla/jargão na mesma frase usando analogia cotidiana."
    )
    bloco_3_e_dai: str = Field(
        description="Tradução prática direta: como esse fato afeta o bolso, a carreira, as compras ou a rotina do jovem."
    )
    bloco_4_fechamento: str = Field(
        description="Pergunta aberta instigante terminada em '?' para estimular comentários e envio no Direct/WhatsApp."
    )


class CurationCriteriaScores(DictCompatibleModel):
    """Pontuação de 0 a 2 para cada um dos 5 critérios da Matriz de Curadoria."""
    impacto_bolso_carreira: int = Field(ge=0, le=2, description="0 a 2: Afeta salário, emprego, juros, impostos ou bolso?")
    fator_conversa_dark_social: int = Field(ge=0, le=2, description="0 a 2: Gera compartilhamento no WhatsApp/Direct?")
    utilidade_pratica: int = Field(ge=0, le=2, description="0 a 2: Ajuda o jovem a tomar uma decisão prática hoje?")
    novidade_sinal_futuro: int = Field(ge=0, le=2, description="0 a 2: Traz tendência de IA, tecnologia, ciência ou carreira?")
    potencial_visual_narrativo: int = Field(ge=0, le=2, description="0 a 2: Rende bons slides de carrossel e gancho de Reels?")


class CurationDecision(DictCompatibleModel):
    """Resultado estruturado da função score_news_curation (Matriz 0 a 10)."""
    is_blacklisted: bool = Field(
        description="True se cair na Lista Negra (policial sangrento, política burocrática sem efeito prático, fofoca vazia)."
    )
    blacklist_reason: str = Field(
        default="",
        description="Motivo do descarte imediato caso is_blacklisted seja True."
    )
    criteria_scores: CurationCriteriaScores = Field(
        description="Notas individuais (0 a 2) nos 5 critérios da Matriz Editorial."
    )
    total_score: int = Field(
        ge=0, le=10,
        description="Soma total dos 5 critérios (0 a 10). Se is_blacklisted=True, total_score=0."
    )
    route: Literal["FULL_OMNICHANNEL", "SHORT_NOTE", "DISCARD"] = Field(
        description="FULL_OMNICHANNEL (score >= 8), SHORT_NOTE (score 6 ou 7), DISCARD (score < 6 ou blacklisted)."
    )
    editorial_Justification: str = Field(
        default="",
        description="Justificativa sintética da nota e do roteamento atribuído."
    )
    latency_ms: float = Field(default=0.0, description="Latência da avaliação em milissegundos.")
    model: str = Field(default="gemini-2.5-flash", description="Modelo que executou a curadoria.")


class Checklist7Items(DictCompatibleModel):
    """Os 7 itens booleanos obrigatórios do Quality Gate pré-publicação."""
    fonte_validada: bool = Field(
        description="1. Possui fonte da Camada 1 (ou órgão oficial) e números/dados exatos?"
    )
    teste_3_segundos: bool = Field(
        description="2. O gancho inicial (bloco_1_gancho) tem até 15 palavras e gera curiosidade imediata?"
    )
    teste_e_dai: bool = Field(
        description="3. Explica claramente o impacto prático no bolso, carreira ou rotina do jovem (bloco_3_e_dai)?"
    )
    limpeza_jargoes: bool = Field(
        description="4. Todas as siglas e termos técnicos têm analogia prática do cotidiano na mesma frase?"
    )
    contagem_palavras: bool = Field(
        description="5. Respeita o limite estrito de palavras e frases curtas (máx. 15-20 palavras por frase base)?"
    )
    reducao_ansiedade: bool = Field(
        description="6. Evita catastrofismo/alarmismo e traz visão racional e prática?"
    )
    gatilho_comunidade: bool = Field(
        description="7. Termina com pergunta aberta engajadora no bloco_4_fechamento ('?')?"
    )


class AuditVerdict(DictCompatibleModel):
    """Resultado estruturado da função audit_checklist_7_items (Quality Gate de 7 Itens)."""
    approved: bool = Field(
        description="True SOMENTE se todos os 7 itens de checklist forem True."
    )
    checklist: Checklist7Items = Field(
        description="Mapa booleano dos 7 critérios auditados."
    )
    passed_count: int = Field(
        ge=0, le=7,
        description="Quantidade de itens aprovados (de 0 a 7)."
    )
    failed_items: List[str] = Field(
        default_factory=list,
        description="Lista com os nomes das chaves que falharam (valor False)."
    )
    correction_instructions: str = Field(
        default="",
        description="Instruções detalhadas apontando exatamente qual bloco/frase o Writer deve reescrever no loop de retry."
    )
    word_count: int = Field(default=0, description="Contagem total de palavras dos 4 blocos somados.")
    gancho_word_count: int = Field(default=0, description="Contagem de palavras do bloco_1_gancho.")
    max_core_sentence_words: int = Field(default=0, description="Maior extensão de frase base encontrada.")
    latency_ms: float = Field(default=0.0, description="Latência da auditoria em milissegundos.")
    model: str = Field(default="gemini-2.5-flash", description="Modelo auditor.")


# =============================================================================
# --- 2. FUNÇÃO DE CURADORIA: score_news_curation (MATRIZ 0 A 10) ---
# =============================================================================

BLACKLIST_PATTERNS = [
    (r'\b(homic[íi]dio|assassinato|chacina|esquartejad[oa]|tiroteio sangrento|latroc[íi]nio|cad[áa]ver|estupro)\b',
     "Tema policial sangrento / violência gráfica (vedado pela Lista Negra)."),
    (r'\b(subcelebridade|ex-bbb flagrad[oa]|barraco em festa|trai[çc][ãa]o de famoso|look de praia)\b',
     "Fofoca vazia de subcelebridade sem impacto econômico ou cultural (Lista Negra)."),
    (r'\b(sess[ãa]o solene|homenagem formal na c[âa]mara|comiss[ãa]o especial sem vota[çc][ãa]o|disputa de diretório partid[áa]rio)\b',
     "Política burocrática partidária sem efeito prático na rotina do jovem (Lista Negra)."),
]

HIGH_IMPACT_ECONOMY_PATTERNS = [
    r'\b(bolso|juros|selic|infla[çc][ãa]o|imposto|cbs|iva|sal[áa]rio|emprego|vagas|carreira|aluguel|cr[ée]dito|pix|cart[ãa]o|fintech|picpay|nubank|investimento|a[çc][õo]es|bolsa|d[óo]lar|renda|cashback|mei| imposto de renda)\b'
]

FUTURE_SIGNAL_PATTERNS = [
    r'\b(ia|intelig[êe]ncia artificial|openai|gemini|claude|chip|semicondutor|rob[ôo]|automa[çc][ãa]o|energia limpa|biotecnologia|startup|ci[êe]ncia|nasa|webb|bateria|el[ée]trico|algoritmo|app|aplicativo|streaming)\b'
]


def _determinar_rota_por_score(total_score: int, is_blacklisted: bool) -> Literal["FULL_OMNICHANNEL", "SHORT_NOTE", "DISCARD"]:
    if is_blacklisted or total_score < 6:
        return "DISCARD"
    if total_score >= 8:
        return "FULL_OMNICHANNEL"
    return "SHORT_NOTE"


def _local_score_news_curation(raw_news: Dict[str, Any], t_start: float) -> CurationDecision:
    """Avaliador determinístico local da Matriz 0 a 10 + Lista Negra."""
    titulo = str(raw_news.get("titulo", "") or "")
    resumo = str(raw_news.get("resumo", "") or raw_news.get("descricao", "") or "")
    caderno = str(raw_news.get("caderno", "") or raw_news.get("tema", "") or "")
    texto_completo = f"{titulo} {resumo} {caderno}".lower()

    # 1. Verificação estrita da Lista Negra
    for pattern, reason in BLACKLIST_PATTERNS:
        if re.search(pattern, texto_completo, re.IGNORECASE):
            scores = CurationCriteriaScores(
                impacto_bolso_carreira=0,
                fator_conversa_dark_social=0,
                utilidade_pratica=0,
                novidade_sinal_futuro=0,
                potencial_visual_narrativo=0,
            )
            return CurationDecision(
                is_blacklisted=True,
                blacklist_reason=reason,
                criteria_scores=scores,
                total_score=0,
                route="DISCARD",
                editorial_Justification=f"Descartado preventivamente pela Lista Negra: {reason}",
                latency_ms=round((time.perf_counter() - t_start) * 1000, 2),
                model="local-deterministic-curation-v3",
            )

    # 2. Pontuação analítica dos 5 critérios (0 a 2 cada)
    has_numbers = bool(re.search(r'(\d+[\.,]?\d*\s*(%|bilh|milh|mil|r\$|us\$|pontos|anos|dias))', texto_completo))
    econ_matches = len(re.findall(HIGH_IMPACT_ECONOMY_PATTERNS[0], texto_completo, re.IGNORECASE))
    future_matches = len(re.findall(FUTURE_SIGNAL_PATTERNS[0], texto_completo, re.IGNORECASE))

    # Critério 1: Impacto no Bolso/Carreira (0-2)
    if econ_matches >= 2 or (econ_matches >= 1 and has_numbers):
        c1 = 2
    elif econ_matches == 1 or any(k in caderno.lower() for k in ["economia", "mercado", "negócios", "finanças"]):
        c1 = 1
    else:
        c1 = 1 if len(resumo.split()) > 25 else 0

    # Critério 2: Fator Conversa / Dark Social (0-2)
    if econ_matches >= 1 or future_matches >= 1 or has_numbers:
        c2 = 2 if (has_numbers and (econ_matches + future_matches >= 2)) else 1
    else:
        c2 = 1 if len(titulo) > 20 else 0

    # Critério 3: Utilidade Prática (0-2)
    if econ_matches >= 1 and has_numbers:
        c3 = 2
    elif econ_matches >= 1 or future_matches >= 1 or has_numbers:
        c3 = 1
    else:
        c3 = 0

    # Critério 4: Novidade / Sinal de Futuro (0-2)
    if future_matches >= 2 or (future_matches >= 1 and has_numbers):
        c4 = 2
    elif future_matches == 1 or any(k in caderno.lower() for k in ["ia", "tecnologia", "ciência", "inovação"]):
        c4 = 2
    else:
        c4 = 1

    # Critério 5: Potencial Visual / Narrativo (0-2)
    if has_numbers and len(resumo.split()) >= 15:
        c5 = 2
    elif len(resumo.split()) >= 10 or bool(raw_news.get("imagem") or raw_news.get("url_imagem")):
        c5 = 1
    else:
        c5 = 1 if has_numbers else 0

    total = min(10, c1 + c2 + c3 + c4 + c5)
    route = _determinar_rota_por_score(total, False)

    scores = CurationCriteriaScores(
        impacto_bolso_carreira=c1,
        fator_conversa_dark_social=c2,
        utilidade_pratica=c3,
        novidade_sinal_futuro=c4,
        potencial_visual_narrativo=c5,
    )

    return CurationDecision(
        is_blacklisted=False,
        blacklist_reason="",
        criteria_scores=scores,
        total_score=total,
        route=route,
        editorial_Justification=(
            f"Score {total}/10 -> Rota {route} "
            f"(Bolso={c1}, Conversa={c2}, Utilidade={c3}, Futuro={c4}, Visual={c5})."
        ),
        latency_ms=round((time.perf_counter() - t_start) * 1000, 2),
        model="local-deterministic-curation-v3",
    )


def score_news_curation(raw_news: Dict[str, Any], use_llm: bool = True) -> CurationDecision:
    """
    Avalia uma notícia bruta segundo a Matriz de Curadoria 0 a 10 do Manual Editorial Jovem:
    - Verifica Lista Negra (policial sangrento, política burocrática sem efeito prático, fofoca vazia).
    - Pontua de 0 a 2 cada um dos 5 critérios (Bolso/Carreira, Conversa/Dark Social,
      Utilidade Prática, Sinal de Futuro, Potencial Visual/Narrativo).
    - Define route:
      * Score >= 8: "FULL_OMNICHANNEL"
      * Score 6 ou 7: "SHORT_NOTE"
      * Score < 6 ou Lista Negra: "DISCARD"
    """
    t_start = time.perf_counter()

    # Filtro rápido de Lista Negra antes mesmo de chamar LLM para economizar tokens
    local_pre = _local_score_news_curation(raw_news, t_start)
    if local_pre.is_blacklisted:
        return local_pre

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if use_llm and gemini_key:
        prompt = (
            "Você é o Curador-Chefe do All News Journal para o público jovem (18 a 30 anos).\n"
            "Avalie a notícia abaixo de acordo com a Matriz de Curadoria 0 a 10:\n"
            "1. Verifique se o tema cai na Lista Negra: policial sangrento/violência gráfica, "
            "política burocrática sem efeito prático na vida real, ou fofoca vazia. Se sim, marque is_blacklisted=True, total_score=0 e route='DISCARD'.\n"
            "2. Caso contrário, avalie de 0 a 2 pontos cada um dos 5 critérios:\n"
            "   - impacto_bolso_carreira (0-2)\n"
            "   - fator_conversa_dark_social (0-2)\n"
            "   - utilidade_pratica (0-2)\n"
            "   - novidade_sinal_futuro (0-2)\n"
            "   - potencial_visual_narrativo (0-2)\n"
            "3. Calcule total_score (soma de 0 a 10) e defina route:\n"
            "   - total_score >= 8: 'FULL_OMNICHANNEL'\n"
            "   - total_score 6 ou 7: 'SHORT_NOTE'\n"
            "   - total_score < 6: 'DISCARD'\n\n"
            f"NOTÍCIA BRUTA:\n{json.dumps(raw_news, ensure_ascii=False)}"
        )
        llm_res = _call_gemini_structured(prompt, CurationDecision, temperature=0.1)
        if llm_res is not None:
            # Garante consistência matemática da soma e da regra de roteamento
            s = llm_res.criteria_scores
            soma = 0 if llm_res.is_blacklisted else (
                s.impacto_bolso_carreira
                + s.fator_conversa_dark_social
                + s.utilidade_pratica
                + s.novidade_sinal_futuro
                + s.potencial_visual_narrativo
            )
            llm_res.total_score = soma
            llm_res.route = _determinar_rota_por_score(soma, llm_res.is_blacklisted)
            llm_res.latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            llm_res.model = "gemini-2.5-flash"
            return llm_res

    return local_pre


# =============================================================================
# --- 3. QUALITY GATE: audit_checklist_7_items (OS 7 ITENS BOOLEANOS) ---
# =============================================================================

# Siglas e jargões técnicos/econômicos que EXIGEM analogia prática na mesma frase
JARGON_TERMS_REQUIRING_ANALOGY = [
    ("cbs", "CBS (Contribuição sobre Bens e Serviços)"),
    ("ibs", "IBS (Imposto sobre Bens e Serviços)"),
    ("selic", "Selic"),
    ("ipca", "IPCA"),
    ("igp-m", "IGP-M"),
    ("ebitda", "EBITDA"),
    ("lajida", "LAJIDA"),
    ("capex", "Capex"),
    ("opex", "Opex"),
    ("ipo", "IPO"),
    ("follow-on", "Follow-on"),
    ("spread", "Spread bancário"),
    ("valuation", "Valuation"),
    ("copom", "Copom"),
    ("p/l", "P/L (Preço sobre Lucro)"),
    ("fii", "FII (Fundo Imobiliário)"),
    ("cdb", "CDB"),
    ("drex", "Drex"),
    ("arcabouço fiscal", "Arcabouço Fiscal"),
    ("resultado primário", "Resultado Primário"),
    ("déficit primário", "Déficit Primário"),
    ("superávit primário", "Superávit Primário"),
    ("default", "Default"),
    ("hawkish", "Hawkish"),
    ("dovish", "Dovish"),
]

ANALOGY_MARKERS_REGEX = re.compile(
    r'(\([^)]{8,}\)|—[^—]{8,}|-\s+como\s+|funciona como|ou seja|isto é|na prática|'
    r'espécie de|que é o|que é a|que serve como|como se fosse|basicamente|'
    r'taxa embutida|imposto único|pedacinho|juro base|diferença entre|'
    r'termômetro|régua|aluguel do dinheiro|caixa da empresa|estreia na bolsa)',
    re.IGNORECASE
)

CATASTROPHIST_PATTERNS = [
    r'\b(colapso total|fim do mundo|destrui[çc][ãa]o irrevers[íi]vel|p[âa]nico generalizado|'
    r'trag[ée]dia econ[ôo]mica sem precedentes|voc[êe] vai perder tudo|caos absoluto|apocalipse)\b'
]

LAYER1_SOURCES_REGEX = re.compile(
    r'\b(reuters|bloomberg|financial times|ft|valor|banco central|bc|ibge|fgv|cvm|sec|'
    r'receita federal|minist[ée]rio da fazenda|tesouro nacional|g1|bbc|estad[ãa]o|folha|nasdaq|nyse|b3|relat[óo]rio|balan[çc]o)\b',
    re.IGNORECASE
)

PRACTICAL_IMPACT_REGEX = re.compile(
    r'\b(seu bolso|sua carreira|sua rotina|sua conta|seu cart[ãa]o|seu sal[áa]rio|seu aluguel|'
    r'suas compras|seu dinheiro|para voc[êe]|na pr[áa]tica|quem investe|quem trabalha|'
    r'quem usa|consumidor|jovem|profissional|or[çc]amento|rendimento|cashback|parcela|financiamento|pre[çc]o)\b',
    re.IGNORECASE
)


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    # Divide por ponto final, exclamação ou interrogação seguidos de espaço ou fim
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def _core_word_count_without_parenthetical_analogy(sentence: str) -> int:
    """
    Calcula o número de palavras da oração principal descontando o parêntese explicativo
    da analogia obrigatória, para que a tradução de jargão na mesma frase não penalize a métrica de frase curta.
    """
    cleaned = re.sub(r'\([^)]*\)', '', sentence)
    cleaned = re.sub(r'—[^—]*—', '', cleaned)
    words = [w for w in cleaned.strip().split() if w]
    return len(words)


def _detect_unexplained_jargons(full_text: str) -> List[str]:
    """
    Verifica frase por frase se alguma sigla ou jargão técnico aparece sem uma analogia/explicação
    prática na mesma frase.
    """
    unexplained = []
    sentences = _split_sentences(full_text)
    for sent in sentences:
        sent_lower = sent.lower()
        for term_key, term_label in JARGON_TERMS_REQUIRING_ANALOGY:
            pattern = rf'(?<![a-zA-Z0-9]){re.escape(term_key)}(?![a-zA-Z0-9])'
            if re.search(pattern, sent_lower):
                if not ANALOGY_MARKERS_REGEX.search(sent):
                    unexplained.append(f"'{term_label}' na frase: \"{sent}\"")
    return unexplained


def _local_audit_checklist_7_items(
    draft: Dict[str, Any],
    channel_specs: Optional[Dict[str, Any]],
    t_start: float
) -> AuditVerdict:
    """Validador determinístico rigoroso dos 7 itens do Quality Gate."""
    gancho = str(draft.get("bloco_1_gancho", "") or "").strip()
    fato = str(draft.get("bloco_2_fato", "") or "").strip()
    e_dai = str(draft.get("bloco_3_e_dai", "") or "").strip()
    fechamento = str(draft.get("bloco_4_fechamento", "") or "").strip()

    # Se vier apenas texto corrido legado sem os 4 blocos, tenta fatiar mas sinaliza se faltar estrutura
    full_text = " ".join([p for p in [gancho, fato, e_dai, fechamento] if p]).strip()
    if not full_text and draft.get("draft_text"):
        full_text = str(draft.get("draft_text", "")).strip()

    total_words = len(full_text.split())
    gancho_words = len(gancho.split()) if gancho else 999

    corrections: List[str] = []

    # 1. fonte_validada: Possui fonte da Camada 1/órgão oficial e números exatos no bloco_2_fato?
    has_source = bool(LAYER1_SOURCES_REGEX.search(fato or full_text))
    has_exact_numbers = bool(re.search(r'\d+', fato or full_text))
    item_1_fonte = bool(fato and has_source and has_exact_numbers)
    if not item_1_fonte:
        corrections.append(
            "[bloco_2_fato] Inclua explicitamente a fonte de Camada 1 (ex.: Reuters, Bloomberg, IBGE, Banco Central, Receita Federal, Valor) e números exatos do fato."
        )

    # 2. teste_3_segundos: Gancho inicial presente, magnético e com no máximo 15 palavras?
    item_2_gancho = bool(gancho and 4 <= gancho_words <= 15)
    if not item_2_gancho:
        corrections.append(
            f"[bloco_1_gancho] Reescreva o gancho em 1 única frase magnética de no máximo 15 palavras (atual: {gancho_words if gancho else 0} palavras)."
        )

    # 3. teste_e_dai: Explica claramente o impacto prático no bolso/carreira/rotina do jovem?
    item_3_edai = bool(e_dai and len(e_dai.split()) >= 10 and PRACTICAL_IMPACT_REGEX.search(e_dai))
    if not item_3_edai:
        corrections.append(
            "[bloco_3_e_dai] Reescreva o Bloco 3 explicando diretamente como isso afeta o bolso, o salário, o cartão, a carreira ou as compras do jovem na prática."
        )

    # 4. limpeza_jargoes: Todas as siglas/termos técnicos têm analogia prática na mesma frase?
    unexplained_jargons = _detect_unexplained_jargons(full_text)
    item_4_jargoes = len(unexplained_jargons) == 0 and len(full_text) > 0
    if not item_4_jargoes:
        corrections.append(
            "[limpeza_jargoes] Traduza imediatamente na mesma frase (entre parênteses com analogia do cotidiano) os seguintes termos técnicos: "
            + "; ".join(unexplained_jargons)
        )

    # 5. contagem_palavras: Limite de palavras total (55 a 145) e frases base curtas (máx 20 palavras por oração base)
    all_sentences = (
        _split_sentences(gancho)
        + _split_sentences(fato)
        + _split_sentences(e_dai)
        + _split_sentences(fechamento)
    )
    core_lengths = [_core_word_count_without_parenthetical_analogy(s) for s in all_sentences] if all_sentences else [99]
    max_core_sent = max(core_lengths) if core_lengths else 99
    max_allowed_sent = int((channel_specs or {}).get("max_sentence_words", 20))
    min_total_words = int((channel_specs or {}).get("min_total_words", 55))
    max_total_words = int((channel_specs or {}).get("max_total_words", 145))

    item_5_palavras = (min_total_words <= total_words <= max_total_words) and (max_core_sent <= max_allowed_sent)
    if not item_5_palavras:
        if not (min_total_words <= total_words <= max_total_words):
            corrections.append(
                f"[contagem_palavras] Ajuste o volume total dos 4 blocos para entre {min_total_words} e {max_total_words} palavras (atual: {total_words} palavras)."
            )
        if max_core_sent > max_allowed_sent:
            long_sents = [s for s in all_sentences if _core_word_count_without_parenthetical_analogy(s) > max_allowed_sent]
            exemplo_longa = long_sents[0] if long_sents else ""
            corrections.append(
                f"[contagem_palavras] Encurte as frases para no máximo {max_allowed_sent} palavras na oração principal (maior encontrada: {max_core_sent} palavras na frase: \"{exemplo_longa}\"). Use voz ativa Sujeito + Verbo + Complemento."
            )

    # 6. reducao_ansiedade: Evita catastrofismo e traz visão racional/prática?
    has_catastrophism = any(re.search(p, full_text, re.IGNORECASE) for p in CATASTROPHIST_PATTERNS)
    item_6_ansiedade = (not has_catastrophism) and len(full_text) > 0
    if not item_6_ansiedade:
        corrections.append(
            "[reducao_ansiedade] Remova expressões alarmistas ou apocalípticas; mantenha tom calmo, analítico e focado em decisão prática."
        )

    # 7. gatilho_comunidade: Termina com pergunta aberta engajadora no bloco_4_fechamento?
    fechamento_words = len(fechamento.split()) if fechamento else 0
    item_7_comunidade = bool(fechamento and fechamento.endswith("?") and 5 <= fechamento_words <= 22)
    if not item_7_comunidade:
        corrections.append(
            "[bloco_4_fechamento] Finalize com uma pergunta aberta engajadora terminada em '?' (entre 5 e 20 palavras) para estimular comentários e envio no Direct/WhatsApp."
        )

    checklist = Checklist7Items(
        fonte_validada=item_1_fonte,
        teste_3_segundos=item_2_gancho,
        teste_e_dai=item_3_edai,
        limpeza_jargoes=item_4_jargoes,
        contagem_palavras=item_5_palavras,
        reducao_ansiedade=item_6_ansiedade,
        gatilho_comunidade=item_7_comunidade,
    )

    checks_dict = checklist.model_dump()
    failed = [k for k, v in checks_dict.items() if not v]
    passed_count = 7 - len(failed)
    approved = len(failed) == 0

    return AuditVerdict(
        approved=approved,
        checklist=checklist,
        passed_count=passed_count,
        failed_items=failed,
        correction_instructions=" | ".join(corrections) if corrections else "",
        word_count=total_words,
        gancho_word_count=gancho_words if gancho else 0,
        max_core_sentence_words=max_core_sent,
        latency_ms=round((time.perf_counter() - t_start) * 1000, 2),
        model="local-deterministic-gatekeeper-v3",
    )


def audit_checklist_7_items(
    draft: Dict[str, Any],
    channel_specs: Optional[Dict[str, Any]] = None,
    use_llm: bool = True
) -> AuditVerdict:
    """
    Quality Gate oficial do Manual Editorial Jovem Multicanal.
    Valida rigorosamente os 7 itens booleanos pré-publicação:
      1. fonte_validada
      2. teste_3_segundos
      3. teste_e_dai
      4. limpeza_jargoes
      5. contagem_palavras
      6. reducao_ansiedade
      7. gatilho_comunidade
    Se qualquer item for False, retorna approved=False e preenche correction_instructions
    detalhando exatamente qual frase/bloco o Writer deve reescrever no loop de retry (retry_count <= 2).
    """
    t_start = time.perf_counter()
    local_verdict = _local_audit_checklist_7_items(draft, channel_specs, t_start)

    # Se as regras determinísticas já detectaram violação objetiva (ex.: jargão sem analogia,
    # gancho > 15 palavras ou ausência de '?'), retornamos imediatamente com precisão cirúrgica
    if not local_verdict.approved:
        return local_verdict

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if use_llm and gemini_key:
        prompt = (
            "Você é o Auditor de Quality Gate do All News Journal (Manual Editorial Jovem 18-30 anos).\n"
            "Valide rigorosamente os 7 itens booleanos sobre o rascunho de 4 blocos abaixo:\n"
            "1. fonte_validada: Possui fonte da Camada 1 e números exatos no bloco_2_fato?\n"
            "2. teste_3_segundos: O bloco_1_gancho tem até 15 palavras e gera curiosidade imediata?\n"
            "3. teste_e_dai: O bloco_3_e_dai explica claramente o impacto prático no bolso/carreira/rotina do jovem?\n"
            "4. limpeza_jargoes: Todas as siglas/termos técnicos têm analogia prática do cotidiano na mesma frase?\n"
            "5. contagem_palavras: Frases são curtas e diretas em voz ativa?\n"
            "6. reducao_ansiedade: Evita catastrofismo e traz visão racional/prática?\n"
            "7. gatilho_comunidade: O bloco_4_fechamento termina com pergunta aberta engajadora ('?')?\n"
            "Se qualquer item for False, defina approved=False e detalhe em correction_instructions exatamente qual frase reescrever.\n\n"
            f"ESPECIFICAÇÕES DE CANAL: {json.dumps(channel_specs or {}, ensure_ascii=False)}\n"
            f"DRAFT 4 BLOCOS:\n{json.dumps(draft, ensure_ascii=False)}"
        )
        llm_verdict = _call_gemini_structured(prompt, AuditVerdict, temperature=0.1)
        if llm_verdict is not None:
            c_dict = llm_verdict.checklist.model_dump()
            failed = [k for k, v in c_dict.items() if not v]
            llm_verdict.failed_items = failed
            llm_verdict.passed_count = 7 - len(failed)
            llm_verdict.approved = len(failed) == 0
            llm_verdict.word_count = local_verdict.word_count
            llm_verdict.gancho_word_count = local_verdict.gancho_word_count
            llm_verdict.max_core_sentence_words = local_verdict.max_core_sentence_words
            llm_verdict.latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            llm_verdict.model = "gemini-2.5-flash"
            return llm_verdict

    return local_verdict


# =============================================================================
# --- 4. CLIENTE GOOGLE GEMINI STRUCTURED OUTPUTS (gemini-2.5-flash) ---
# =============================================================================

def _call_gemini_structured(prompt: str, schema_cls: Any, temperature: float = 0.1) -> Optional[Any]:
    """
    Executa chamada estruturada ao Google Gemini ('gemini-2.5-flash') usando Pydantic response_schema
    e temperature=0.1. Suporta tanto o SDK 'google-genai' quanto 'google-generativeai'.
    Retorna instância validada de schema_cls ou None em caso de ausência de chave/falha de rede.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key in ("dummy_key", "none"):
        return None

    # 1. Tenta o SDK oficial google-genai (novo)
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=schema_cls,
            ),
        )
        if response and getattr(response, "parsed", None) is not None:
            if isinstance(response.parsed, schema_cls):
                return response.parsed
            if isinstance(response.parsed, dict):
                return schema_cls(**response.parsed)
        if response and getattr(response, "text", None):
            data = json.loads(response.text)
            return schema_cls(**data)
    except Exception:
        pass

    # 2. Fallback para google.generativeai com response_schema / JSON
    try:
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                model = genai_legacy.GenerativeModel(model_name)
                resp = model.generate_content(
                    prompt,
                    generation_config=genai_legacy.types.GenerationConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                    ),
                )
                if resp and resp.text:
                    data = json.loads(resp.text.strip())
                    return schema_cls(**data)
            except Exception:
                continue
    except Exception:
        pass

    return None


# =============================================================================
# --- 5. COMPATIBILIDADE RETROATIVA (SYSTEM 1 LEGADO & SUPERVISOR TRIAGE) ---
# =============================================================================

SYSTEM_PROMPT_CRITIC = """
Você é o Quality Gate do All News Journal. Audite a resenha contra as diretrizes normativas da publicação.
"""


class CriticAuditResult(BaseModel):
    """Esquema de auditoria legado."""
    aprovado: bool = Field(description="True se aprovado nas regras, False se reprovado")
    word_count: int = Field(description="Contagem de palavras do campo resumo_texto")
    motivo_rejeicao: str = Field(default="", description="Motivo detalhado da rejeição se reprovado")
    instrucao_reescrita: str = Field(default="", description="Instrução orientativa para regeneração imediata")


class EditorialDecision(BaseModel):
    """Esquema de decisão editorial legado (System 1)."""
    score: int = Field(ge=1, le=5, description="Nota de qualidade editorial de 1 a 5")
    noul: bool = Field(description="Booleano de integridade: True se ausente de violações/alucinações")
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


def auditar_resumo_critic(resumo_texto: str, usar_llm: bool = False) -> Dict[str, Any]:
    """Mantido para compatibilidade retroativa com testes legados."""
    texto = (resumo_texto or "").strip()
    palavras = texto.split()
    word_count = len(palavras)

    erros = []
    instrucoes = []

    if word_count < 58:
        erros.append(f"Subdimensionado: {word_count} palavras (mínimo obrigatório: 60 palavras).")
        instrucoes.append(f"Expanda a resenha com mais dados substantivos para atingir entre 60 e 90 palavras (atualmente {word_count}).")
    elif word_count > 92:
        erros.append(f"Superdimensionado: {word_count} palavras (teto obrigatório: 90 palavras).")
        instrucoes.append(f"Sintetize a resenha para atingir entre 60 e 90 palavras (atualmente {word_count}).")

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

    if re.search(r'<(?!/?b\b)[^>]+>', texto) or re.search(r'<[^>]*$', texto):
        erros.append("Símbolo HTML quebrado ou tag não autorizada.")
        instrucoes.append("Remova tags HTML quebradas ou não autorizadas (permitido exclusivamente <b> para negrito).")

    termos_proibidos = [
        "você não vai acreditar", "confira a seguir", "veja mais", "clique aqui",
        "imperdível", "surpreendente", "chocante", "fique ligado", "o artigo fala",
        "segundo a publicação",
        "estabelecem uma nova dinâmica competitiva", "nova dinâmica competitiva",
        "impactos substanciais na cadeia operacional", "cadeia operacional",
        "acompanhado de perto por analistas", "acompanhado por analistas"
    ]
    for termo in termos_proibidos:
        if termo in texto.lower():
            erros.append(f"Uso de clichê/chavão vedado: '{termo}'.")
            instrucoes.append(f"Substitua o clichê '{termo}' por fatos concretos, dados numéricos e causalidade estrutural.")
            break

    aprovado = len(erros) == 0
    return {
        "aprovado": aprovado,
        "word_count": word_count,
        "motivo_rejeicao": " | ".join(erros) if erros else "",
        "instrucao_reescrita": " | ".join(instrucoes) if instrucoes else ""
    }


def _local_system1_editorial_evaluate(article_text: str, guidelines: str = "") -> Dict[str, Any]:
    t0 = time.perf_counter()
    texto = (article_text or "").strip()
    blocos = [p.strip() for p in re.split(r'\n\s*\n', texto) if p.strip()]
    if len(blocos) <= 1 and "\n" in texto:
        blocos = [p.strip() for p in texto.split("\n") if p.strip()]
    num_paragrafos = len(blocos) if blocos else 1

    auditoria = auditar_resumo_critic(texto)
    word_count = auditoria["word_count"]
    aprovado = auditoria["aprovado"]
    motivo = auditoria["motivo_rejeicao"]

    if aprovado:
        score, noul, choice, confidence = 5, True, "APPROVE", 0.95
        reason = f"Conforme diretrizes editoriais: {word_count} palavras."
    elif word_count < 45 or word_count > 120 or len(motivo.split(" | ")) >= 3:
        score, noul, choice, confidence = 1, False, "REJECT", 0.92
        reason = f"Rejeitado por desconformidade crítica: {motivo}"
    else:
        score = 3 if (58 <= word_count <= 92) else 2
        noul, choice, confidence = False, "REVISE", 0.88
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

    if encontrou_critico and not any(w in trace_lower for w in ["warn", "warning", "retry_count"]):
        noul, choice, score, confidence = False, "CRITICAL", 1, 0.94
        action = "ALERT_FOUNDER_AND_HALT"
        details = f"Anomalia crítica detectada: ocorrência de {encontrou_critico[0]}."
    elif encontrou_aviso:
        noul, choice, score, confidence = False, "WARNING", 3, 0.86
        action = "MONITOR_AND_RETRY"
        details = f"Aviso de degradação: ocorrência de {encontrou_aviso[0]}."
    elif encontrou_critico:
        noul, choice, score, confidence = False, "CRITICAL", 1, 0.94
        action = "ALERT_FOUNDER_AND_HALT"
        details = f"Anomalia crítica detectada: ocorrência de {encontrou_critico[0]}."
    else:
        noul, choice, score, confidence = True, "HEALTHY", 5, 0.98
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


def evaluate_editorial_quality(article_text: str, guidelines: str = "") -> Dict[str, Any]:
    resultado = _local_system1_editorial_evaluate(article_text, guidelines)
    validado = EditorialDecision(**resultado)
    return validado.model_dump()


def quick_triage_supervisor(log_or_trace: str) -> Dict[str, Any]:
    resultado = _local_system1_supervisor_triage(log_or_trace)
    validado = SupervisorTriage(**resultado)
    return validado.model_dump()
