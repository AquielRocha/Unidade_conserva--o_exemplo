import streamlit as st
import sqlite3
import pandas as pd
import os

# ------------------------------------------------------------------------
#           Configurações de Página e Verificação de Login
# ------------------------------------------------------------------------
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login.")
    st.stop()

usuario_cpf   = st.session_state.get("cpf", "000.000.000-00")
usuario_perfil = st.session_state.get("perfil", "padrao")

st.set_page_config(
    page_title="Gestão de Insumos",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

os.makedirs("database", exist_ok=True)
conn = sqlite3.connect("database/app_data.db", check_same_thread=False)
cursor = conn.cursor()

# ------------------------------------------------------------------------
#              Funções Auxiliares
# ------------------------------------------------------------------------
def get_distinct_elementos():
    cursor.execute("SELECT DISTINCT elemento_despesa FROM td_insumos ORDER BY elemento_despesa")
    rows = cursor.fetchall()
    return [row[0] for row in rows if row[0]]

def get_distinct_espec_padrao(elemento=None):
    if elemento:
        cursor.execute("""
            SELECT DISTINCT especificacao_padrao 
              FROM td_insumos 
             WHERE elemento_despesa = ?
          ORDER BY especificacao_padrao
        """, (elemento,))
    else:
        cursor.execute("SELECT DISTINCT especificacao_padrao FROM td_insumos ORDER BY especificacao_padrao")
    rows = cursor.fetchall()
    return [row[0] for row in rows if row[0]]

def get_distinct_insumos(elemento=None, espec=None):
    query = "SELECT DISTINCT descricao_insumo FROM td_insumos WHERE 1=1"
    params = []
    if elemento:
        query += " AND elemento_despesa = ?"
        params.append(elemento)
    if espec:
        query += " AND especificacao_padrao = ?"
        params.append(espec)
    query += " ORDER BY descricao_insumo"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [row[0] for row in rows if row[0]]

def check_existing_insumo(elemento, espec, insumo):
    query = """
        SELECT COUNT(*) 
          FROM td_insumos
         WHERE LOWER(elemento_despesa) = ?
           AND LOWER(especificacao_padrao) = ?
           AND LOWER(descricao_insumo) = ?
    """
    cursor.execute(
        query,
        (elemento.lower(), espec.lower(), insumo.lower())
    )
    (count,) = cursor.fetchone()
    return count > 0

def insert_insumo(elemento, espec_padrao, nome_insumo, preco, origem, situacao, registrado_por):
    cursor.execute("""
        INSERT INTO td_insumos (
            elemento_despesa,
            especificacao_padrao,
            descricao_insumo,
            especificacao_tecnica,
            preco_referencia,
            origem,
            situacao,
            registrado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        elemento or "",
        espec_padrao or "",
        nome_insumo or "",
        "",  # especificacao_tecnica pode ficar vazio
        preco or 0.0,
        origem,
        situacao,
        registrado_por
    ))
    conn.commit()

def update_insumo(insumo_id, elemento, espec_padrao, nome_insumo, espec_tecnica, preco, situacao):
    cursor.execute("""
        UPDATE td_insumos
           SET elemento_despesa = ?,
               especificacao_padrao = ?,
               descricao_insumo = ?,
               especificacao_tecnica = ?,
               preco_referencia = ?,
               situacao = ?
         WHERE id = ?
    """, (
        elemento,
        espec_padrao,
        nome_insumo,
        espec_tecnica,
        preco,
        situacao,
        insumo_id
    ))
    conn.commit()

def get_sugestoes_insumos(perfil):
    if perfil == "cocam":
        query = "SELECT * FROM td_insumos WHERE situacao = 'em análise' ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
    else:
        query = "SELECT * FROM td_insumos WHERE situacao = 'em análise' AND registrado_por = ? ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=[usuario_cpf])
    return df

def get_insumos_ativos():
    query = "SELECT * FROM td_insumos WHERE situacao = 'ativo' ORDER BY id DESC"
    return pd.read_sql_query(query, conn)

def get_insumos_desativados():
    query = "SELECT * FROM td_insumos WHERE situacao = 'desativado' ORDER BY id DESC"
    return pd.read_sql_query(query, conn)

def filtrar_df(df, elemento, espec, insumo):
    """Aplica filtros no DF, se não forem vazios."""
    if elemento:
        df = df[df["elemento_despesa"] == elemento]
    if espec:
        df = df[df["especificacao_padrao"] == espec]
    if insumo:
        df = df[df["descricao_insumo"] == insumo]
    return df


# ------------------------------------------------------------------------
#                 Interface - Cabeçalho
# ------------------------------------------------------------------------
st.subheader("Gestão de Insumos 🔧")
st.markdown("---")


# ------------------------------------------------------------------------
# 1) Formulário de Sugestão Lado Esquerdo
# ------------------------------------------------------------------------
col_form, col_empty, col_filtros = st.columns([10, 0.5, 2])

with col_form:
    st.markdown("### Formulário de Sugestão")
    with st.form(key="form_sugestao_texto_livre"):
        elemento_text = st.text_input("Elemento de Despesa (texto livre)").strip()
        espec_text = st.text_input("Especificação Padrão (texto livre)").strip()
        desc_insumo_text = st.text_input("Descrição do Insumo (texto livre)").strip()
        preco_input = st.number_input("Preço de Referência (R$)", min_value=0.0, step=0.5, value=0.0)

        submitted_livre = st.form_submit_button("Enviar Sugestão")
        if submitted_livre:
            if not elemento_text:
                st.error("O campo 'Elemento de Despesa' é obrigatório!")
            elif not espec_text:
                st.error("O campo 'Especificação Padrão' é obrigatório!")
            elif not desc_insumo_text:
                st.error("O campo 'Descrição do Insumo' é obrigatório!")
            else:
                if check_existing_insumo(elemento_text, espec_text, desc_insumo_text):
                    st.warning("Já existe um item com essa combinação de Elemento, Especificação e Descrição!")
                else:
                    user_setor = st.session_state.get("setor", "desconhecido")
                    insert_insumo(
                        elemento=elemento_text,
                        espec_padrao=espec_text,
                        nome_insumo=desc_insumo_text,
                        preco=preco_input,
                        origem=user_setor,
                        situacao="em análise",
                        registrado_por=usuario_cpf
                    )
                    st.success("Sugestão adicionada com sucesso!")
                    st.rerun()


# ------------------------------------------------------------------------
# 2) Expander de Filtros (Selectboxes)
# ------------------------------------------------------------------------
with col_filtros:
    with st.popover("Filtros de Consulta"):
        # Monta as opções de cada filtro
        todos_elementos = get_distinct_elementos()
        selected_elemento = st.selectbox("Elemento de Despesa:", options=[""] + todos_elementos)

        if selected_elemento:
            especs = get_distinct_espec_padrao(selected_elemento)
        else:
            especs = get_distinct_espec_padrao()  # sem filtro

        selected_espec = st.selectbox("Especificação Padrão:", options=[""] + especs)

        if selected_espec:
            insumos = get_distinct_insumos(selected_elemento, selected_espec)
        else:
            insumos = get_distinct_insumos(selected_elemento)  # filtra só por elemento, se houver
        selected_insumo = st.selectbox("Descrição do Insumo:", options=[""] + insumos)

        st.info("Esses filtros serão aplicados às tabelas abaixo.")


st.markdown("---")

# =============================================================================
# 3) Tabela de Itens Sugeridos (Em Análise) - Aplica Filtro
# =============================================================================
st.markdown("### Itens Sugeridos (Em Análise)")

df_sugestoes = get_sugestoes_insumos(usuario_perfil)
df_sugestoes = filtrar_df(df_sugestoes, selected_elemento, selected_espec, selected_insumo)

if df_sugestoes.empty:
    st.info("Não há itens sugeridos em análise no momento (ou não correspondem aos filtros).")
else:
    # Definindo config de colunas conforme o perfil:
    if usuario_perfil == "admin":
        # Admin pode editar tudo (menos ID). 'situacao' é SelectboxColumn, 
        # pois tem opções definidas.
        col_config_sug = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=False),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=False),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=False),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=False
            ),
            "situacao": st.column_config.SelectboxColumn(
                "Situação", options=["em análise", "ativo", "desativado"], width="small"
            ),
            "origem": st.column_config.TextColumn("Origem", disabled=False),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=False),
        }
    elif usuario_perfil == "cocam":
        # cocam pode editar elemento, espec, descrição, preço e situacao
        col_config_sug = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=False),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=False),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=False),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=False
            ),
            "situacao": st.column_config.SelectboxColumn(
                "Situação", options=["em análise", "ativo", "desativado"], width="small"
            ),
            "origem": st.column_config.TextColumn("Origem", disabled=True),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
        }
    else:
        # perfil comum: pode editar apenas espec, descrição e preço
        col_config_sug = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=True),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=False),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=False),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=False
            ),
            "situacao": st.column_config.TextColumn("Situação", disabled=True),
            "origem": st.column_config.TextColumn("Origem", disabled=True),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
        }

    # Ordenando as colunas no DF
    df_sugestoes = df_sugestoes[[
        "id", "elemento_despesa", "especificacao_padrao",
        "descricao_insumo", "preco_referencia", "situacao",
        "origem", "registrado_por"
    ]]

    edited_df_sug = st.data_editor(
        df_sugestoes,
        column_config=col_config_sug,
        use_container_width=True,
        hide_index=True,
        key="editor_sugestoes"
    )

    if st.button("Salvar Alterações em Itens Sugeridos"):
        for index, row in edited_df_sug.iterrows():
            update_insumo(
                insumo_id=row["id"],
                elemento=row["elemento_despesa"],
                espec_padrao=row["especificacao_padrao"],
                nome_insumo=row["descricao_insumo"],
                espec_tecnica="",
                preco=row["preco_referencia"],
                situacao=row["situacao"]
            )
        st.success("Sugestões atualizadas com sucesso!")
        st.rerun()

st.markdown("---")

# =============================================================================
# 4) Tabela de Itens Ativos - Aplica Filtro
# =============================================================================
st.markdown("### Itens Ativos")

df_ativos = get_insumos_ativos()
df_ativos = filtrar_df(df_ativos, selected_elemento, selected_espec, selected_insumo)

if df_ativos.empty:
    st.info("Não há itens ativos no momento (ou não correspondem aos filtros).")
else:
    if usuario_perfil == "admin":
        # admin pode editar tudo
        col_config_ativos = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=False),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=False),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=False),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=False
            ),
            "situacao": st.column_config.SelectboxColumn(
                "Situação", options=["em análise", "ativo", "desativado"], width="small"
            ),
            "origem": st.column_config.TextColumn("Origem", disabled=False),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=False),
        }
    elif usuario_perfil == "cocam":
        # cocam pode editar APENAS situacao
        col_config_ativos = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=True),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=True),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=True),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=True
            ),
            "situacao": st.column_config.SelectboxColumn(
                "Situação", options=["em análise", "ativo", "desativado"], width="small"
            ),
            "origem": st.column_config.TextColumn("Origem", disabled=True),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
        }
    else:
        # perfil comum: não pode editar nada
        col_config_ativos = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=True),
            "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=True),
            "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=True),
            "preco_referencia": st.column_config.NumberColumn(
                "Preço de Referência", format="localized", disabled=True
            ),
            "situacao": st.column_config.TextColumn("Situação", disabled=True),
            "origem": st.column_config.TextColumn("Origem", disabled=True),
            "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
        }

    df_ativos = df_ativos[[
        "id", "elemento_despesa", "especificacao_padrao",
        "descricao_insumo", "preco_referencia", "situacao",
        "origem", "registrado_por"
    ]]

    edited_df_ativos = st.data_editor(
        df_ativos,
        column_config=col_config_ativos,
        use_container_width=True,
        hide_index=True,
        key="editor_ativos"
    )

    # só cocam ou admin podem alterar
    if usuario_perfil in ["cocam", "admin"]:
        if st.button("Salvar Alterações em Itens Ativos"):
            for index, row in edited_df_ativos.iterrows():
                update_insumo(
                    insumo_id=row["id"],
                    elemento=row["elemento_despesa"],
                    espec_padrao=row["especificacao_padrao"],
                    nome_insumo=row["descricao_insumo"],
                    espec_tecnica="",
                    preco=row["preco_referencia"],
                    situacao=row["situacao"]
                )
            st.success("Itens ativos atualizados com sucesso!")
            st.rerun()

st.markdown("---")

# =============================================================================
# 5) Expander com Itens Desativados - Aplica Filtro
# =============================================================================
with st.expander("Itens Desativados"):
    df_desativados = get_insumos_desativados()
    df_desativados = filtrar_df(df_desativados, selected_elemento, selected_espec, selected_insumo)

    if df_desativados.empty:
        st.info("Não há itens desativados no momento (ou não correspondem aos filtros).")
    else:
        # Se cocam ou admin, pode excluir itens e alterar situacao
        if usuario_perfil in ["cocam", "admin"]:
            df_desativados["excluir"] = False

        # Montamos colunas exibidas
        cols_to_show = [
            "id", "elemento_despesa", "especificacao_padrao", "descricao_insumo",
            "preco_referencia", "situacao", "origem", "registrado_por"
        ]
        if "excluir" in df_desativados.columns:
            cols_to_show.append("excluir")

        df_desativados = df_desativados[cols_to_show]

        # Config da tabela de desativados
        if usuario_perfil == "admin":
            # admin pode editar tudo e excluir
            col_config_des = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=False),
                "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=False),
                "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=False),
                "preco_referencia": st.column_config.NumberColumn(
                    "Preço de Referência", format="localized", disabled=False
                ),
                "situacao": st.column_config.SelectboxColumn(
                    "Situação", options=["em análise", "ativo", "desativado"], width="small"
                ),
                "origem": st.column_config.TextColumn("Origem", disabled=False),
                "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=False),
                "excluir": st.column_config.CheckboxColumn(
                    "Excluir?", help="Marque para excluir este registro.", disabled=False
                ),
            }
        elif usuario_perfil == "cocam":
            # cocam só edita situacao e excluir
            col_config_des = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=True),
                "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=True),
                "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=True),
                "preco_referencia": st.column_config.NumberColumn(
                    "Preço de Referência", format="localized", disabled=True
                ),
                "situacao": st.column_config.SelectboxColumn(
                    "Situação", options=["em análise", "ativo", "desativado"], width="small"
                ),
                "origem": st.column_config.TextColumn("Origem", disabled=True),
                "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
                "excluir": st.column_config.CheckboxColumn(
                    "Excluir?", help="Marque para excluir este registro.", disabled=False
                ),
            }
        else:
            # perfil comum: não edita nada
            col_config_des = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "elemento_despesa": st.column_config.TextColumn("Elemento de Despesa", disabled=True),
                "especificacao_padrao": st.column_config.TextColumn("Especificação Padrão", disabled=True),
                "descricao_insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=True),
                "preco_referencia": st.column_config.NumberColumn(
                    "Preço de Referência", format="localized", disabled=True
                ),
                "situacao": st.column_config.TextColumn("Situação", disabled=True),
                "origem": st.column_config.TextColumn("Origem", disabled=True),
                "registrado_por": st.column_config.TextColumn("Registrado Por", disabled=True),
            }

        edited_df_des = st.data_editor(
            df_desativados,
            column_config=col_config_des,
            use_container_width=True,
            hide_index=True,
            key="editor_desativados"
        )

        # Apenas cocam ou admin podem salvar (e excluir)
        if usuario_perfil in ["cocam", "admin"]:
            if st.button("Salvar Alterações nos Itens Desativados"):
                for index, row in edited_df_des.iterrows():
                    # Se "excluir" estiver marcado, removemos do banco
                    if "excluir" in row and row["excluir"]:
                        cursor.execute("DELETE FROM td_insumos WHERE id = ?", (row["id"],))
                        conn.commit()
                    else:
                        update_insumo(
                            insumo_id=row["id"],
                            elemento=row["elemento_despesa"],
                            espec_padrao=row["especificacao_padrao"],
                            nome_insumo=row["descricao_insumo"],
                            espec_tecnica="",
                            preco=row["preco_referencia"],
                            situacao=row["situacao"]
                        )
                st.success("Itens desativados atualizados com sucesso!")
                st.rerun()
