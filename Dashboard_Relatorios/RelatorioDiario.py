import streamlit as st
from PIL import Image
import base64


icon = Image.open("Colaí.png.png")#Aqui voce coloca o titulo do arquivo da imagem que vc quer colocar como icone do site(essa imagem vai ficar na barra da URL)
st.set_page_config(page_title='Nome que vc preferir', page_icon=icon, layout="centered")#Coloca o titulo do seu site


fundo_do_site = """
<style>
.stApp {
    background-image: url("https://acdn-us.mitiendanube.com/stores/853/995/themes/common/logo-852124537-1693921118-0fc332af4475bdb9e91df6c0a219df6b1693921119-480-0.webp");
    background-size: 400px;
    background-repeat: no-repeat;
    background-position: center 80%;
    background-attachment: fixed;
}
</style>
"""


utilizadores = {
    "Nome de usuario" : "senha" #se quiser acrescentar mais usuarios só ir colocando um nome e senha no dicionario
}

#Parte de conexão com usuario que antecede a entrada do site
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_nome = ""


if not st.session_state.logado:
    st.markdown(fundo_do_site, unsafe_allow_html=True)
    

    _, col_login, _ = st.columns([1, 2, 1])
    
    with col_login:
        st.write("") # 
        st.subheader("Por favor, faça seu login:")
        

        with st.form("form_login"):
            usuario = st.text_input('Usuário:')  
            senha = st.text_input('Senha:', type='password')
            submit = st.form_submit_button('ENTRAR', use_container_width=True)
            
            if submit:
                if utilizadores.get(usuario) == senha:
                    st.session_state.logado = True
                    st.session_state.usuario_nome = usuario
                    st.rerun()
                else:
                    st.error('Usuário ou senha incorretos. Tente novamente!')
#borda lateral com opção de escolha de setor junto com o nome do usario, imagem representando a empresa e opção de sair

else:

    with st.sidebar:
        st.image("GrupoM.A.png", width=300)
   
        with st.container(border=True):
             st.write(f"👤 Usuário: **{st.session_state.usuario_nome}**")
        st.markdown("---")
        
        st.markdown("### Setor:")
        opcao_setor = st.selectbox(
            'Escolha o Setor:',
            ['Integração', 'Produção', 'Expedição', 'Estoque',],
            label_visibility="collapsed"
        )
        
        if opcao_setor == 'Integração':
            st.selectbox(
            "Relatorio Integração"
            )
            st.button("Gerar Relatorio Integração")
            if st.button(" Gerar Relatorio Integração",key="btn_rlt_int" , use_container_width=True):
                         with st.spinner('📝 Gerando relatorio... Aguarde!'):
            st.selectbox(
            "Relatorio Comercial"
            )
            st.button("Gerar Relatorio Comercial")
            st.selectbox(
            "Relatorio TI"
            )
            st.button("Gerar Relatorio TI")
        if opcao_setor == 'Produção':
            st.selectbox(
                "Relatorio Produção"
            )
            st.button("Gerar relatorio Produção")
        if opcao_setor == 'Expedição':
            st.selectbox(
                "Relatorio Expedição"
            )
            st.button("Gerar Relatorio Expedição")
        if opcao_setor == 'Estoque':
            st.selectbox(
                "Relatorio Estoque"
            )
            st.button("Gerar Relatorio Estoque")

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()
    
    
    #Parte frontal do site com uma breve apresentação ao usuario junto com uma apresentação do que é feito (esse painel deve sumir assim que o usuario subir as planilhas para aparecer os relatorios e dashboard)            
    
    st.title(f'Olá, {st.session_state.usuario_nome}! 👋')
    st.markdown("### Bem-vindo ao **Painel de Dashboard e Relatorios** ")
    st.write('Selecione o setor e o  relatorio desejado para visualizar no seu painel.')
    st.markdown("---") 


    