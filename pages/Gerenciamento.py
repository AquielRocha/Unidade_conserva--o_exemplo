import streamlit as st
from db import fetch_processes, insert_process, delete_process, update_process

# Configurações de página
st.set_page_config(
    page_title="Sistema de Gestão de Processos",
    layout="centered",
    initial_sidebar_state="expanded"
)

# CSS para ocultar o item nº1 do menu (normalmente a página principal “app”)
hide_app_style = """
<style>
[data-testid="stSidebarNav"] ul li:nth-child(1) {
    display: none;
}
</style>
"""
st.markdown(hide_app_style, unsafe_allow_html=True)

# CSS para customizar o visual
CUSTOM_CSS = """
<style>
/* Ajusta a cor de fundo e cor do texto global */
body, .css-18e3th9, .css-1d391kg {
    background-color: #1e1e1e !important;
    color: #e8e8e8 !important;
}

/* Títulos */
h1, h2, h3, h4, h5, h6 {
    color: #4CAF50 !important;
}

/* Caixa da barra lateral */
.css-1lcbmhc, .css-1l02zno, .css-12oz5g7 {
    background-color: #2e2e2e !important;
}

/* Expander: borda e espaçamento */
.stExpander {
    border: 1px solid #4CAF50 !important;
    border-radius: 6px;
    margin-bottom: 1rem;
}

/* Cabeçalho do Expander */
.streamlit-expanderHeader {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #4CAF50 !important;
}

/* Conteúdo do Expander */
.stExpanderContent {
    background-color: #2e2e2e !important;
    padding: 0.5rem 1rem !important;
}

/* Botões padrão do Streamlit */
.stButton>button {
    background-color: #4CAF50 !important;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background-color 0.3s ease, transform 0.3s ease;
    margin-right: 0.5rem;
    margin-top: 0.5rem;
}
.stButton>button:hover {
    background-color: #45a049 !important;
    transform: scale(1.03);
}

/* Botão de link (Mandar para o SEI) */
.sei-button {
    padding: 6px 12px;
    background-color: #f0f0f0;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    text-decoration: none;
    transition: background-color 0.3s ease, transform 0.3s ease;
    display: inline-block;
    margin-top: 0.5rem;
}
.sei-button:hover {
    background-color: yellow;
    color: "#fff";
    transform: scale(1.03);
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def main():
    st.title("Sistema de Gestão de Processos")
    st.sidebar.header("Menu de Gerenciamento")
    
    # Formulário para adicionar novo processo
    st.subheader("Adicionar Novo Processo")
    with st.expander("Clique para adicionar"):
        nome = st.text_input("Nome")
        unidade_conservacao = st.text_input("Unidade de Conservação")
        eixo_tematico = st.selectbox("Eixo Temático", ["Educação Ambiental", "Gestão de Recursos", "Sustentabilidade"])
        numero_sei = st.text_input("Número SEI")
        no_sei = st.checkbox("O processo está no SEI?")
        
        if st.button("Salvar Processo"):
            insert_process(nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei)
            st.success("Processo adicionado com sucesso!")
            st.rerun()

    st.subheader("Lista de Processos")
    processos = fetch_processes()
    
    if processos:
        for proc in processos:
            with st.expander(f"{proc[1]} - {proc[2]}"):
                st.write(f"**Eixo Temático:** {proc[3]}")
                st.write(f"**Número SEI:** {proc[4] if proc[4] else 'Não cadastrado'}")
                st.write(f"**Está no SEI?** {'Sim' if proc[5] else 'Não'}")
                
                # Controle do modo de edição utilizando session_state
                edit_key = f"edit_mode_{proc[0]}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                
                if not st.session_state[edit_key]:
                    cols = st.columns([1, 1, 1])  # 3 colunas para botões
                    with cols[0]:
                        if st.button(f"Editar {proc[1]}", key=f"edit_{proc[0]}"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    with cols[1]:
                        if st.button(f"Excluir {proc[1]}", key=f"delete_{proc[0]}"):
                            delete_process(proc[0])
                            st.warning("Processo excluído!")
                            st.rerun()
                    with cols[2]:
                        # Botão para enviar para o SEI (link estilizado como botão)
                        sei_link_html = f"""
                        <a href="https://dsvlabsingular.icmbio.gov.br/interno/rascunhos/novo?id=c4a0ca8107292c3579851221f78347d94cf6c1ca" target="_blank" class="sei-button" style="color: green;">
                            Mandar para o SEI
                        </a>
                        """
                        st.markdown(sei_link_html, unsafe_allow_html=True)
                else:
                    # Formulário de edição
                    with st.form(key=f"edit_form_{proc[0]}"):
                        novo_nome = st.text_input("Nome", proc[1])
                        nova_unidade = st.text_input("Unidade de Conservação", proc[2])
                        novo_eixo = st.selectbox(
                            "Eixo Temático", 
                            ["Educação Ambiental", "Gestão de Recursos", "Sustentabilidade"], 
                            index=["Educação Ambiental", "Gestão de Recursos", "Sustentabilidade"].index(proc[3])
                        )
                        novo_numero_sei = st.text_input("Número SEI", proc[4] if proc[4] else "")
                        novo_no_sei = st.checkbox("O processo está no SEI?", proc[5])
                        
                        submit_edit = st.form_submit_button("Salvar Alterações")
                        if submit_edit:
                            update_process(proc[0], novo_nome, nova_unidade, novo_eixo, novo_numero_sei, novo_no_sei)
                            st.success("Processo atualizado com sucesso!")
                            st.session_state[edit_key] = False
                            st.rerun()

                    if st.button("Cancelar", key=f"cancel_{proc[0]}"):
                        st.session_state[edit_key] = False
                        st.rerun()
    else:
        st.info("Nenhum processo cadastrado ainda.")

if __name__ == "__main__":
    main()
