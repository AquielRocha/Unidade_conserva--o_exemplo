import streamlit as st
import sqlite3
import os
import time

# Importe a função de inicialização
from init_db import init_database
from init_db import init_samge_database

# Caminho onde o DB será criado
db_path = "database/app_data.db"

# Verifica se o banco já existe. Caso não exista, cria.
if not os.path.exists(db_path):
    init_database()
    init_samge_database()

st.set_page_config(
    page_title="SAMGePlan (v.0)",
    page_icon="♾️",
    layout="centered"
    )

# st.sidebar.title("▶️ Início")  # Define o título da barra lateral

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


# 📌 Função para buscar usuário no banco
def buscar_usuario(cpf):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nome_completo, email, setor_demandante, perfil FROM tf_usuarios WHERE cpf = ?", (cpf,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario  # Retorna None se o usuário não existir

# 📌 Função para cadastrar usuário no banco
def cadastrar_usuario(cpf, nome, email, setor, perfil="comum"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil) 
        VALUES (?, ?, ?, ?, ?)""", (cpf, nome, email, setor, perfil))
    conn.commit()
    conn.close()

# 📌 Função para atualizar o setor demandante do usuário
def atualizar_setor(cpf, novo_setor):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE tf_usuarios SET setor_demandante = ? WHERE cpf = ?", (novo_setor, cpf))
    conn.commit()
    conn.close()

# 📌 Função para obter setores demandantes do banco
def obter_setores_demandantes():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT nome_demandante FROM td_demandantes ORDER BY nome_demandante")
    setores = [row[0] for row in cursor.fetchall()]
    conn.close()
    return setores

# 📌 Função para validar CPF (simples, sem algoritmo de validação)
def validar_cpf(cpf):
    return cpf.isdigit() and len(cpf) == 11

# 📌 Inicialização da sessão
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False
    st.session_state["perfil"] = None

st.subheader("🔐 Login")

st.markdown("**Insira seu CPF para acessar o sistema**")
cpf_input = st.text_input("CPF", max_chars=11, placeholder="Digite seu CPF (somente números)")

if cpf_input:
    if not validar_cpf(cpf_input):
        st.error("CPF inválido! Digite apenas números, com 11 dígitos.")
    else:
        usuario = buscar_usuario(cpf_input)

        if usuario:
            # Se o usuário já existe, preencher os campos automaticamente
            nome_completo, email, setor_demandante, perfil = usuario
            st.success("Usuário encontrado! Verifique suas informações abaixo.")

            st.text_input("Nome Completo", value=nome_completo, disabled=True)
            st.text_input("E-mail Institucional", value=email, disabled=True)
            
            # Obtém a lista de setores demandantes
            lista_setores = obter_setores_demandantes()

            # Checkbox para permitir alteração do setor demandante
            # Estado inicial
            if "editar_setor" not in st.session_state:
                st.session_state["editar_setor"] = False

            # Toggle para edição
            st.session_state["editar_setor"] = st.toggle("Editar Setor", value=st.session_state["editar_setor"])

            if st.session_state["editar_setor"]:
                novo_setor = st.selectbox("Selecione o novo setor", lista_setores, index=lista_setores.index(setor_demandante) if setor_demandante in lista_setores else 0)
                
                if st.button("✅ Salvar Alteração"):
                    atualizar_setor(cpf_input, novo_setor)
                    st.success("✅ Setor atualizado com sucesso!")
                    
                    import time
                    time.sleep(2)

                    st.session_state["editar_setor"] = False
                    st.rerun()
            else:
                st.selectbox("Setor Demandante", lista_setores, index=lista_setores.index(setor_demandante) if setor_demandante in lista_setores else 0, disabled=True)

            # 📌 Armazena os dados na sessão
            st.session_state["usuario_logado"] = True
            st.session_state["cpf"] = cpf_input
            st.session_state["nome"] = nome_completo
            st.session_state["email"] = email
            st.session_state["setor"] = setor_demandante
            st.session_state["perfil"] = perfil

        else:
            st.warning("Usuário não cadastrado. Preencha os campos abaixo para se registrar.")

            nome_completo = st.text_input("Nome Completo")
            email = st.text_input("E-mail Institucional")
            
            # Obtém a lista de setores demandantes
            lista_setores = obter_setores_demandantes()

            if lista_setores:
                setor_demandante = st.selectbox("Setor Demandante", lista_setores)
            else:
                setor_demandante = st.text_input("Setor Demandante (Nenhum setor cadastrado)")

            if st.button("Cadastrar"):
                if nome_completo and email and setor_demandante:
                    cadastrar_usuario(cpf_input, nome_completo, email, setor_demandante)
                    st.success("Usuário cadastrado com sucesso! Agora você pode acessar o sistema.")
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos.")

# 📌 Controle de acesso às páginas
if st.session_state["usuario_logado"]:
    st.success(f"✅ Bem-vindo, {st.session_state['nome']}!")
    
    # 🏆 Se for admin, exibe aviso
    if st.session_state["perfil"] == "admin":
        st.sidebar.warning("🛠 Modo Administrador Ativado")

    st.sidebar.success("Você está autenticado. Navegue pelo menu lateral.")

    # 📌 Botão de logout
    if st.sidebar.button("🚪 Sair"):
        st.session_state["usuario_logado"] = False
        st.session_state["perfil"] = None
        st.rerun()
else:
    st.sidebar.warning("🔒 Faça login para acessar o sistema.")