"""
tests/test_quality_filter.py — Testes Unitários do Quality Gate com Supressão Editorial Ativa
All News Journal (v2.2)

Valida:
1. Eliminação de listas genéricas e tutoriais triviais.
2. Critérios de Wellness: aprovação de inovação de produto/negócios e rejeição de treinos/dietas genéricas.
3. Critérios de IA: aprovação de lançamentos técnicos/hardware e rejeição de especulações vazias.
4. Regra de supressão ativa: corte de 8.0/10 e classificação como SUPPRESSED.
5. Persistência de auditoria em logs/alertas_cadernos.json e contingência manual.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

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

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.quality_filter import (
    triar_caderno_com_ia,
    registrar_alerta_caderno,
    obter_alertas_cadernos,
    remover_alerta_caderno,
    _avaliar_heuristica_local,
    ALERTAS_FILE
)

BRT = timezone(timedelta(hours=-3))


class TestQualityFilter(unittest.TestCase):

    def setUp(self):
        """Salva estado original de alertas_cadernos.json."""
        self.backup_alertas = None
        if ALERTAS_FILE.exists():
            try:
                with open(ALERTAS_FILE, "r", encoding="utf-8") as f:
                    self.backup_alertas = f.read()
            except Exception:
                pass
        # Inicializa arquivo de alertas limpo para o teste
        ALERTAS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTAS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    def tearDown(self):
        """Restaura alertas originais."""
        if self.backup_alertas is not None:
            with open(ALERTAS_FILE, "w", encoding="utf-8") as f:
                f.write(self.backup_alertas)
        elif ALERTAS_FILE.exists():
            try:
                ALERTAS_FILE.unlink()
            except Exception:
                pass

    def test_01_elimination_generic_lists(self):
        """Valida que títulos com padrões de listas ('5 dicas', 'exercícios para') são rejeitados."""
        res1 = _avaliar_heuristica_local("Geral", "5 dicas infalíveis para organizar suas finanças")
        self.assertFalse(res1["aprovado"])
        self.assertLess(res1["score"], 8.0)

        res2 = _avaliar_heuristica_local("Wellness", "7 exercícios para perder barriga em casa")
        self.assertFalse(res2["aprovado"])
        self.assertLess(res2["score"], 8.0)

    def test_02_wellness_product_innovation_approved(self):
        """Valida que inovação tecnológica de tênis ou bike em Wellness atinge nota de corte."""
        res = _avaliar_heuristica_local(
            "Wellness",
            "Nike lança novo tênis com placa de carbono e tecnologia de amortecimento para maratonistas",
            "O novo calçado traz sensores biométricos de performance e contrato recorde para a maratona."
        )
        self.assertTrue(res["aprovado"])
        self.assertGreaterEqual(res["score"], 8.0)

    def test_03_wellness_generic_diet_rejected(self):
        """Valida que receitas ou dietas genéricas são rejeitadas em Wellness."""
        res = _avaliar_heuristica_local(
            "Wellness",
            "Como fazer suco verde para emagrecer e manter a dieta no verão",
            "Dicas simples para emagrecer rápido com alimentação saudável."
        )
        self.assertFalse(res["aprovado"])
        self.assertLess(res["score"], 8.0)

    def test_04_ia_technical_release_approved(self):
        """Valida que lançamentos de modelos, semicondutores e GPUs são aprovados em IA."""
        res = _avaliar_heuristica_local(
            "IA",
            "Nvidia e OpenAI apresentam nova arquitetura de datacenter com chips e supercomputador para IA",
            "Hardware avançado eleva benchmark de treinamento de modelos com investimento bilionário."
        )
        self.assertTrue(res["aprovado"])
        self.assertGreaterEqual(res["score"], 8.0)

    def test_05_ia_shallow_speculation_rejected(self):
        """Valida que especulações ou boatos genéricos em IA são rejeitados."""
        res = _avaliar_heuristica_local(
            "IA",
            "A inteligência artificial vai roubar seu emprego? Veja os mitos das redes",
            "Discussão genérica sobre o futuro do trabalho sem dados técnicos."
        )
        self.assertFalse(res["aprovado"])
        self.assertLess(res["score"], 8.0)

    def test_06_caderno_suppression_when_no_story_qualifies(self):
        """Valida que se nenhuma matéria atinge score >= 8.0, o caderno é SUPPRESSED e registrado."""
        candidatas_rasas = [
            {"title": "5 dicas de alongamento para o dia a dia", "summary": "Exercícios simples."},
            {"title": "Receita de chá termogênico para desinchar", "summary": "Dieta fácil."},
            {"title": "Como beber mais água com lembretes no celular", "summary": "Dicas de saúde."}
        ]
        resultado = triar_caderno_com_ia("Wellness", candidatas_rasas)
        self.assertEqual(resultado["status"], "SUPPRESSED")
        self.assertEqual(len(resultado["materias_aprovadas"]), 0)
        self.assertGreater(len(resultado["materias_descartadas"]), 0)
        self.assertIsNotNone(resultado["motivo_supressao"])

        # Verifica se gravou no arquivo de alertas
        alertas = obter_alertas_cadernos()
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["caderno"], "Wellness")
        self.assertEqual(alertas[0]["status"], "SUPPRESSED")
        self.assertGreater(len(alertas[0]["exemplos_descartados"]), 0)

    def test_07_caderno_approval_when_story_qualifies(self):
        """Valida que o caderno é aprovado se contiver matéria com score >= 8.0."""
        candidatas_mistas = [
            {"title": "5 dicas para emagrecer rápido", "summary": "Dieta rasa."},
            {
                "title": "Specialized apresenta bicicleta com sensores biométricos e quadro de carbono para o circuito mundial",
                "summary": "Inovação tecnológica para atletas de alta performance com investimento de milhões."
            }
        ]
        resultado = triar_caderno_com_ia("Wellness", candidatas_mistas)
        self.assertEqual(resultado["status"], "APPROVED")
        self.assertGreaterEqual(len(resultado["materias_aprovadas"]), 1)
        self.assertGreaterEqual(resultado["materias_aprovadas"][0]["quality_score"], 8.0)

    def test_08_alert_recovery_and_cleanup(self):
        """Valida a remoção de alerta de caderno após contingência manual."""
        data_hoje = datetime.now(BRT).strftime("%Y-%m-%d")
        registrar_alerta_caderno("Economia", "Falta de matérias relevantes", ["Título 1", "Título 2"], data_hoje)
        
        alertas = obter_alertas_cadernos(data_hoje)
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["caderno"], "Economia")

        # Recuperação por contingência manual
        removido = remover_alerta_caderno("Economia", data_hoje)
        self.assertTrue(removido)
        
        alertas_pos = obter_alertas_cadernos(data_hoje)
        self.assertEqual(len(alertas_pos), 0)


if __name__ == "__main__":
    unittest.main()
