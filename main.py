import streamlit as st
import sqlite3
import os
import time
import base64

# Importe as funções de inicialização (se necessário)
from init_db import init_database, init_samge_database

# Caminho onde o DB será criado
db_path = "database/app_data.db"

# Verifica se o banco já existe. Caso não exista, cria.
if not os.path.exists(db_path):
    init_database()
    init_samge_database()

# --------------------------------------------------
# Configuração da página
# --------------------------------------------------
# Renomeie o page_title para "Home" (aparece na aba do navegador)
st.set_page_config(
    page_title="Home",
    page_icon="♾️",
    layout="centered"
)

# --------------------------------------------------
# Função auxiliar para converter imagem em base64
# --------------------------------------------------
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Caminho para a imagem de fundo
img_path = os.path.join("public", "assets", "plano.jpg")
img_base64 = get_base64_of_bin_file(img_path)

# --------------------------------------------------
# CSS para imagem de fundo e customização da sidebar
# --------------------------------------------------
BACKGROUND_CSS = f"""
<style>
/* Fundo da aplicação */
.stApp {{
    background: url("data:image/jpg;base64,{img_base64}");
    background-size: cover;
    background-position: center;
}}

/* Força a cor de fundo da sidebar */
[data-testid="stSidebar"] > div:first-child {{
    background-color: rgba(0, 0, 0, 0.6) !important;
}}

</style>
"""
st.markdown(BACKGROUND_CSS, unsafe_allow_html=True)

# --------------------------------------------------
# Título e descrição do sistema
# --------------------------------------------------
st.markdown(
    """
    # CICA
 
    #### Cadastro de Iniciativas Estruturantes da Compensação Ambiental
    *Módulo de Construção de Regras de Negócio (financeiro | insumos)* - SAMGePlan 2025
 
    ---
 
    #### Planejamento Compensação Ambiental - FCA 2025
    *Iniciativas Estruturantes 2024/25*
 
    ---
 
    """
)
 

# --------------------------------------------------
# Funções de banco de dados
# --------------------------------------------------
def buscar_usuario(cpf):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nome_completo, email, setor_demandante, perfil FROM tf_usuarios WHERE cpf = ?", (cpf,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario  # Retorna None se não existir

def atualizar_setor(cpf, novo_setor):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tf_usuarios SET setor_demandante = ? WHERE cpf = ?", (novo_setor, cpf))
    conn.commit()
    conn.close()

def obter_setores_demandantes():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT nome_demandante FROM td_demandantes ORDER BY nome_demandante")
    setores = [row[0] for row in cursor.fetchall()]
    conn.close()
    return setores

def validar_cpf(cpf):
    return cpf.isdigit() and len(cpf) == 11

# --------------------------------------------------
# Inicialização de sessão
# --------------------------------------------------
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False
    st.session_state["perfil"] = None

# --------------------------------------------------
# Área de Login
# --------------------------------------------------
st.subheader("🔐 Login")
st.markdown("**Insira seu CPF para acessar o sistema**")

cpf_input = st.text_input("CPF", max_chars=11, placeholder="Digite seu CPF (somente números)")

if cpf_input:
    if not validar_cpf(cpf_input):
        st.error("CPF inválido! Digite apenas números, com 11 dígitos.")
    else:
        usuario = buscar_usuario(cpf_input)

        if usuario:
            # Usuário encontrado
            nome_completo, email, setor_demandante, perfil = usuario
            st.success("Usuário encontrado! Verifique suas informações abaixo.")

            st.text_input("Nome Completo", value=nome_completo, disabled=True)
            st.text_input("E-mail Institucional", value=email, disabled=True)

            # Obtém a lista de setores demandantes
            lista_setores = obter_setores_demandantes()

            if "editar_setor" not in st.session_state:
                st.session_state["editar_setor"] = False

            st.session_state["editar_setor"] = st.toggle("Editar Setor", value=st.session_state["editar_setor"])

            if st.session_state["editar_setor"]:
                # Editando setor
                if lista_setores:
                    novo_setor = st.selectbox(
                        "Selecione o novo setor", 
                        lista_setores, 
                        index=lista_setores.index(setor_demandante) if setor_demandante in lista_setores else 0
                    )
                else:
                    novo_setor = st.text_input("Setor Demandante (Nenhum setor cadastrado)", value=setor_demandante)

                if st.button("✅ Salvar Alteração"):
                    atualizar_setor(cpf_input, novo_setor)
                    st.success("✅ Setor atualizado com sucesso!")
                    time.sleep(2)
                    st.session_state["editar_setor"] = False
                    st.rerun()
            else:
                # Exibe setor sem edição
                if lista_setores and setor_demandante in lista_setores:
                    st.selectbox("Setor Demandante", lista_setores, index=lista_setores.index(setor_demandante), disabled=True)
                else:
                    st.text_input("Setor Demandante", value=setor_demandante, disabled=True)

            # Armazena dados na sessão
            st.session_state["usuario_logado"] = True
            st.session_state["cpf"] = cpf_input
            st.session_state["nome"] = nome_completo
            st.session_state["email"] = email
            st.session_state["setor"] = setor_demandante
            st.session_state["perfil"] = perfil

        else:
            # Usuário não cadastrado
            st.error("Usuário não cadastrado no sistema. Entre em contato com o administrador.")

# --------------------------------------------------
# Se logado, exibe mensagens e opções
# --------------------------------------------------
if st.session_state["usuario_logado"]:
    st.success(f"✅ Bem-vindo, {st.session_state['nome']}!")
    
    # Configura a sidebar com título "Home" e opções
    with st.sidebar:
        st.title("Home")
        if st.session_state["perfil"] == "admin":
            st.warning("🛠 Modo Administrador Ativado")
        st.success("Você está autenticado. Navegue pelo menu lateral.")
        
        if st.button("🚪 Sair"):
            st.session_state["usuario_logado"] = False
            st.session_state["perfil"] = None
            st.rerun()
else:
    st.sidebar.warning("🔒 Faça login para acessar o sistema.")
