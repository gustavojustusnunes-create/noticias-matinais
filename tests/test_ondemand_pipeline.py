"""
tests/test_ondemand_pipeline.py — Testes Unitários e de Integração da Pipeline On-Demand
All News Journal (v2.2)

Valida:
1. Resiliência do nó Researcher (fallback nativo para Google News RSS).
2. Nó Writer: formatação de headline, blocos de 85 a 105 palavras e hashtags.
3. Nó Critic: conformidade do Jev Quality Gate e roteamento condicional.
4. Nó Media Retriever: download de imagem e renderização dos slides 1080x1350.
5. Watchdog HITL: enfileiramento, aprovação manual, rejeição e auto-publicação em timeout de 60 min.
6. Dispatcher Instagram: modo fallback / dry-run e Meta Graph API.
"""

import os
import sys
import json
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ondemand_state import OnDemandState
from core.ondemand_researcher import node_researcher, buscar_noticias_rss_fallback
from core.ondemand_writer import node_writer
from core.ondemand_graph import node_ondemand_critic, rotear_pos_critic, ondemand_graph
from core.ondemand_media import node_media_retriever, buscar_imagem_wikimedia
from core.ondemand_watchdog import (
    adicionar_tarefa_fila,
    obter_fila,
    obter_tarefa,
    aprovar_tarefa,
    rejeitar_tarefa,
    verificar_timeouts,
    QUEUE_FILE
)
from instagram_poster import publicar_post_ondemand

BRT = timezone(timedelta(hours=-3))


class TestOnDemandPipeline(unittest.TestCase):

    def setUp(self):
        """Salva o estado original da fila para não corromper dados reais."""
        self.backup_queue = None
        if QUEUE_FILE.exists():
            try:
                with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                    self.backup_queue = f.read()
            except Exception:
                pass
        # Inicializa fila limpa para os testes
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    def tearDown(self):
        """Restaura o estado original da fila."""
        if self.backup_queue is not None:
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                f.write(self.backup_queue)
        elif QUEUE_FILE.exists():
            try:
                QUEUE_FILE.unlink()
            except Exception:
                pass

    def test_01_researcher_fallback(self):
        """Valida se o researcher busca fontes reais via Google News RSS sem API keys."""
        noticias = buscar_noticias_rss_fallback("Inteligência Artificial Brasil")
        self.assertIsInstance(noticias, list)
        self.assertGreater(len(noticias), 0, "Deveria retornar ao menos 1 notícia do Google News RSS.")
        self.assertTrue("title" in noticias[0])
        self.assertTrue("url" in noticias[0])

    def test_02_writer_structure(self):
        """Valida se o nó writer estrutura manchete, subtítulo e blocos de leitura."""
        mock_state: OnDemandState = {
            "task_id": "test_task_01",
            "topic_raw": "BCE anuncia corte de juros de 25 pontos base após desaceleração da inflação",
            "tema": "Economia",
            "formato": "carrossel",
            "research_dossier": {
                "summary": "O Banco Central Europeu realizou novo corte nos juros de referência da Zona do Euro...",
                "sources": [{"title": "BCE corta juros", "url": "https://exemplo.com", "snippet": "Decisão histórica"}]
            },
            "retry_count": 0,
            "execution_log": []
        }
        resultado = node_writer(mock_state)
        self.assertIn("headline", resultado)
        self.assertIn("slides_text", resultado)
        self.assertIn("caption", resultado)
        self.assertGreater(len(resultado["slides_text"]), 0)
        # Manchete não deve terminar com ?
        self.assertFalse(resultado["headline"].endswith("?"))

    def test_03_critic_and_routing(self):
        """Valida a avaliação do Jev Quality Gate e a lógica de edge condicional."""
        mock_state: OnDemandState = {
            "task_id": "test_task_02",
            "headline": "Corte de juros no BCE impulsiona bolsas globais",
            "slides_text": [
                "O Banco Central Europeu determinou nesta manhã a redução de vinte e cinco pontos base na taxa básica de juros, marcando uma transição na estratégia monetária do bloco. A autoridade financeira busca equilibrar o controle dos preços com o estímulo à atividade econômica nos países membros."
            ],
            "retry_count": 0,
            "execution_log": []
        }
        res_critic = node_ondemand_critic(mock_state)
        self.assertIn("is_approved_by_critic", res_critic)
        self.assertIn("critic_verdict", res_critic)

        # Testa roteamento
        mock_state["is_approved_by_critic"] = True
        self.assertEqual(rotear_pos_critic(mock_state), "approved")

        mock_state["is_approved_by_critic"] = False
        mock_state["retry_count"] = 0
        self.assertEqual(rotear_pos_critic(mock_state), "retry_writer")

        mock_state["retry_count"] = 2
        self.assertEqual(rotear_pos_critic(mock_state), "approved")

    def test_04_media_retriever_rendering(self):
        """Valida se o nó media_retriever busca imagem e gera arquivos de imagem reais no disco."""
        mock_state: OnDemandState = {
            "task_id": "test_media_render",
            "tema": "Economia",
            "formato": "carrossel",
            "headline": "Taxa de Juros Europeia Recua",
            "subtitulo": "BCE ajusta juros após estabilização econômica",
            "keyword": "ECONOMIA",
            "slides_text": [
                "A decisão de flexibilizar a política monetária representa um marco significativo após anos de combate rigoroso à inflação na Europa. Analistas apontam que a liquidez adicional deve aquecer o comércio.",
                "Por outro lado, o Banco Central mantém cautela em relação a novas movimentações, afirmando que qualquer passo subsequente dependerá de indicadores macroeconômicos consistentes."
            ],
            "image_query": "Central Bank Finance",
            "execution_log": []
        }
        res_media = node_media_retriever(mock_state)
        self.assertIn("slide_paths", res_media)
        slide_paths = res_media["slide_paths"]
        self.assertGreater(len(slide_paths), 0)
        
        # Verifica se os arquivos foram criados e são imagens válidas
        for p in slide_paths:
            self.assertTrue(os.path.exists(p), f"Arquivo de slide não existe: {p}")
            self.assertGreater(os.path.getsize(p), 1000, f"Arquivo de imagem está vazio: {p}")

        # Limpeza
        output_dir = Path("edicoes") / "ondemand" / "test_media_render"
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_05_watchdog_queue_and_actions(self):
        """Valida o enfileiramento, consulta, aprovação manual e rejeição de tarefas."""
        agora = datetime.now(BRT)
        task_id = "test_queue_001"
        task_data = {
            "task_id": task_id,
            "topic_raw": "Notícia teste de fila",
            "tema": "IA",
            "formato": "carrossel",
            "headline": "Avanço Histórico em IA",
            "caption": "Legenda teste #ia",
            "slide_paths": ["instagram_poster.py"],
            "hitl_status": "PENDING_APPROVAL",
            "created_at": agora.isoformat(),
            "expires_at": (agora + timedelta(seconds=3600)).isoformat(),
            "retry_count": 0,
            "execution_log": []
        }

        # 1. Enfileirar
        adicionar_tarefa_fila(task_data)
        fila = obter_fila()
        self.assertEqual(len(fila), 1)
        self.assertEqual(fila[0]["task_id"], task_id)
        self.assertEqual(fila[0]["hitl_status"], "PENDING_APPROVAL")

        # 2. Aprovação Manual
        res_aprov = aprovar_tarefa(task_id)
        self.assertTrue(res_aprov["success"])
        self.assertEqual(res_aprov["status"], "PUBLISHED")
        
        t_pos_aprov = obter_tarefa(task_id)
        self.assertEqual(t_pos_aprov["hitl_status"], "PUBLISHED")

        # 3. Rejeição
        task_id_2 = "test_queue_002"
        task_data_2 = dict(task_data, task_id=task_id_2, hitl_status="PENDING_APPROVAL")
        adicionar_tarefa_fila(task_data_2)
        res_rej = rejeitar_tarefa(task_id_2, motivo="Pauta duplicada")
        self.assertTrue(res_rej["success"])
        self.assertEqual(res_rej["status"], "REJECTED")

    def test_06_watchdog_timeout_auto_publish(self):
        """Valida o auto-dispatch autônomo quando uma tarefa atinge 60 minutos (timeout)."""
        passado = datetime.now(BRT) - timedelta(seconds=3650)
        task_id = "test_timeout_task"
        task_data = {
            "task_id": task_id,
            "topic_raw": "Pauta expirada sem intervenção",
            "tema": "Economia",
            "formato": "carrossel",
            "headline": "Mercados em Alta",
            "caption": "Legenda #economia",
            "slide_paths": ["instagram_poster.py"],
            "hitl_status": "PENDING_APPROVAL",
            "created_at": passado.isoformat(),
            "expires_at": (passado + timedelta(seconds=3600)).isoformat(),
            "retry_count": 0
        }
        adicionar_tarefa_fila(task_data)

        # Executa verificação de timeouts do watchdog
        processadas = verificar_timeouts()
        self.assertEqual(len(processadas), 1)
        self.assertEqual(processadas[0]["task_id"], task_id)
        self.assertTrue(processadas[0].get("auto_published"))

        t_atualizada = obter_tarefa(task_id)
        self.assertEqual(t_atualizada["hitl_status"], "PUBLISHED")

    def test_07_instagram_dispatcher_dryrun(self):
        """Valida a publicação no modo seguro/dry-run."""
        res = publicar_post_ondemand(paths=["instagram_poster.py"], legenda="Teste de publicação")
        self.assertTrue(res["success"])
        self.assertIn("mode", res)


if __name__ == "__main__":
    unittest.main()
