"""
core/ondemand_watchdog.py — Watchdog e Fila de Aprovação HITL para Pautas On-Demand
All News Journal (v2.2)

Responsável por:
1. Persistir o estado da fila em logs/ondemand_queue.json de forma segura e atômica.
2. Monitorar tarefas em PENDING_APPROVAL.
3. Se 60 minutos se passarem sem intervenção manual do fundador, o watchdog auto-aprova
   a pauta e dispara a publicação autônoma no Instagram.
4. Fornecer endpoints/funções para aprovação e rejeição manual no Control Center (Streamlit).
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

BRT = timezone(timedelta(hours=-3))
QUEUE_FILE = Path("logs") / "ondemand_queue.json"
_queue_lock = threading.Lock()
_watchdog_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _parse_datetime(ts_str: Optional[str]) -> datetime:
    """Converte string ISO 8601 em objeto datetime com fuso BRT."""
    if not ts_str:
        return datetime.now(BRT)
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BRT)
        return dt
    except Exception:
        return datetime.now(BRT)


def _carregar_fila_unlocked() -> List[Dict[str, Any]]:
    """Lê a fila de tarefas do disco sem adquirir o lock (uso interno sob lock)."""
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "tasks" in data:
                return data["tasks"]
            return []
    except Exception as e:
        print(f"⚠️ [Watchdog] Erro ao ler fila de {QUEUE_FILE}: {e}")
        return []


def _salvar_fila_unlocked(fila: List[Dict[str, Any]]) -> None:
    """Salva a fila de tarefas no disco com escrita atômica (uso interno sob lock)."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = QUEUE_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=2)
        # Substituição atômica no sistema operacional
        temp_file.replace(QUEUE_FILE)
    except Exception as e:
        print(f"❌ [Watchdog] Erro ao salvar fila em {QUEUE_FILE}: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def obter_fila() -> List[Dict[str, Any]]:
    """Retorna todas as tarefas da fila ordenadas pelas mais recentes."""
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        return sorted(fila, key=lambda x: x.get("created_at", ""), reverse=True)


def obter_tarefa(task_id: str) -> Optional[Dict[str, Any]]:
    """Localiza uma tarefa específica pelo ID."""
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        for t in fila:
            if t.get("task_id") == task_id:
                return t
    return None


def adicionar_tarefa_fila(task_data: Dict[str, Any]) -> None:
    """Adiciona uma nova tarefa ou atualiza uma existente na fila persistente."""
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        task_id = task_data.get("task_id")
        
        existente = False
        for idx, t in enumerate(fila):
            if t.get("task_id") == task_id:
                fila[idx] = task_data
                existente = True
                break
        
        if not existente:
            fila.append(task_data)
        
        _salvar_fila_unlocked(fila)
        print(f"   📋 [Watchdog] Tarefa '{task_id}' adicionada à fila com sucesso.")


def aprovar_tarefa(task_id: str) -> Dict[str, Any]:
    """
    Aprovação manual pelo fundador.
    Dispara a publicação no Instagram e atualiza o status na fila.
    """
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        tarefa = None
        for t in fila:
            if t.get("task_id") == task_id:
                tarefa = t
                break
        
        if not tarefa:
            return {"success": False, "error": f"Tarefa {task_id} não encontrada."}
        
        agora = datetime.now(BRT)
        tarefa["hitl_status"] = "APPROVED_MANUAL"
        tarefa["approved_at"] = agora.isoformat()
        
        # Dispara publicação no Instagram
        try:
            from instagram_poster import publicar_post_ondemand
            slide_paths = tarefa.get("slide_paths", [])
            legenda = tarefa.get("caption", "")
            res_pub = publicar_post_ondemand(slide_paths, legenda)
            
            tarefa["publish_result"] = res_pub
            tarefa["published_at"] = datetime.now(BRT).isoformat()
            if res_pub.get("success", False):
                tarefa["hitl_status"] = "PUBLISHED"
            else:
                tarefa["hitl_status"] = "PUBLISH_FAILED"
                tarefa["publish_error"] = res_pub.get("error", "Falha desconhecida no disparo")
        except Exception as e_pub:
            tarefa["hitl_status"] = "PUBLISH_FAILED"
            tarefa["publish_error"] = str(e_pub)
            res_pub = {"success": False, "error": str(e_pub)}

        _salvar_fila_unlocked(fila)
        return {
            "success": tarefa["hitl_status"] == "PUBLISHED",
            "task_id": task_id,
            "status": tarefa["hitl_status"],
            "publish_result": res_pub
        }


def rejeitar_tarefa(task_id: str, motivo: str = "Rejeitado pelo fundador") -> Dict[str, Any]:
    """Rejeita uma tarefa na fila, cancelando a publicação."""
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        tarefa = None
        for t in fila:
            if t.get("task_id") == task_id:
                tarefa = t
                break
        
        if not tarefa:
            return {"success": False, "error": f"Tarefa {task_id} não encontrada."}
        
        agora = datetime.now(BRT)
        tarefa["hitl_status"] = "REJECTED"
        tarefa["rejection_reason"] = motivo
        tarefa["rejected_at"] = agora.isoformat()
        
        _salvar_fila_unlocked(fila)
        return {
            "success": True,
            "task_id": task_id,
            "status": "REJECTED",
            "motivo": motivo
        }


def verificar_timeouts() -> List[Dict[str, Any]]:
    """
    Varre a fila por tarefas pendentes que atingiram ou superaram o tempo limite de 60 minutos.
    Auto-aprova e dispara a publicação autônoma.
    """
    processadas = []
    agora = datetime.now(BRT)
    
    with _queue_lock:
        fila = _carregar_fila_unlocked()
        alterado = False
        
        for tarefa in fila:
            if tarefa.get("hitl_status") == "PENDING_APPROVAL":
                expires_at_str = tarefa.get("expires_at")
                expires_dt = _parse_datetime(expires_at_str)
                
                # Se agora >= expires_dt (60 min se passaram)
                if agora >= expires_dt:
                    task_id = tarefa.get("task_id")
                    print(f"⏱️ [Watchdog] Timeout de 60 min atingido para '{task_id}'. Auto-aprovando...")
                    
                    tarefa["hitl_status"] = "AUTO_APPROVED_TIMEOUT"
                    tarefa["auto_published"] = True
                    tarefa["timeout_triggered_at"] = agora.isoformat()
                    
                    try:
                        from instagram_poster import publicar_post_ondemand
                        slide_paths = tarefa.get("slide_paths", [])
                        legenda = tarefa.get("caption", "")
                        res_pub = publicar_post_ondemand(slide_paths, legenda)
                        
                        tarefa["publish_result"] = res_pub
                        tarefa["published_at"] = datetime.now(BRT).isoformat()
                        if res_pub.get("success", False):
                            tarefa["hitl_status"] = "PUBLISHED"
                        else:
                            tarefa["hitl_status"] = "PUBLISH_FAILED"
                            tarefa["publish_error"] = res_pub.get("error")
                    except Exception as e_pub:
                        tarefa["hitl_status"] = "PUBLISH_FAILED"
                        tarefa["publish_error"] = str(e_pub)
                    
                    processadas.append(tarefa)
                    alterado = True
        
        if alterado:
            _salvar_fila_unlocked(fila)
            
    return processadas


def _watchdog_loop(intervalo_segundos: int = 30) -> None:
    """Loop em segundo plano do daemon do Watchdog."""
    print("🚀 [Watchdog Daemon] Iniciado com verificação a cada 30 segundos.")
    while not _stop_event.is_set():
        try:
            verificar_timeouts()
        except Exception as e:
            print(f"⚠️ [Watchdog Daemon] Erro na iteração: {e}")
        
        # Dorme de forma interrompível
        _stop_event.wait(intervalo_segundos)
    print("🛑 [Watchdog Daemon] Finalizado com sucesso.")


def iniciar_watchdog_daemon(intervalo_segundos: int = 30) -> None:
    """Inicia o daemon do Watchdog se ainda não estiver em execução."""
    global _watchdog_thread, _stop_event
    if _watchdog_thread and _watchdog_thread.is_alive():
        return
    
    _stop_event.clear()
    _watchdog_thread = threading.Thread(
        target=_watchdog_loop,
        args=(intervalo_segundos,),
        daemon=True,
        name="AllNewsWatchdogDaemon"
    )
    _watchdog_thread.start()


def parar_watchdog_daemon() -> None:
    """Interrompe o daemon de forma limpa."""
    global _watchdog_thread, _stop_event
    _stop_event.set()
    if _watchdog_thread and _watchdog_thread.is_alive():
        _watchdog_thread.join(timeout=2)
    _watchdog_thread = None
