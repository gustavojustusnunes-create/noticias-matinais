import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Briefing Personalizado",
    page_icon="☕",
    layout="centered"
)

# Título e Subtítulo
st.title("☕ Seu Briefing Matinal")
st.write("Receba notícias resumidas por IA, direto no seu e-mail, todos os dias às 07:00.")

# Formulário de Inscrição
with st.form("cadastro"):
    nome = st.text_input("Seu Nome:")
    email = st.text_input("Seu E-mail:")
    
    st.write("---")
    st.write("### 🗞️ O que você quer receber?")
    
    # As opções de escolha
    col1, col2 = st.columns(2)
    with col1:
        tema_mercado = st.checkbox("💰 Mercado & Finanças")
        tema_tech = st.checkbox("📱 Tech & Inovação")
    with col2:
        tema_motos = st.checkbox("🏍️ Motos & Estradas")
        tema_fofoca = st.checkbox("✨ Fofoca & Lazer")
        
    st.write("")
    submitted = st.form_submit_button("✅ Inscrever-me Gratuitamente")

    if submitted:
        if email:
            # Por enquanto só mostramos na tela, depois vamos salvar no banco
            st.success(f"Show, {nome}! Você receberá o briefing no e-mail: {email}")
            st.json({
                "Nome": nome,
                "E-mail": email,
                "Temas": [tema_mercado, tema_tech, tema_motos, tema_fofoca]
            })
        else:
            st.error("Por favor, preencha o seu e-mail!")

st.markdown("---")
st.caption("Desenvolvido por Gustavo AI • Powered by Gemini")
