import streamlit as st
import pandas as pd
import sqlite3
import os
import numpy as np

DB_PATH = "database/app_data.db"  # Ajuste o caminho do seu DB

# 1) Verificação de Login
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

# 2) Verificação de Perfil (ex: admin)
if st.session_state["perfil"] != "admin":
    st.warning("🔒 Acesso negado! Você não tem permissão para acessar esta seção.")
    st.stop()

# 3) Configuração de Página
st.set_page_config(
    page_title="Consulta Elaborada de Tetos",
    page_icon="♾️",
    layout="wide"
)

st.title("Consulta Elaborada de Tetos e Distribuição")

# 4) Função para carregar dados
@st.cache_data
def load_tetos_from_db() -> pd.DataFrame:
    """Carrega dados da tabela tf_distribuicao_elegiveis do banco."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
    conn.close()
    return df

# 5) Carregar DataFrame
df_tetos = load_tetos_from_db()
if df_tetos.empty:
    st.warning("Nenhum dado encontrado na tabela 'tf_distribuicao_elegiveis'.")
    st.stop()

# (Opcional) Renomear algumas colunas para ficar mais legível
rename_map = {
    "Unidade de Conservação": "UnidadeConservacao",  # Evita espaço no nome
    "TetoSaldo disponível":   "TetoSaldoDisponivel",
    "TetoPrevisto 2025":      "TetoPrevisto2025",
    "TetoPrevisto 2026":      "TetoPrevisto2026",
    "TetoPrevisto 2027":      "TetoPrevisto2027",
    "TetoTotalDisponivel":    "TetoTotalDisponivel",
    "A Distribuir":           "SaldoADistribuir",
    # etc., se houver mais colunas
}
df_tetos.rename(columns=rename_map, inplace=True)

# 6) Barra Lateral (SideBar) - Filtros
st.sidebar.header("Filtros")

# a) Filtro Iniciativa
lista_iniciativas = sorted(df_tetos["Nome da Proposta/Iniciativa Estruturante"].dropna().unique())
filtro_iniciativa = st.sidebar.selectbox(
    "Selecione a Iniciativa",
    options=["Todos"] + lista_iniciativas
)
if filtro_iniciativa != "Todos":
    df_tetos = df_tetos[df_tetos["Nome da Proposta/Iniciativa Estruturante"] == filtro_iniciativa]

# b) Filtro UC
if "UnidadeConservacao" in df_tetos.columns:
    lista_uc = sorted(df_tetos["UnidadeConservacao"].dropna().unique())
    filtro_uc = st.sidebar.selectbox("Unidade de Conservação", ["Todas"] + list(lista_uc))
    if filtro_uc != "Todas":
        df_tetos = df_tetos[df_tetos["UnidadeConservacao"] == filtro_uc]

# filtro por demandante
if "DEMANDANTE (diretoria)" in df_tetos.columns:
    lista_demandantes = sorted(df_tetos["DEMANDANTE (diretoria)"].dropna().unique())
    filtro_demandante = st.sidebar.selectbox("Demandante", ["Todos"] + list(lista_demandantes))
    if filtro_demandante != "Todos":
        df_tetos = df_tetos[df_tetos["DEMANDANTE (diretoria)"] == filtro_demandante]


# c) (Opcional) Filtrar só tetos > 0
filtro_somente_positivos = st.sidebar.checkbox("Mostrar somente TetoTotalDisponivel > 0?", value=False)
if filtro_somente_positivos and "TetoTotalDisponivel" in df_tetos.columns:
    df_tetos = df_tetos[df_tetos["TetoTotalDisponivel"] > 0]

# d) Caso deseje filtrar por TetoPrevisto2025, etc., pode adicionar mais.

if df_tetos.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

# 7) Estatísticas/Métricas Globais
st.subheader("Estatísticas Globais")

col1, col2, col3, col4, col5 = st.columns(5)

total_registros = len(df_tetos)
col1.metric("Total de Registros", total_registros)

# Quantidade de UCs
if "UnidadeConservacao" in df_tetos.columns:
    total_ucs = df_tetos["UnidadeConservacao"].nunique()
    col2.metric("Total de UCs", total_ucs)

# Soma do TetoTotalDisponivel
if "TetoTotalDisponivel" in df_tetos.columns:
    soma_teto = df_tetos["TetoTotalDisponivel"].fillna(0).sum()
    col3.metric("Soma Teto Total", f"R$ {soma_teto:,.2f}")

# Soma do Saldo a Distribuir
if "SaldoADistribuir" in df_tetos.columns:
    soma_saldo = df_tetos["SaldoADistribuir"].fillna(0).sum()
    col4.metric("Soma do Saldo a Distribuir", f"R$ {soma_saldo:,.2f}")

# Uma métrica extra, como TetoSaldoDisponivel
if "TetoSaldoDisponivel" in df_tetos.columns:
    soma_saldoDisp = df_tetos["TetoSaldoDisponivel"].fillna(0).sum()
    col5.metric("Teto Saldo Disponível (Soma)", f"R$ {soma_saldoDisp:,.2f}")

st.divider()

# 8) Expanders com Análises Agrupadas
st.subheader("Análises Agrupadas")

def fmt_money(valor):
    """Função de formatação monetária."""
    try:
        return f"R$ {float(valor):,.2f}"
    except:
        return "R$ 0,00"

def agrupar_e_exibir(coluna_grupo):
    """Agrupa a df_tetos pela coluna_grupo e mostra soma das colunas monetárias."""
    if coluna_grupo not in df_tetos.columns:
        st.warning(f"Coluna {coluna_grupo} não existe no DataFrame.")
        return

    # Definimos colunas monetárias que queremos somar
    col_monetarias = []
    for c in ["TetoSaldoDisponivel", "TetoPrevisto2025", "TetoPrevisto2026", 
              "TetoPrevisto2027", "TetoTotalDisponivel", "SaldoADistribuir"]:
        if c in df_tetos.columns:
            col_monetarias.append(c)

    ag_dict = {}
    for c in col_monetarias:
        ag_dict[c] = "sum"

    df_ag = df_tetos.groupby(coluna_grupo).agg(ag_dict).reset_index()
    # Adiciona linha "Total Geral"
    linha_total = {}
    for c in df_ag.columns:
        if c == coluna_grupo:
            linha_total[c] = "Total Geral"
        else:
            linha_total[c] = df_ag[c].sum()
    df_ag.loc[len(df_ag)] = linha_total

    # Formata
    for c in col_monetarias:
        df_ag[c] = df_ag[c].apply(fmt_money)

    st.dataframe(df_ag, use_container_width=True)

# Exemplo de alguns expanders
with st.expander("Agrupado por Iniciativa (id_iniciativa)", expanded=False):
    if "id_iniciativa" in df_tetos.columns:
        agrupar_e_exibir("id_iniciativa")
    else:
        st.info("Coluna 'id_iniciativa' não disponível.")

with st.expander("Agrupado por UC (UnidadeConservacao)", expanded=False):
    if "UnidadeConservacao" in df_tetos.columns:
        agrupar_e_exibir("UnidadeConservacao")
    else:
        st.info("Coluna 'UnidadeConservacao' não disponível.")

with st.expander("Agrupado por CNUC", expanded=False):
    if "CNUC" in df_tetos.columns:
        agrupar_e_exibir("CNUC")
    else:
        st.info("Coluna 'CNUC' não disponível.")

# etc... você pode adicionar mais expanders conforme suas colunas de interesse

st.divider()

# 9) Exibição Detalhada da Tabela (pós-filtros)
st.subheader("Tabela Detalhada (pós-filtros)")

# Remonta colunas na ordem que desejar
col_order = ["id", "id_iniciativa", "UnidadeConservacao", 
             "TetoSaldoDisponivel", "TetoPrevisto2025", 
             "TetoPrevisto2026", "TetoPrevisto2027",
             "TetoTotalDisponivel", "SaldoADistribuir", "CNUC"]

col_order = [c for c in col_order if c in df_tetos.columns]
df_show = df_tetos[col_order].copy().reset_index(drop=True)

# Insere coluna "No" manual
df_show.insert(0, "No", range(1, len(df_show)+1))

# Formata monetariamente
for c_moeda in ["TetoSaldoDisponivel", "TetoPrevisto2025", "TetoPrevisto2026",
                "TetoPrevisto2027", "TetoTotalDisponivel", "SaldoADistribuir"]:
    if c_moeda in df_show.columns:
        df_show[c_moeda] = df_show[c_moeda].apply(fmt_money)

st.dataframe(df_show, use_container_width=True)

# 10) Botão de Download
csv_data = df_show.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Baixar CSV",
    data=csv_data,
    file_name="consulta_tetos.csv",
    mime="text/csv"
)

st.success("Consulta de Tetos concluída!")
