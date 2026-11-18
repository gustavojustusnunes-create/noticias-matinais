"""
tests/test_editorial_jovem_4blocos.py — Suíte de Testes Automatizados
Manual Editorial Jovem Multicanal (18 a 30 anos)

Valida:
1. Existência e estrutura da skill permanente em skills/editorial_jovem/SKILL.md.
2. Matriz de Curadoria 0 a 10 e Lista Negra via score_news_curation().
3. Rejeição cirúrgica e aprovação nos 7 itens do Quality Gate via audit_checklist_7_items().
4. Conversão ponta a ponta no LangGraph de uma notícia financeira densa
   (queda das ações do PicPay e revisão da CBS) para a anatomia de 4 Blocos Universais,
   validação dos 7 checks verdes e geração paralela dos 4 canais (Newsletter HTML,
   Carrossel IG, Thread X e Roteiro Podcast/Reels).
"""

import os
import sys
import json
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.jev_gatekeeper import (
    CurationDecision,
    AuditVerdict,
    score_news_curation,
    audit_checklist_7_items,
)
from core.graph_engine import (
    executar_fluxo,
    aprovar_e_despachar,
    carregar_skill_editorial_jovem,
)


class TestEditorialJovem4Blocos(unittest.TestCase):
    def test_1_skill_editorial_jovem_exists_and_has_4_blocks(self):
        """Verifica se skills/editorial_jovem/SKILL.md existe e contém a anatomia obrigatória."""
        skill_path = ROOT_DIR / "skills" / "editorial_jovem" / "SKILL.md"
        self.assertTrue(skill_path.exists(), "Arquivo skills/editorial_jovem/SKILL.md deve existir.")

        conteudo = carregar_skill_editorial_jovem()
        self.assertIn("18 a 30 anos", conteudo)
        self.assertIn("bloco_1_gancho", conteudo)
        self.assertIn("bloco_2_fato", conteudo)
        self.assertIn("bloco_3_e_dai", conteudo)
        self.assertIn("bloco_4_fechamento", conteudo)

    def test_2_score_news_curation_blacklist_and_matrix(self):
        """Valida descarte imediato na Lista Negra e pontuação >= 8 em pauta de alto impacto no bolso."""
        noticia_proibida = {
            "titulo": "Homicídio e tiroteio sangrento deixam feridos em operação policial",
            "caderno": "Policial",
            "resumo": "Caso policial violento registrado na madrugada.",
        }
        dec_black = score_news_curation(noticia_proibida, use_llm=False)
        self.assertIsInstance(dec_black, CurationDecision)
        self.assertTrue(dec_black.is_blacklisted)
        self.assertEqual(dec_black.total_score, 0)
        self.assertEqual(dec_black.route, "DISCARD")

        noticia_picpay_cbs = {
            "titulo": "Ações do PicPay recuam 12% em NY após revisão de lucro e ajuste na alíquota da CBS",
            "caderno": "Macroeconomia & Mercados",
            "resumo": (
                "Segundo dados da Bloomberg e da Receita Federal, as ações do PicPay caíram 12% na bolsa "
                "após revisão da projeção de lucro trimestral para R$ 180 milhões diante da nova alíquota "
                "de 26,5% da CBS e do aperto no spread bancário sobre cartões e crédito digital."
            ),
        }
        dec_alta = score_news_curation(noticia_picpay_cbs, use_llm=False)
        self.assertFalse(dec_alta.is_blacklisted)
        self.assertGreaterEqual(dec_alta.total_score, 8)
        self.assertEqual(dec_alta.route, "FULL_OMNICHANNEL")

    def test_3_audit_checklist_7_items_rejects_jargon_without_analogy(self):
        """Garante que rascunhos com siglas cruas (CBS, EBITDA, Spread) sem analogia na mesma frase sejam reprovados."""
        rascunho_ruim = {
            "bloco_1_gancho": (
                "As flutuações macroeconômicas trimestrais nos índices internacionais demonstram "
                "uma volatilidade acentuada nos ativos financeiros listados no exterior."
            ),
            "bloco_2_fato": "O EBITDA caiu por causa da CBS e do spread bancário elevado.",
            "bloco_3_e_dai": "O mercado segue cauteloso.",
            "bloco_4_fechamento": "Fim do comunicado.",
        }
        verdict = audit_checklist_7_items(rascunho_ruim, use_llm=False)
        self.assertIsInstance(verdict, AuditVerdict)
        self.assertFalse(verdict.approved)
        self.assertFalse(verdict.checklist.limpeza_jargoes)
        self.assertFalse(verdict.checklist.teste_3_segundos)
        self.assertFalse(verdict.checklist.gatilho_comunidade)
        self.assertIn("limpeza_jargoes", verdict.failed_items)
        self.assertGreater(len(verdict.correction_instructions), 20)

    def test_4_full_pipeline_converts_dense_picpay_cbs_news_and_passes_all_7_checks(self):
        """
        Teste Ponta a Ponta (Etapa 4):
        Converte uma notícia corporativa/tributária densa (queda das ações do PicPay + revisão da CBS)
        para o formato de 4 Blocos Universais, valida aprovação nos 7 itens do checklist e verifica
        os payloads dos 4 subagentes multicanal gerados em paralelo.
        """
        noticia_densa = {
            "titulo": "Papéis do PicPay recuam 12% na Nasdaq em meio à recalibração da CBS e compressão de spread",
            "caderno": "Macroeconomia & Mercados",
            "fonte": "Bloomberg / Receita Federal",
            "link": "https://noticias-matinais.vercel.app",
            "imagem": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=1200",
            "resumo": (
                "As ações do PicPay registraram retração de 12% no pregão de Nova York após a instituição "
                "revisar o guidance operacional para R$ 180 milhões no trimestre, pressionada pela regulamentação "
                "da alíquota de 26,5% da CBS pela Receita Federal e pelo estreitamento do spread bancário nas "
                "operações de crédito rotativo e emissões de CDB promocional."
            ),
        }

        estado_inicial = {
            "raw_news": [noticia_densa],
            "retry_count": 0,
            "is_approved": False,
            "hitl_approved": False,
            "status": "PENDING",
            "execution_log": [],
        }

        resultado_hitl = executar_fluxo(initial_state=estado_inicial, thread_id="test_picpay_cbs_4blocos")

        # 1. Valida Curadoria (Score 0-10)
        self.assertGreaterEqual(resultado_hitl["curation_score"], 8)
        self.assertEqual(resultado_hitl["curation_route"], "FULL_OMNICHANNEL")

        # 2. Valida Anatomia de 4 Blocos Universais
        blocos = resultado_hitl["draft_blocks"]
        for k in ("bloco_1_gancho", "bloco_2_fato", "bloco_3_e_dai", "bloco_4_fechamento"):
            self.assertIn(k, blocos)
            self.assertTrue(len(blocos[k].strip()) > 0)
        self.assertLessEqual(len(blocos["bloco_1_gancho"].split()), 15)
        self.assertTrue(blocos["bloco_4_fechamento"].endswith("?"))

        # 3. Valida Aprovação nos 7 Itens do Checklist
        verdict = resultado_hitl["audit_verdict"]
        checklist = verdict["checklist"]
        self.assertTrue(resultado_hitl["is_approved"])
        self.assertTrue(verdict["approved"])
        self.assertEqual(verdict["passed_count"], 7)
        self.assertTrue(checklist["fonte_validada"])
        self.assertTrue(checklist["teste_3_segundos"])
        self.assertTrue(checklist["teste_e_dai"])
        self.assertTrue(checklist["limpeza_jargoes"])
        self.assertTrue(checklist["contagem_palavras"])
        self.assertTrue(checklist["reducao_ansiedade"])
        self.assertTrue(checklist["gatilho_comunidade"])

        # 4. Valida Fan-out Paralelo dos 4 Canais
        fanout = resultado_hitl["multichannel_payloads"]
        self.assertIn("email_newsletter", fanout)
        self.assertIn("💰 Como isso afeta você", fanout["email_newsletter"]["full_html"])
        self.assertIn("💬 Pergunta do Dia", fanout["email_newsletter"]["full_html"])

        ig = fanout["instagram_carousel"]
        self.assertTrue(6 <= ig["slide_count"] <= 8)
        for slide in ig["slides"]:
            self.assertTrue(25 <= slide["word_count"] <= 35)
        self.assertTrue(80 <= ig["caption_word_count"] <= 120)

        x_payload = fanout["x_twitter"]
        self.assertTrue(5 <= x_payload["post_count"] <= 7)
        for c_len, w_len in zip(x_payload["char_counts"], x_payload["word_counts"]):
            self.assertLessEqual(c_len, 240)
            self.assertTrue(25 <= w_len <= 45)

        av_payload = fanout["audio_video_reels"]
        self.assertGreaterEqual(len(av_payload["podcast_dialogue"]), 4)
        self.assertTrue(110 <= av_payload["reels_word_count"] <= 150)

        # 5. Valida Retenção no HITL Founder Gate e Despacho Final
        self.assertEqual(resultado_hitl["status"], "AWAITING_FOUNDER_APPROVAL")
        resultado_final = aprovar_e_despachar(thread_id="test_picpay_cbs_4blocos")
        self.assertEqual(resultado_final["status"], "DISPATCHED")
        self.assertTrue(resultado_final["hitl_approved"])

        print("\n=== RESUMO DA CONVERSÃO AUTOMATIZADA (PICPAY & CBS -> 4 BLOCOS + 7 CHECKS) ===")
        print(f"Score Curadoria: {resultado_hitl['curation_score']}/10 | Rota: {resultado_hitl['curation_route']}")
        print(json.dumps(blocos, indent=2, ensure_ascii=False))
        print("Checklist 7 Itens:", json.dumps(checklist, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
