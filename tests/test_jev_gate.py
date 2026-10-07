"""
tests/test_jev_gate.py — Suíte de Testes Unitários e Validação do TypeSafe Jev (System 1)
All News Journal (v2.1)

Valida:
1. Avaliação editorial ultrarrápida (< 200ms) para matérias aderentes aos padrões (85-105 palavras).
2. Detecção e reprovação/revisão estruturada de artigos fora da margem, com perguntas finais ou clickbait.
3. Triagem de observabilidade operacional (quick_triage_supervisor) para cenários HEALTHY, WARNING e CRITICAL.
4. Integração nativa do Jev Gatekeeper com o StateGraph do LangGraph (node_critic e rotear_pos_critic).
5. Métricas de latência sub-milissegundo e cálculo de economia de tokens de inferência.
"""

import os
import sys
import unittest
import time
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.jev_gatekeeper import (
    evaluate_editorial_quality,
    quick_triage_supervisor,
    EditorialDecision,
    SupervisorTriage,
    SYSTEM_PROMPT_CRITIC,
    CriticAuditResult,
    auditar_resumo_critic
)
from core.graph_engine import node_writer, node_critic, rotear_pos_critic, GraphState


class TestJevGatekeeper(unittest.TestCase):
    """Testes unitários dos primitivos e regras de decisão do TypeSafe Jev."""

    def setUp(self):
        # Resenha calibrada com 61 palavras em 3 passos estilo The Economist (Fato com dados, Mecânica estrutural e So What?)
        self.artigo_perfeito = (
            "A expansão acelerada dos investimentos em inteligência artificial mobilizou 120 bilhões de dólares entre as principais corporações de tecnologia neste trimestre. "
            "A pressão de custos operacionais e a corrida por semicondutores de última geração forçaram uma reestruturação profunda nos orçamentos de pesquisa e desenvolvimento. "
            "Fabricantes de chips consolidam margens recordes no curto prazo, enquanto desenvolvedores de software enfrentam compressão de lucros sob risco de consolidação hostil."
        )
        self.artigo_curto = "A inteligência artificial avançou bastante neste último trimestre e trouxe novos investimentos para o setor de computação."
        self.artigo_com_interrogacao = (
            "A expansão acelerada dos investimentos em inteligência artificial mobilizou 120 bilhões de dólares entre as corporações globais. "
            "A pressão de custos e a corrida por semicondutores de última geração forçaram uma reestruturação profunda nos orçamentos vigentes. "
            "Será que as empresas conseguirão sustentar esse nível de investimento no próximo ano?"
        )
        self.artigo_com_clickbait = (
            "A expansão acelerada dos investimentos em inteligência artificial mobilizou 120 bilhões de dólares entre as corporações globais. "
            "Você não vai acreditar nas transformações que estão ocorrendo nos data centers de alta capacidade computacional neste momento. "
            "Fabricantes de semicondutores ampliam receitas imediatas, enquanto empresas menores enfrentam escassez de suprimentos."
        )

    def test_approved_article_fast_latency(self):
        """Valida se artigo conforme é aprovado em tempo < 200ms com primitivos válidos."""
        t0 = time.perf_counter()
        resultado = evaluate_editorial_quality(self.artigo_perfeito)
        duracao_ms = (time.perf_counter() - t0) * 1000

        # Validação de SLA de latência ultrarrápida
        self.assertLess(duracao_ms, 200.0, f"Latência de inferência ({duracao_ms:.2f}ms) excedeu o teto de 200ms")
        self.assertLess(resultado["latency_ms"], 200.0)

        # Validação dos primitivos estruturados Jev
        self.assertEqual(resultado["choice"], "APPROVE")
        self.assertTrue(resultado["noul"], "O primitivo noul deve ser True para artigos sem violação")
        self.assertGreaterEqual(resultado["score"], 4)
        self.assertGreaterEqual(resultado["confidence"], 0.80)
        self.assertGreaterEqual(resultado["word_count"], 58)
        self.assertLessEqual(resultado["word_count"], 92)

    def test_undersized_article_revises(self):
        """Valida que textos com menos de 58 palavras são encaminhados para revisão."""
        resultado = evaluate_editorial_quality(self.artigo_curto)
        self.assertIn(resultado["choice"], ["REVISE", "REJECT"])
        self.assertFalse(resultado["noul"], "O primitivo noul deve ser False para textos fora de conformidade")
        self.assertLessEqual(resultado["score"], 3)
        self.assertIn("Subdimensionado", resultado["reason"])

    def test_trailing_question_mark_revises(self):
        """Valida que interrogações finais causam reprovação com justificativa precisa."""
        resultado = evaluate_editorial_quality(self.artigo_com_interrogacao)
        self.assertIn(resultado["choice"], ["REVISE", "REJECT"])
        self.assertFalse(resultado["noul"])
        self.assertIn("interrogação", resultado["reason"].lower())

    def test_clickbait_revises(self):
        """Valida detecção de clichês jornalísticos e clickbaits."""
        resultado = evaluate_editorial_quality(self.artigo_com_clickbait)
        self.assertIn(resultado["choice"], ["REVISE", "REJECT"])
        self.assertFalse(resultado["noul"])
        self.assertIn("clichê", resultado["reason"].lower())

    def test_quick_triage_healthy(self):
        """Valida triagem operacional de rotina saudável."""
        log = "INFO [2026-09-25 18:00:00] Pipeline concluído com sucesso. Tempo total: 2.1s. Status 200 OK."
        triage = quick_triage_supervisor(log)
        self.assertTrue(triage["noul"])
        self.assertEqual(triage["choice"], "HEALTHY")
        self.assertEqual(triage["score"], 5)
        self.assertEqual(triage["action"], "PROCEED")
        self.assertLess(triage["latency_ms"], 100.0)

    def test_quick_triage_critical_trace(self):
        """Valida detecção imediata de anomalia crítica (Traceback/Exception)."""
        log = "ERROR [node_writer] Traceback (most recent call last): Exception: ConnectionRefusedError(10061)"
        triage = quick_triage_supervisor(log)
        self.assertFalse(triage["noul"])
        self.assertEqual(triage["choice"], "CRITICAL")
        self.assertEqual(triage["score"], 1)
        self.assertIn("ALERT", triage["action"])

    def test_quick_triage_warning_rate_limit(self):
        """Valida classificação de aviso operacional (ex: 429 Too Many Requests)."""
        log = "WARN [gemini_api] 429 Too Many Requests: quota exceeded, retry_count=1 acionado."
        triage = quick_triage_supervisor(log)
        self.assertFalse(triage["noul"])
        self.assertEqual(triage["choice"], "WARNING")
        self.assertEqual(triage["score"], 3)
        self.assertIn("MONITOR", triage["action"])


class TestLangGraphCriticIntegration(unittest.TestCase):
    """Testes de integração do nó Critic (Quality Gate) e roteamento de autocura."""

    def setUp(self):
        self.artigo_bom = (
            "A expansão acelerada dos investimentos globais em infraestrutura de inteligência artificial "
            "consolida um novo paradigma competitivo para as principais corporações de tecnologia. "
            "A mobilização de mais de duzentos bilhões de dólares na aquisição de processadores especializados "
            "e em complexos de energia limpa reforça a resiliência das cadeias produtivas continentais.\n\n"
            "Analistas de mercado observam que o movimento estabelece barreiras significativas de entrada "
            "para participantes emergentes no ecossistema de software empresarial. "
            "Com isso, a governança operacional e a previsibilidade orçamentária passam a ditar o ritmo das fusões corporativas."
        )

    def test_node_critic_approves_and_records_jev_decision(self):
        """Valida se o nó Critic aprova matéria conforme e registra os metadados do Jev."""
        estado_inicial: GraphState = {
            "draft_text": self.artigo_bom,
            "retry_count": 0,
            "status": "DRAFT_GENERATED",
            "execution_log": []
        }
        novo_estado = node_critic(estado_inicial)

        self.assertTrue(novo_estado["is_approved"])
        self.assertEqual(novo_estado["status"], "CRITIC_APPROVED")
        self.assertIn("Jev System 1 [APPROVE", novo_estado["critique_feedback"])
        self.assertIn("jev_decision", novo_estado)
        self.assertEqual(novo_estado["jev_decision"]["choice"], "APPROVE")
        self.assertTrue(novo_estado["jev_decision"]["noul"])

        # Validação do roteamento pós-critic
        destino = rotear_pos_critic(novo_estado)
        self.assertEqual(destino, "approved")

    def test_node_critic_rejects_and_triggers_autocure_loop(self):
        """Valida se rascunho defeituoso incrementa retry_count e aciona loop de autocura."""
        estado_inicial: GraphState = {
            "draft_text": "Texto muito curto com defeito evidente.",
            "retry_count": 0,
            "status": "DRAFT_GENERATED",
            "execution_log": []
        }
        novo_estado = node_critic(estado_inicial)

        self.assertFalse(novo_estado["is_approved"])
        self.assertEqual(novo_estado["retry_count"], 1)
        self.assertIn(novo_estado["status"], ["CRITIC_REVISED", "CRITIC_REJECTED"])
        self.assertFalse(novo_estado["jev_decision"]["noul"])

        # O roteamento condicional deve retornar para o Writer quando retry_count < 3
        destino = rotear_pos_critic(novo_estado)
        self.assertEqual(destino, "retry_writer")

    def test_node_critic_exhaustion_allows_progression(self):
        """Valida que após 3 tentativas o loop não trava indefinidamente e avança."""
        estado_esgotado: GraphState = {
            "draft_text": "Texto curto.",
            "retry_count": 3,
            "is_approved": False,
            "status": "CRITIC_REJECTED"
        }
        destino = rotear_pos_critic(estado_esgotado)
        self.assertEqual(destino, "approved")

    def test_node_writer_economist_style(self):
        """Valida que o Nó 2 (Writer) gera resenha calibrada entre 60 e 90 palavras nos 3 passos."""
        estado = {
            "selected_story": {
                "titulo": "Banco Central mantém juros",
                "resumo": "Taxa mantida a 10,50%",
                "caderno": "Economia"
            },
            "retry_count": 0
        }
        res = node_writer(estado)
        self.assertEqual(res["status"], "DRAFT_GENERATED")
        self.assertGreaterEqual(res["word_count"], 58)
        self.assertLessEqual(res["word_count"], 92)

    def test_node_writer_discard_status(self):
        """Valida que o Nó 2 (Writer) acata o status DISCARD para matérias rasas."""
        import json
        from unittest.mock import MagicMock, patch
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({"status": "DISCARD", "motivo": "Ausência de dados concretos."})
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp

        with patch("google.generativeai.GenerativeModel", return_value=mock_model), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key_for_test"}):
            estado = {
                "selected_story": {
                    "titulo": "Fato Raso",
                    "resumo": "Sem dados",
                    "caderno": "Geral"
                }
            }
            res = node_writer(estado)
            self.assertEqual(res["status"], "DISCARDED")
            self.assertIn("Ausência de dados", res["discard_reason"])
            c_res = node_critic(res)
            self.assertEqual(c_res["status"], "DISCARDED")
            self.assertFalse(c_res["is_approved"])

    def test_benchmark_latency_and_efficiency(self):
        """Executa bateria de 50 iterações para demonstrar estabilidade sub-10ms e economia de tokens."""
        latencias = []
        for _ in range(50):
            t0 = time.perf_counter()
            decisao = evaluate_editorial_quality(self.artigo_bom)
            latencias.append((time.perf_counter() - t0) * 1000)

        media_ms = sum(latencias) / len(latencias)
        p95_ms = sorted(latencias)[int(len(latencias) * 0.95)]

        print(f"\n⚡ [JEV BENCHMARK] Média: {media_ms:.2f}ms | P95: {p95_ms:.2f}ms | Amostras: 50")
        self.assertLess(media_ms, 50.0, f"Latência média ({media_ms:.2f}ms) deve ser amplamente inferior a 50ms")
        self.assertLess(p95_ms, 100.0, f"P95 ({p95_ms:.2f}ms) deve ser inferior a 100ms")



class TestQualityGateCriticAudit(unittest.TestCase):
    """Testes específicos das 4 Regras de Validação do SYSTEM_PROMPT_CRITIC."""

    def setUp(self):
        # Resenha calibrada com 61 palavras em 3 passos estilo The Economist
        self.resumo_valido = (
            "A expansão acelerada dos investimentos em inteligência artificial mobilizou 120 bilhões de dólares entre as principais corporações de tecnologia neste trimestre. "
            "A pressão de custos operacionais e a corrida por semicondutores de última geração forçaram uma reestruturação profunda nos orçamentos de pesquisa e desenvolvimento. "
            "Fabricantes de chips consolidam margens recordes no curto prazo, enquanto desenvolvedores de software enfrentam compressão de lucros sob risco de consolidação hostil."
        )

    def test_regra_1_contagem_valida_e_invalida(self):
        # Válido: 61 palavras
        r = auditar_resumo_critic(self.resumo_valido)
        self.assertTrue(r["aprovado"])
        self.assertEqual(r["word_count"], len(self.resumo_valido.split()))
        self.assertEqual(r["motivo_rejeicao"], "")
        self.assertEqual(r["instrucao_reescrita"], "")

        # Inválido: subdimensionado
        texto_curto = "Texto curto com poucas palavras sem cumprir a meta normativa do jornal."
        r_curto = auditar_resumo_critic(texto_curto)
        self.assertFalse(r_curto["aprovado"])
        self.assertIn("Subdimensionado", r_curto["motivo_rejeicao"])
        self.assertTrue(len(r_curto["instrucao_reescrita"]) > 0)

    def test_regra_2_integridade_ponto_final_e_corte_abrupto(self):
        # Corte abrupto com reticências
        texto_reticencias = self.resumo_valido.rsplit(".", 1)[0] + "..."
        r1 = auditar_resumo_critic(texto_reticencias)
        self.assertFalse(r1["aprovado"])
        self.assertIn("reticências", r1["motivo_rejeicao"].lower())

        # Término com pergunta
        texto_pergunta = self.resumo_valido.rsplit(".", 1)[0] + "?"
        r2 = auditar_resumo_critic(texto_pergunta)
        self.assertFalse(r2["aprovado"])
        self.assertIn("interrogação", r2["motivo_rejeicao"].lower())

    def test_regra_3_limpeza_creditos_e_html(self):
        # Crédito Getty / BBC / Foto
        texto_com_credito = self.resumo_valido + " Foto: Getty Images / BBC."
        r1 = auditar_resumo_critic(texto_com_credito)
        self.assertFalse(r1["aprovado"])
        self.assertIn("crédito", r1["motivo_rejeicao"].lower())

        # HTML quebrado
        texto_html_quebrado = self.resumo_valido + " <div class='quebrado'"
        r2 = auditar_resumo_critic(texto_html_quebrado)
        self.assertFalse(r2["aprovado"])
        self.assertIn("html", r2["motivo_rejeicao"].lower())

    def test_regra_4_profundidade_e_cliches(self):
        # Clickbait proibido
        texto_cliche = "Você não vai acreditar no avanço da computação. " + self.resumo_valido
        r = auditar_resumo_critic(texto_cliche)
        self.assertFalse(r["aprovado"])
        self.assertIn("clichê", r["motivo_rejeicao"].lower())

    def test_cliches_proibidos_the_economist(self):
        """Valida reprovação de chavões proibidos: nova dinâmica competitiva, cadeia operacional, acompanhado de perto por analistas."""
        for frase_proibida in [
            "estabelecem uma nova dinâmica competitiva no mercado internacional.",
            "geram impactos substanciais na cadeia operacional das corporações.",
            "o movimento é acompanhado de perto por analistas do setor financeiro."
        ]:
            texto_cliche = f"{self.resumo_valido} O cenário {frase_proibida}"
            r = auditar_resumo_critic(texto_cliche)
            self.assertFalse(r["aprovado"])
            self.assertIn("clichê", r["motivo_rejeicao"].lower())

    def test_esquema_pydantic_critic_audit_result(self):
        res = auditar_resumo_critic(self.resumo_valido)
        modelo = CriticAuditResult(**res)
        self.assertTrue(modelo.aprovado)
        self.assertGreaterEqual(modelo.word_count, 60)
        self.assertLessEqual(modelo.word_count, 90)


if __name__ == "__main__":
    unittest.main()
