import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Briefing Personalizado", page_icon="☕", layout="centered")

# --- CONEXÃO COM O GOOGLE SHEETS ---
def conectar_banco():
    try:
        # Pega a chave dos segredos do Streamlit
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        json_key = json.loads(st.secrets["gcp_service_account"]["json_key"])
        credentials = Credentials.from_service_account_info(json_key, scopes=scopes)
        client = gspread.authorize(credentials)
        # Abre a planilha pelo nome
        return client.open("noticias_db").sheet1
    except Exception as e:
        st.error(f"Erro ao conectar no banco de dados: {e}")
        return None

# --- INTERFACE DO SITE ---
st.title("☕ Seu Briefing Matinal")
st.write("Receba notícias resumidas por IA, personalizadas para você, todos os dias às 07:00.")

with st.form("cadastro"):
    nome = st.text_input("Seu Nome:")
    email = st.text_input("Seu E-mail:")
    
    st.write("---")
    st.write("### 🗞️ O que você quer receber?")
    
    col1, col2 = st.columns(2)
    with col1:
        tema_mercado = st.checkbox("💰 Mercado & Finanças")
        tema_tech = st.checkbox("📱 Tech & Inovação")
    with col2:
        tema_motos = st.checkbox("🏍️ Motos & Estradas")
        tema_fofoca = st.checkbox("✨ Fofoca & Lazer")
        
    submitted = st.form_submit_button("✅ Inscrever-me Gratuitamente")

    if submitted:
        if not email or not nome:
            st.warning("Por favor, preencha nome e e-mail!")
        else:
            sheet = conectar_banco()
            if sheet:
                # Cria a linha de dados: Nome, Email, Merc, Tech, Motos, Fofoca (True/False)
                # Converter True/False para "Sim"/"Não" fica mais bonito na planilha
                dados = [
                    nome, 
                    email, 
                    "Sim" if tema_mercado else "Não",
                    "Sim" if tema_tech else "Não",
                    "Sim" if tema_motos else "Não",
                    "Sim" if tema_fofoca else "Não"
                ]
                
                # Salva no Google Sheets
                try:
                    sheet.append_row(dados)
                    st.success(f"Show, {nome}! Você está inscrito! 🚀")
                    st.balloons() # Solta balões na tela!
                except Exception as e:
                    st.error("Erro ao salvar sua inscrição. Tente novamente.")
