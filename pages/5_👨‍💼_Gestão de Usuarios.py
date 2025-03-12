import streamlit as st
import os
import sqlite3
import math

# -------------------------------------------------------------------
# Configurações e inicialização do banco de dados
# -------------------------------------------------------------------
db_path = "database/app_data.db"

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS tf_usuarios")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tf_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            email TEXT NOT NULL,
            setor_demandante TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'comum'
        )
    """)
    conn.commit()
    conn.close()

if not os.path.exists(db_path):
    init_db()

# -------------------------------------------------------------------
# Autenticação (verifica se está logado e se é admin)
# -------------------------------------------------------------------
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

perfil = st.session_state.get("perfil", "comum")
if perfil != "admin":
    st.error("🚫 Acesso restrito: somente administradores podem acessar esta página.")
    st.stop()

# -------------------------------------------------------------------
# Configuração da página
# -------------------------------------------------------------------
st.set_page_config(page_title="Gestão de Usuários", page_icon="🛠", layout="wide")
st.title("Gestão de Usuários - Administração")

# -------------------------------------------------------------------
# Funções de banco de dados
# -------------------------------------------------------------------
def get_all_users():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tf_usuarios")
    users = cursor.fetchall()
    conn.close()
    return users

def update_user(user_id, cpf, nome_completo, email, setor_demandante, perfil_user):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tf_usuarios 
        SET cpf = ?, nome_completo = ?, email = ?, setor_demandante = ?, perfil = ?
        WHERE id = ?
    """, (cpf, nome_completo, email, setor_demandante, perfil_user, user_id))
    conn.commit()
    conn.close()

def create_user(cpf, nome_completo, email, setor_demandante, perfil_user):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, (cpf, nome_completo, email, setor_demandante, perfil_user))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tf_usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# -------------------------------------------------------------------
# Auxiliar para recarregar a página
# -------------------------------------------------------------------
def rerun():
    st.rerun()

# Você não precisa instalar math via pip. 
# 'math' é um módulo interno do Python.
# Ele já vem incluso na biblioteca padrão.
# pip install math não é necessário (e nem existe).
# from math import something  # se quiser usar funções do math.

# -------------------------------------------------------------------
# CSS para dar aparência de "card" e para o card na sidebar
# -------------------------------------------------------------------
CARD_CSS = """
<style>
.card {
  background-color: #f7f7f7;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 0.5rem;
  padding: 0.5rem;
  margin: 0.5rem 0;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.card-header {
  margin-bottom: 0.5rem;
}
.card-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}
.card-sector {
  font-size: 0.9rem;
  color: #f39c12;
  font-weight: 500;
  margin-bottom: 0.3rem;
}
.card-description {
  margin: 0;
  color: #9ca3af;
  font-size: 0.875rem;
}
.card-content p {
  margin: 0.25rem 0;
  font-size: 0.90rem;
}
.card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
/* Inputs no modo edição */
.card-content input[type="text"], .card-content select {
  width: 100%;
  margin: 0.25rem 0 0.5rem 0;
  padding: 0.3rem;
  border: 1px solid #4b5563;
  border-radius: 0.25rem;
  background-color: #2d2d2d;
  color: #fff;
}
/* Botões */
.stButton>button {
  background-color: #374151;
  color: #fff;
  border: none;
  border-radius: 0.25rem;
  padding: 0.3rem 0.75rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.stButton>button:hover {
  background-color: #4b5563;
}
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# Lógica principal
# -------------------------------------------------------------------
users = get_all_users()

if "edit_data" not in st.session_state:
    st.session_state["edit_data"] = {}

def init_edit_data(user_id, cpf="", nome="", email="", setor="", perfil="comum"):
    st.session_state["edit_data"][user_id] = {
        "cpf": cpf,
        "nome_completo": nome,
        "email": email,
        "setor_demandante": setor,
        "perfil": perfil
    }

def render_card(user_id, is_new=False):
    """Renderiza um card (sem usar 'with container:')."""
    # Início do card
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    if not is_new:
        user_data = [u for u in users if u[0] == user_id]
        if not user_data:
            st.error("Usuário não encontrado!")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        _, cpf, nome_completo, email, setor_demandante, perfil_user = user_data[0]
    else:
        cpf = ""
        nome_completo = ""
        email = ""
        setor_demandante = ""
        perfil_user = "comum"

    if user_id not in st.session_state["edit_data"]:
        init_edit_data(user_id, cpf, nome_completo, email, setor_demandante, perfil_user)

    editing = (st.session_state.get("edit_user_id") == user_id)

    if editing:
        # Título
        st.markdown("""
          <div class="card-header">
            <h2 class="card-title">Editando Usuário</h2>
          </div>
        """, unsafe_allow_html=True)

        st.session_state["edit_data"][user_id]["cpf"] = st.text_input(
            "CPF", 
            value=st.session_state["edit_data"][user_id]["cpf"], 
            key=f"cpf_{user_id}"
        )
        st.session_state["edit_data"][user_id]["nome_completo"] = st.text_input(
            "Nome Completo", 
            value=st.session_state["edit_data"][user_id]["nome_completo"], 
            key=f"nome_{user_id}"
        )
        st.session_state["edit_data"][user_id]["email"] = st.text_input(
            "Email", 
            value=st.session_state["edit_data"][user_id]["email"], 
            key=f"email_{user_id}"
        )
        st.session_state["edit_data"][user_id]["setor_demandante"] = st.text_input(
            "Setor Demandante", 
            value=st.session_state["edit_data"][user_id]["setor_demandante"], 
            key=f"setor_{user_id}"
        )
        st.session_state["edit_data"][user_id]["perfil"] = st.selectbox(
            "Perfil", 
            ["comum", "admin"], 
            index=0 if st.session_state["edit_data"][user_id]["perfil"] == "comum" else 1,
            key=f"perfil_{user_id}"
        )

        st.markdown("<div class='card-footer'>", unsafe_allow_html=True)
        if st.button("💾 Salvar", key=f"save_{user_id}"):
            data = st.session_state["edit_data"][user_id]
            if is_new:
                # Criar
                try:
                    create_user(
                        data["cpf"], 
                        data["nome_completo"], 
                        data["email"], 
                        data["setor_demandante"], 
                        data["perfil"]
                    )
                    st.success("Usuário adicionado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao adicionar usuário: {e}")
            else:
                # Atualizar
                try:
                    update_user(
                        user_id,
                        data["cpf"], 
                        data["nome_completo"], 
                        data["email"], 
                        data["setor_demandante"], 
                        data["perfil"]
                    )
                    st.success("Usuário atualizado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao atualizar usuário: {e}")

            st.session_state["edit_user_id"] = None
            rerun()

        if st.button("❌ Cancelar", key=f"cancel_{user_id}"):
            st.session_state["edit_user_id"] = None
            if is_new:
                st.session_state["edit_data"].pop(user_id, None)
            rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Visualização
        if is_new:
            st.markdown("""
            <div class="card-header">
              <h2 class="card-title">Novo Usuário</h2>
              <p class="card-description">Clique para adicionar um novo usuário</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="card-header">
              <h2 class="card-title">{nome_completo}</h2>
              <p class="card-sector">{setor_demandante}</p>
              <p class="card-description">CPF: {cpf}</p>
            </div>
            <div class="card-content">
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Perfil:</strong> {perfil_user}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='card-footer'>", unsafe_allow_html=True)
        if is_new:
            if st.button("➕ Adicionar", key="add_new_btn"):
                st.session_state["edit_user_id"] = user_id
                rerun()
        else:
            if st.button("✏️ Editar", key=f"edit_btn_{user_id}"):
                st.session_state["edit_user_id"] = user_id
                rerun()
            if st.button("🗑 Excluir", key=f"delete_btn_{user_id}"):
                delete_user(user_id)
                st.success("Usuário excluído com sucesso!")
                rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Fecha a div.card
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Montando a página
# -------------------------------------------------------------------

# 1) Card de Novo Usuário na Sidebar
with st.sidebar:
    st.header("Adicionar Novo Usuário")
    render_card(user_id="new_user", is_new=True)

# 2) Lista de Usuários na página principal, em colunas (3 por linha)
def chunkify(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

CARDS_PER_ROW = 3

st.subheader("Usuários Existentes")
all_users = get_all_users()
rows = list(chunkify(all_users, CARDS_PER_ROW))

for row_users in rows:
    # Cria colunas de acordo com quantos usuários tem nessa linha
    cols = st.columns(len(row_users))
    for col, user in zip(cols, row_users):
        with col:
            render_card(user_id=user[0], is_new=False)
