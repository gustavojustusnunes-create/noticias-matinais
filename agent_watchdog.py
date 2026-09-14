"""
agent_watchdog.py — Agente Sentinela de Monitoramento e Auto-Recuperação
Vigia continuamente o funcionamento dos outros agentes (All News Journal, All News Finance,
Instagram Poster e Supervisor de Qualidade), registrando a saúde do sistema e disparando
ações de auto-recuperação (self-healing) quando necessário.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Garante saída UTF-8 em terminais Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Timezone de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_FILE = LOGS_DIR / "agent_health.json"
MEMORY_FILE = LOGS_DIR / "supervisor_memory.json"
EDICOES_DIR = Path("edicoes")
EDICOES_FIN_DIR = Path("edicoes_finance")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM    = os.environ.get("RESEND_FROM", "All News Sentinel <onboarding@resend.dev>")
ALERT_EMAIL    = os.environ.get("ALERT_EMAIL", "allnewsjournal@gmail.com")

def enviar_alerta_resend(assunto, mensagem_html):
    """Envia notificação crítica de sentinela caso algum agente falhe."""
    if not RESEND_API_KEY:
        print("   ℹ️ RESEND_API_KEY ausente — alerta por e-mail pulado.")
        return False
    try:
        import requests
        payload = {
            "from": RESEND_FROM,
            "to": [ALERT_EMAIL],
            "subject": assunto,
            "html": mensagem_html,
        }
        res = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        if 200 <= res.status_code < 300:
            print("   ✅ Alerta de sentinela enviado por e-mail.")
            return True
        else:
            print(f"   ⚠️ Falha ao disparar alerta no Resend: HTTP {res.status_code}")
    except Exception as e:
        print(f"   ⚠️ Erro ao enviar e-mail de alerta: {e}")
    return False

def disparar_workflow_recuperacao(workflow_name):
    """Dispara a execução de um workflow do GitHub Actions para auto-recuperação."""
    print(f"   🚨 Disparando auto-recuperação para: {workflow_name}...")
    try:
        cmd = ["gh", "workflow", "run", workflow_name]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            print(f"   ✅ Auto-recuperação acionada via GitHub Actions: {workflow_name}")
            return True
        else:
            print(f"   ⚠️ gh workflow run falhou: {res.stderr.strip()}")
    except Exception as e:
        print(f"   ⚠️ Erro ao acionar recuperação: {e}")
    return False

def inspecionar_agentes():
    agora_brt = datetime.now(BRT)
    hoje_str = agora_brt.strftime("%Y-%m-%d")
    hora_atual = agora_brt.hour + (agora_brt.minute / 60.0)
    dia_semana = agora_brt.weekday()  # 0=Segunda ... 6=Domingo
    
    print(f"\n🛡️  INICIANDO VARREDURA DO AGENTE SENTINELA — {hoje_str} às {agora_brt.strftime('%H:%M')} BRT")
    print("─" * 65)

    agentes_status = {}
    incidentes = []
    auto_recuperacoes = []

    # ── 1. AGENTE ALL NEWS JOURNAL (EDIÇÃO PRINCIPAL) ──
    arquivo_edicao = EDICOES_DIR / f"{hoje_str}.json"
    if arquivo_edicao.exists():
        try:
            dados = json.loads(arquivo_edicao.read_text(encoding="utf-8"))
            cadernos = dados.get("cadernos", {})
            total_noticias = sum(len(n) for n in cadernos.values())
            agentes_status["journal"] = {
                "nome": "All News Journal (Edição Diária)",
                "status": "ONLINE",
                "detalhe": f"Edição publicada com sucesso ({total_noticias} notícias).",
                "ultima_edicao": hoje_str,
                "horario_previsto": "05:20 BRT",
                "total_itens": total_noticias
            }
            print(f"   🟢 [Journal] ONLINE — Edição {hoje_str} verificada ({total_noticias} matérias).")
        except Exception as e:
            agentes_status["journal"] = {
                "nome": "All News Journal (Edição Diária)",
                "status": "DEGRADED",
                "detalhe": f"Arquivo corrompido: {e}",
                "ultima_edicao": hoje_str,
                "horario_previsto": "05:20 BRT"
            }
            incidentes.append(f"Edição {hoje_str} do Journal está com JSON inválido.")
    else:
        if hora_atual >= 6.25:
            agentes_status["journal"] = {
                "nome": "All News Journal (Edição Diária)",
                "status": "OFFLINE",
                "detalhe": f"Edição de hoje ({hoje_str}) não foi gerada até às {agora_brt.strftime('%H:%M')} BRT.",
                "ultima_edicao": "Pendente",
                "horario_previsto": "05:20 BRT"
            }
            incidentes.append(f"All News Journal não gerou a edição matinal de {hoje_str}.")
            if disparar_workflow_recuperacao("daily.yml"):
                auto_recuperacoes.append("daily.yml disparado para auto-recuperação.")
                agentes_status["journal"]["status"] = "RECOVERING"
            print(f"   🔴 [Journal] OFFLINE / RECUPERANDO — Edição ausente após as 06:15.")
        else:
            agentes_status["journal"] = {
                "nome": "All News Journal (Edição Diária)",
                "status": "SCHEDULED",
                "detalhe": "Aguardando horário de disparo (05:20 BRT).",
                "ultima_edicao": "Aguardando",
                "horario_previsto": "05:20 BRT"
            }
            print(f"   ⚪ [Journal] AGENDADO — Aguardando horário matinal.")

    # ── 2. AGENTE ALL NEWS FINANCE ──
    if dia_semana < 5:  # Segunda a Sexta
        arquivo_fin = EDICOES_FIN_DIR / f"{hoje_str}.json"
        if arquivo_fin.exists():
            try:
                dados_fin = json.loads(arquivo_fin.read_text(encoding="utf-8"))
                cadernos_fin = dados_fin.get("cadernos", {})
                total_fin = sum(len(n) for n in cadernos_fin.values())
                agentes_status["finance"] = {
                    "nome": "All News Finance",
                    "status": "ONLINE",
                    "detalhe": f"Edição de mercado publicada ({total_fin} análises).",
                    "ultima_edicao": hoje_str,
                    "horario_previsto": "05:25 BRT",
                    "total_itens": total_fin
                }
                print(f"   🟢 [Finance] ONLINE — Edição de finanças verificada ({total_fin} matérias).")
            except Exception as e:
                agentes_status["finance"] = {
                    "nome": "All News Finance",
                    "status": "DEGRADED",
                    "detalhe": str(e),
                    "ultima_edicao": hoje_str,
                    "horario_previsto": "05:25 BRT"
                }
        else:
            if hora_atual >= 6.3:
                agentes_status["finance"] = {
                    "nome": "All News Finance",
                    "status": "OFFLINE",
                    "detalhe": f"Edição financeira de hoje ausente após as 06:20.",
                    "ultima_edicao": "Pendente",
                    "horario_previsto": "05:25 BRT"
                }
                incidentes.append(f"All News Finance não concluiu a edição de {hoje_str}.")
                if disparar_workflow_recuperacao("finance_daily.yml"):
                    auto_recuperacoes.append("finance_daily.yml disparado para auto-recuperação.")
                    agentes_status["finance"]["status"] = "RECOVERING"
                print(f"   🔴 [Finance] OFFLINE / RECUPERANDO — Edição financeira pendente.")
            else:
                agentes_status["finance"] = {
                    "nome": "All News Finance",
                    "status": "SCHEDULED",
                    "detalhe": "Aguardando horário de disparo (05:25 BRT).",
                    "ultima_edicao": "Aguardando",
                    "horario_previsto": "05:25 BRT"
                }
                print(f"   ⚪ [Finance] AGENDADO — Dia útil aguardando horário.")
    else:
        agentes_status["finance"] = {
            "nome": "All News Finance",
            "status": "WEEKEND_REST",
            "detalhe": "Mercados fechados aos fins de semana.",
            "ultima_edicao": "Segunda-feira",
            "horario_previsto": "Seg-Sex às 05:25"
        }
        print(f"   ⚪ [Finance] EM REPOUSO — Fim de semana (mercados fechados).")

    # ── 3. AGENTE INSTAGRAM POSTER ──
    memoria_data = {}
    if MEMORY_FILE.exists():
        try:
            memoria_data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except:
            pass
    ultima_postagem_ig = memoria_data.get("ultima_edicao_instagram", "")
    
    if ultima_postagem_ig == hoje_str:
        agentes_status["instagram"] = {
            "nome": "Instagram Daily Posts",
            "status": "ONLINE",
            "detalhe": f"Posts da edição de {hoje_str} gerados e registrados.",
            "ultima_edicao": hoje_str,
            "horario_previsto": "09:15 BRT"
        }
        print(f"   🟢 [Instagram] ONLINE — Posts de {hoje_str} entregues.")
    else:
        if hora_atual >= 12.5:
            agentes_status["instagram"] = {
                "nome": "Instagram Daily Posts",
                "status": "PENDING",
                "detalhe": f"Ainda não postou a edição de hoje ({hoje_str}).",
                "ultima_edicao": ultima_postagem_ig or "N/A",
                "horario_previsto": "09:15 BRT"
            }
            print(f"   🟡 [Instagram] PENDENTE — Aguardando nova postagem.")
        else:
            agentes_status["instagram"] = {
                "nome": "Instagram Daily Posts",
                "status": "SCHEDULED",
                "detalhe": "Aguardando horário agendado (09:15 BRT).",
                "ultima_edicao": ultima_postagem_ig or "N/A",
                "horario_previsto": "09:15 BRT"
            }
            print(f"   ⚪ [Instagram] AGENDADO — Previsto para 09:15 BRT.")

    # ── 4. AGENTE SUPERVISOR DE QUALIDADE DA IA ──
    erros_acumulados = len(memoria_data.get("erros", []))
    fotos_recentes = len(memoria_data.get("imagens_recentes", []))
    agentes_status["supervisor"] = {
        "nome": "AI Quality Supervisor",
        "status": "ONLINE",
        "detalhe": f"Auditoria cognitiva ativa. {erros_acumulados} lições de aprendizado acumuladas.",
        "licoes_aprendidas": erros_acumulados,
        "fotos_rastreadas": fotos_recentes
    }
    print(f"   🟢 [Supervisor IA] ONLINE — {erros_acumulados} lições ativas na memória.")

    # ── 5. AGENTE SENTINELA (AUTO-AVALIAÇÃO) ──
    agentes_status["watchdog"] = {
        "nome": "Watchdog Sentinela",
        "status": "ACTIVE",
        "detalhe": "Monitoramento em tempo real operando com sucesso.",
        "ultimo_scan": agora_brt.strftime("%Y-%m-%d %H:%M BRT"),
        "incidentes_abertos": len(incidentes)
    }

    if any(a.get("status") == "OFFLINE" for a in agentes_status.values()):
        sistema_geral = "ALERT"
    elif any(a.get("status") in ("RECOVERING", "DEGRADED") for a in agentes_status.values()):
        sistema_geral = "WARNING"
    else:
        sistema_geral = "HEALTHY"

    relatorio = {
        "timestamp_scan": agora_brt.isoformat(),
        "data_hoje": hoje_str,
        "sistema_geral": sistema_geral,
        "incidentes": incidentes,
        "auto_recuperacoes": auto_recuperacoes,
        "agentes": agentes_status
    }

    HEALTH_FILE.write_text(json.dumps(relatorio, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Relatório de saúde salvo em {HEALTH_FILE}. Status Geral: {sistema_geral}")

    if incidentes and sistema_geral == "ALERT":
        corpo_html = f"""
        <h2>🚨 Alerta do Agente Sentinela — All News Journal</h2>
        <p>Durante a varredura das <b>{agora_brt.strftime('%H:%M')} BRT</b>, foram detectados os seguintes problemas:</p>
        <ul>
            {''.join(f'<li><b>{inc}</b></li>' for inc in incidentes)}
        </ul>
        <p><b>Ações automáticas executadas:</b></p>
        <ul>
            {''.join(f'<li>{rec}</li>' for rec in auto_recuperacoes) if auto_recuperacoes else '<li>Nenhuma ação automática disponível.</li>'}
        </ul>
        <p>Verifique o painel do Streamlit ou as execuções no GitHub Actions.</p>
        """
        enviar_alerta_resend(f"🚨 Alerta Sentinela: Falha em Agentes ({hoje_str})", corpo_html)

    return relatorio

if __name__ == "__main__":
    inspecionar_agentes()
