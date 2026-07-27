"""
sheets_db.py — Integração com Google Sheets (banco de dados do All News Journal)
Inclui: conexão, histórico de notícias, logs de envio.
"""
import json
import hashlib
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from config import GCP_JSON, GOOGLE_SHEETS_ID


def conectar_banco():
    """Abre a planilha e retorna (sheet_usuarios, sheet_historico, sheet_logs)."""
    try:
        creds_dict = json.loads(GCP_JSON)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        if GOOGLE_SHEETS_ID:
            planilha = client.open_by_key(GOOGLE_SHEETS_ID)
        else:
            planilha = client.open("noticias_db")

        sheet_usuarios = planilha.sheet1

        try:
            sheet_historico = planilha.worksheet("historico")
        except gspread.exceptions.WorksheetNotFound:
            sheet_historico = planilha.add_worksheet(title="historico", rows=5000, cols=3)
            sheet_historico.append_row(["hash", "titulo", "data"])

        try:
            sheet_logs = planilha.worksheet("logs")
        except gspread.exceptions.WorksheetNotFound:
            sheet_logs = planilha.add_worksheet(title="logs", rows=5000, cols=5)
            sheet_logs.append_row(["data", "nome", "email", "status", "temas"])

        return planilha, sheet_usuarios, sheet_historico, sheet_logs

    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None, None, None, None


def obter_coluna_editorial(planilha):
    """Lê a aba 'Editorial' e retorna o texto agendado para hoje, se houver."""
    try:
        try:
            sheet_editorial = planilha.worksheet("Editorial")
        except gspread.exceptions.WorksheetNotFound:
            sheet_editorial = planilha.add_worksheet(title="Editorial", rows=100, cols=3)
            sheet_editorial.append_row(["data", "titulo", "texto"])
            return None

        registros = sheet_editorial.get_all_records()
        hoje = datetime.now().strftime("%d/%m/%Y")
        for r in reversed(registros):  # Pega o último caso haja vários
            if str(r.get("data", "")).strip() == hoje:
                texto = str(r.get("texto", "")).strip()
                if texto:
                    return {
                        "titulo": str(r.get("titulo") or r.get("título", "")).strip(),
                        "texto": texto
                    }
    except Exception as e:
        print(f"⚠️ Erro ao ler aba Editorial: {e}")
    return None


def gerar_hash(titulo, link):
    """Gera hash MD5 único para deduplicação de notícias."""
    return hashlib.md5(f"{titulo}{link}".encode("utf-8")).hexdigest()


def carregar_historico(sheet_historico):
    """Carrega hashes dos últimos 30 dias e remove entradas antigas."""
    try:
        registros = sheet_historico.get_all_records()
        if not registros:
            return set()

        limite  = datetime.now() - timedelta(days=30)
        hashes  = set()
        remover = []

        for i, r in enumerate(registros, start=2):
            try:
                data = datetime.strptime(r.get("data", "")[:10], "%d/%m/%Y")
                if data >= limite:
                    hashes.add(r["hash"])
                else:
                    remover.append(i)
            except Exception:
                hashes.add(r.get("hash", ""))

        for idx in reversed(remover):
            try:
                sheet_historico.delete_rows(idx)
            except Exception:
                pass

        if remover:
            print(f"   🧹 Histórico: {len(remover)} entradas antigas removidas.")

        print(f"   🗂️ Histórico: {len(hashes)} notícias nos últimos 30 dias.")
        return hashes

    except Exception as e:
        print(f"⚠️ Histórico indisponível: {e}")
        return set()


def salvar_no_historico(sheet_historico, noticias_novas):
    """Salva hashes das novas notícias no histórico para evitar duplicatas futuras."""
    hoje   = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        [gerar_hash(n["titulo"], n["link"]), n["titulo"][:80], hoje]
        for n in noticias_novas
    ]
    if linhas:
        sheet_historico.append_rows(linhas)


def registrar_log(sheet_logs, nome, email, status, temas_enviados):
    """Registra cada envio na aba de logs da planilha."""
    try:
        sheet_logs.append_row([
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            nome, email,
            "✅ Enviado" if status else "❌ Falhou",
            ", ".join(temas_enviados),
        ])
    except Exception as e:
        print(f"⚠️ Log não registrado ({nome}): {e}")


# =============================================================================
# --- BANCO DE DADOS — ALL NEWS FINANCE ---
# =============================================================================

def conectar_aba_finance(planilha=None):
    """Retorna a aba 'all news finance' da planilha, criando-a se não existir."""
    if planilha is None:
        planilha, _, _, _ = conectar_banco()
    if not planilha:
        return None
    try:
        try:
            sheet_finance = planilha.worksheet("all news finance")
        except gspread.exceptions.WorksheetNotFound:
            sheet_finance = planilha.add_worksheet(title="all news finance", rows=2000, cols=4)
            sheet_finance.append_row(["data_inscricao", "nome", "email", "status"])
        return sheet_finance
    except Exception as e:
        print(f"❌ Erro ao conectar na aba all news finance: {e}")
        return None


def adicionar_assinante_finance(nome, email):
    """Adiciona um novo assinante na aba 'all news finance'."""
    sheet_finance = conectar_aba_finance()
    if not sheet_finance:
        return False, "Falha na conexão com o banco de dados."
    
    try:
        email_limpo = email.strip().lower()
        nome_limpo = nome.strip()
        registros = sheet_finance.get_all_records()
        
        for idx, reg in enumerate(registros, start=2):
            if str(reg.get("email", reg.get("E-mail", reg.get("Email", "")))).strip().lower() == email_limpo:
                # Se estava cancelado, reativa
                if str(reg.get("status", reg.get("Status", ""))).strip().lower() == "cancelado":
                    sheet_finance.update_cell(idx, 4, "ativo")
                    return True, "Sua assinatura foi reativada com sucesso!"
                return True, "Este e-mail já está inscrito no All News Finance."
        
        hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet_finance.append_row([hoje, nome_limpo, email_limpo, "ativo"])
        return True, "Inscrição realizada com sucesso no All News Finance!"
    except Exception as e:
        print(f"❌ Erro ao inscrever em finanças: {e}")
        return False, f"Erro ao salvar inscrição: {e}"


def listar_assinantes_finance():
    """Retorna lista de assinantes ativos da aba 'all news finance'."""
    sheet_finance = conectar_aba_finance()
    if not sheet_finance:
        return []
    try:
        registros = sheet_finance.get_all_records()
        ativos = []
        for reg in registros:
            status = str(reg.get("status", reg.get("Status", "ativo"))).strip().lower()
            email = str(reg.get("email", reg.get("E-mail", reg.get("Email", "")))).strip()
            nome = str(reg.get("nome", reg.get("Nome", ""))).strip()
            if email and status != "cancelado":
                ativos.append({"nome": nome or "Leitor(a)", "email": email})
        print(f"   👥 All News Finance: {len(ativos)} assinantes ativos.")
        return ativos
    except Exception as e:
        print(f"⚠️ Erro ao ler assinantes do All News Finance: {e}")
        return []


def cancelar_assinatura_finance(email):
    """Cancela a assinatura alterando status para 'cancelado'."""
    sheet_finance = conectar_aba_finance()
    if not sheet_finance:
        return False, "Falha na conexão."
    try:
        email_limpo = email.strip().lower()
        registros = sheet_finance.get_all_records()
        for idx, reg in enumerate(registros, start=2):
            reg_email = str(reg.get("email", reg.get("E-mail", reg.get("Email", "")))).strip().lower()
            if reg_email == email_limpo:
                sheet_finance.update_cell(idx, 4, "cancelado")
                return True, "Assinatura cancelada com sucesso no All News Finance."
        return False, "E-mail não encontrado."
    except Exception as e:
        return False, f"Erro ao cancelar: {e}"

