"""
core/ondemand_state.py — Esquemas de Dados e Tipagem do Pipeline On-Demand
All News Journal (v2.2)

Define os contratos tipados do subgrafo LangGraph para Breaking News e pautas quentes:
- OnDemandState (TypedDict compatível com LangGraph StateGraph)
- Modelos Pydantic v2 para validação e serialização de Dossiê, Rascunho e Status HITL.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    title: str = Field(default="", description="Título da fonte ou matéria")
    url: str = Field(default="", description="URL de referência")
    snippet: str = Field(default="", description="Trecho substantivo extraído")


class ResearchDossier(BaseModel):
    topic: str = Field(description="Pauta bruta pesquisada")
    summary: str = Field(description="Síntese factual consolidada com múltiplos ângulos")
    key_facts: List[str] = Field(default_factory=list, description="Lista de fatos verificáveis")
    sources: List[ResearchSource] = Field(default_factory=list, description="Fontes jornalísticas citadas")
    recommended_theme: str = Field(default="Mundo", description="Caderno temático editorial sugerido")
    search_provider: str = Field(default="tavily", description="Provedor de pesquisa utilizado")


class PostDraft(BaseModel):
    headline: str = Field(description="Manchete principal de alto impacto em serifa")
    keyword: str = Field(description="Palavra-chave curta (1 a 2 palavras) para a máscara tipográfica")
    subtitulo: str = Field(default="", description="Subtítulo ou gancho analítico")
    slides_text: List[str] = Field(description="Blocos de leitura (85 a 105 palavras por slide)")
    caption: str = Field(description="Legenda completa para o Instagram com parágrafos e hashtags")
    image_search_query: str = Field(description="Query semântica otimizada para busca de foto de alta definição")


class OnDemandState(TypedDict, total=False):
    """Estado compartilhado do subgrafo LangGraph para pautas quentes (On-Demand)."""
    task_id: str
    topic_raw: str
    tema: str
    formato: Literal["carrossel", "card_unico"]
    
    # Pesquisa
    dossier: Dict[str, Any]
    
    # Redação
    headline: str
    subtitulo: str
    keyword: str
    slides_text: List[str]
    caption: str
    image_query: str
    
    # Quality Gate (Jev System 1)
    critic_verdict: Dict[str, Any]
    retry_count: int
    is_approved_by_critic: bool
    
    # Mídia
    image_url: Optional[str]
    image_source_info: Optional[str]
    slide_paths: List[str]
    
    # Governança HITL & Watchdog Timer
    hitl_status: Literal[
        "DRAFT_GENERATED",
        "PENDING_APPROVAL",
        "APPROVED_MANUAL",
        "AUTO_APPROVED_TIMEOUT",
        "REJECTED",
        "DISPATCHED",
        "FAILED"
    ]
    created_at: str
    expires_at: str
    dispatched_at: Optional[str]
    dispatch_result: Optional[Dict[str, Any]]
    rejection_reason: Optional[str]
    
    # Auditoria de Execução
    execution_log: List[Dict[str, Any]]
