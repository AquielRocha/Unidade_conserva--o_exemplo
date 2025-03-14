import streamlit as st
import pandas as pd
import sqlite3
import os

# Ajuste o caminho do banco conforme a sua necessidade
DB_PATH = "database/app_data.db"

# Verifica se o usuário está logado
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

# Verifica se o perfil do usuário é admin (se for necessário restringir)
if st.session_state["perfil"] != "admin":
    st.warning("🔒 Acesso negado! Você não tem permissão para acessar esta seção.")
    st.stop()

st.set_page_config(
    page_title="Consultar Tetos",
    page_icon="♾️",
    layout="wide"
)

st.title("Consulta de Tetos e Distribuição")

@st.cache_data
def load_tetos_from_db() -> pd.DataFrame:
    """Carrega dados da tabela tf_distribuicao_elegiveis."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()  # Se não existe o arquivo de DB
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
    conn.close()
    return df

# 1) Carregar dados
df_tetos = load_tetos_from_db()

if df_tetos.empty:
    st.warning("Nenhum dado encontrado na tabela 'tf_distribuicao_elegiveis'. Verifique se o banco foi inicializado.")
    st.stop()

# 2) Sidebar com Filtros
st.sidebar.header("Filtros")

# Filtro por id_iniciativa (se existir essa coluna)
lista_iniciativas = sorted(df_tetos["id_iniciativa"].dropna().unique())
filtro_iniciativa = st.sidebar.selectbox("Selecione a Iniciativa (id_iniciativa)", 
    options=["Todos"] + list(map(str, lista_iniciativas)), 
    index=0)

if filtro_iniciativa != "Todos":
    # Toma cuidado se "id_iniciativa" for numérico ou string
    # Se for numérico, converta de volta:
    try:
        val = int(filtro_iniciativa)
        df_tetos = df_tetos[df_tetos["id_iniciativa"] == val]
    except:
        # Ou se for string
        df_tetos = df_tetos[df_tetos["id_iniciativa"].astype(str) == filtro_iniciativa]

# Filtro por Unidade de Conservação
lista_ucs = sorted(df_tetos["Unidade de Conservação"].dropna().unique())
filtro_uc = st.sidebar.selectbox("Unidade de Conservação", ["Todas"] + lista_ucs, index=0)
if filtro_uc != "Todas":
    df_tetos = df_tetos[df_tetos["Unidade de Conservação"] == filtro_uc]

# Se após filtros ficou vazio, avisamos
if df_tetos.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

# 3) Exibir Estatísticas Simples (opcional)
st.subheader("Estatísticas Gerais")
col1, col2 = st.columns(2)

# Exemplo: quantas UCs e quantas iniciativas existem após os filtros
col1.metric(
    label="Total de Registros",
    value=len(df_tetos)
)
num_ucs = df_tetos["Unidade de Conservação"].nunique()
col2.metric(
    label="Total de UCs",
    value=num_ucs
)

# 4) Exibir Tabela com colunas principais
# Se quiser renomear colunas para exibição
rename_map = {
    "Unidade de Conservação": "Unidade de Conservação",
    "TetoSaldo disponível":   "Teto Saldo Disponível",
    "TetoPrevisto 2025":      "Teto Previsto 2025",
    "TetoPrevisto 2026":      "Teto Previsto 2026",
    "TetoPrevisto 2027":      "Teto Previsto 2027",
    "TetoTotalDisponivel":    "Teto Total Disponível",
    "A Distribuir":           "Saldo a Distribuir",
    "CNUC":                   "CNUC",  # se existir
}

df_viz = df_tetos.copy()

# Ajustamos o "No" manualmente, se quiser um índice visual
df_viz.reset_index(drop=True, inplace=True)
df_viz.insert(0, "No", range(1, len(df_viz)+1))

df_viz.rename(columns=rename_map, inplace=True)

# 4.1) Selecionar colunas que desejamos exibir
colunas_para_exibir = [
    "No", 
    "Unidade de Conservação", 
    "Teto Total Disponível",
    "Saldo a Distribuir",
    "Teto Saldo Disponível", 
    "Teto Previsto 2025", 
    "Teto Previsto 2026", 
    "Teto Previsto 2027"
]
colunas_existentes = [c for c in colunas_para_exibir if c in df_viz.columns]
df_viz = df_viz[colunas_existentes]

# 5) Formatar colunas monetárias
def fmt_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}"
    except:
        return "R$ 0,00"

for col in df_viz.columns:
    if col not in ["No", "Unidade de Conservação", "CNUC"]:
        df_viz[col] = df_viz[col].apply(fmt_moeda)

st.subheader("Tabela de Tetos")
st.dataframe(df_viz, use_container_width=True)

# 6) Caso deseje uma “exportação” ou algo adicional, pode colocar
csv_data = df_tetos.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Baixar CSV",
    data=csv_data,
    file_name="consulta_tetos.csv",
    mime="text/csv"
)

st.info("Página de consulta de tetos concluída.")
