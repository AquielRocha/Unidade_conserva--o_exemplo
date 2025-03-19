import streamlit as st
import pandas as pd
import sqlite3
import os
import numpy as np
import plotly.express as px
import plotly 
import json

from init_db import init_database
from init_db import init_samge_database

DB_PATH = "database/app_data.db"  # Ajuste o caminho do seu DB

####################################
# 1) Verificação de Login e Perfil #
####################################
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

if st.session_state["perfil"] != "admin":
    st.warning("🔒 Acesso negado! Você não tem permissão para acessar esta seção.")
    st.stop()

#######################################
# 2) Configurações Gerais da Página   #
#######################################
st.set_page_config(
    page_title="Consulta Tetos FCA",
    page_icon="♾️",
    layout="wide"
)

st.subheader("Consulta Tetos FCA")

####################################
# 3) Função para carregar dados    #
####################################
@st.cache_data
def load_tetos_from_db() -> pd.DataFrame:
    """Carrega dados da tabela tf_distribuicao_elegiveis do banco."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
    conn.close()
    return df

####################################
# 4) Verifica se o BD existe       #
####################################
if not os.path.exists(DB_PATH):
    st.warning("Banco de dados não encontrado. Verifique se executou o init_db.py.")
    st.stop()

df_tetos = load_tetos_from_db()
if df_tetos.empty:
    st.warning("Nenhum dado encontrado na tabela 'tf_distribuicao_elegiveis'.")
    st.stop()

####################################
# 5) Renomear colunas (opcional)   #
####################################
rename_map = {
    "Unidade de Conservação": "UnidadeConservacao",
    "TetoSaldo disponível":   "TetoSaldoDisponivel",
    "TetoPrevisto 2025":      "TetoPrevisto2025",
    "TetoPrevisto 2026":      "TetoPrevisto2026",
    "TetoPrevisto 2027":      "TetoPrevisto2027",
    "TetoTotalDisponivel":    "TetoTotalDisponivel",
    "A Distribuir":           "SaldoADistribuir",
    # Adicione mais se precisar
}
df_tetos.rename(columns=rename_map, inplace=True)

##########################################
# 6) Layout de Filtros na Barra Lateral  #
##########################################
# - Criamos duas colunas na sidebar:
#   col1 = "Filtros"
#   col2 = botão "Limpar Filtros"
##########################################

col_filtro, col_btn = st.sidebar.columns([3, 1])
col_filtro.header("Filtros")

# Botão de limpar filtros
with col_btn:
    st.markdown(
        """
        <style>
        div.stButton > button {
            width: 100%;
            padding: 5px 10px;
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    if st.button("🧹", help="Limpar Filtros"):
        # Aqui você pode resetar os states dos filtros
        st.session_state["filtro_iniciativa"] = "Todos"
        st.session_state["filtro_uc"] = "Todas"
        st.session_state["filtro_demandante"] = "Todos"
        st.session_state["filtro_somente_positivos"] = False
        st.rerun()

# Filtro Iniciativa
lista_iniciativas = sorted(df_tetos["Nome da Proposta/Iniciativa Estruturante"].dropna().unique())
filtro_iniciativa = st.sidebar.selectbox(
    "Selecione a Iniciativa",
    options=["Todos"] + lista_iniciativas,
    key="filtro_iniciativa"
)
if filtro_iniciativa != "Todos":
    df_tetos = df_tetos[df_tetos["Nome da Proposta/Iniciativa Estruturante"] == filtro_iniciativa]

# Filtro UC
if "UnidadeConservacao" in df_tetos.columns:
    lista_uc = sorted(df_tetos["UnidadeConservacao"].dropna().unique())
    filtro_uc = st.sidebar.selectbox("Unidade de Conservação", ["Todas"] + list(lista_uc), key="filtro_uc")
    if filtro_uc != "Todas":
        df_tetos = df_tetos[df_tetos["UnidadeConservacao"] == filtro_uc]

# Filtro Demandante
if "DEMANDANTE (diretoria)" in df_tetos.columns:
    lista_demandantes = sorted(df_tetos["DEMANDANTE (diretoria)"].dropna().unique())
    filtro_demandante = st.sidebar.selectbox("Diretoria", ["Todos"] + list(lista_demandantes), key="filtro_demandante")
    if filtro_demandante != "Todos":
        df_tetos = df_tetos[df_tetos["DEMANDANTE (diretoria)"] == filtro_demandante]

# Filtrar por GR (Gerência Regional) (utilizar tabela td_unidades)
# a tabela td_unidades tem uma coluna cnuc que relaciona com a coluna CNUC do df_tetos
# e uma coluna gr que indica a Gerência Regional da unidade
if "CNUC" in df_tetos.columns:
    conn = sqlite3.connect(DB_PATH)
    df_unidades = pd.read_sql_query("SELECT cnuc, gr FROM td_unidades", conn)
    conn.close()
    if not df_unidades.empty:
        # Obtemos a lista de CNUCs disponíveis no df_tetos
        lista_cnuc = sorted(df_tetos["CNUC"].dropna().unique())
        # Filtramos o df_unidades para obter somente os CNUCs presentes no df_tetos
        df_unidades = df_unidades[df_unidades["cnuc"].isin(lista_cnuc)]
        
        if not df_unidades.empty:
            # Obtemos a lista de GRs disponíveis
            lista_gr = sorted(df_unidades["gr"].dropna().unique())
            filtro_gr = st.sidebar.selectbox("Gerência Regional", ["Todas"] + list(lista_gr), key="filtro_gr")
            if filtro_gr != "Todas":
                cnucs_filtrados = df_unidades[df_unidades["gr"] == filtro_gr]["cnuc"].unique()
                df_tetos = df_tetos[df_tetos["CNUC"].isin(cnucs_filtrados)]
# Se o filtro de GR não retornar nenhum CNUNC, mantemos o df_tetos original
# Caso contrário, o df_tetos será filtrado para incluir somente os CNUNCs correspondentes à GR selecionada




# Se o DF ficar vazio após filtros, interrompe
if df_tetos.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

################################################
# 7) Expander de Configurações (opcional/admin)#
################################################
# Se quiser manter a mesma lógica do outro script:
if st.session_state["usuario_logado"] and st.session_state["perfil"] == "admin":
    with st.sidebar.expander("⚙️ Configurações", expanded=False):
        # Filtro somente positivos
        st.warning("Mostrar somente Teto Total Disponivel > 0")
        filtro_somente_positivos = st.toggle("", value=False, key="filtro_somente_positivos")
        if filtro_somente_positivos and "TetoTotalDisponivel" in df_tetos.columns:
            df_tetos = df_tetos[df_tetos["TetoTotalDisponivel"] > 0]

        # if st.button("🔄 Recriar Banco de Dados"):
        #     if os.path.exists(DB_PATH):
        #         os.remove(DB_PATH)
        #     try:
        #         init_database()
        #         init_samge_database()
        #         st.success("Banco de dados recriado com sucesso!")
        #         st.rerun()
        #     except Exception as e:
        #         st.error(f"Erro ao recriar o banco: {e}")

        # if st.button("🗑 Limpar Cache"):
        #     st.cache_data.clear()
        #     st.success("Cache limpo com sucesso!")
        #     st.rerun()

###################################
# 8) Exibição de Estatísticas     #
###################################
st.divider()
st.subheader("Estatísticas Gerais")

# Podemos exibir algumas métricas em colunas
col1, col2, col3, col4 = st.columns(4)

# Total de Registros e Total de UCs
total_registros = len(df_tetos)
col1.metric("Total de Registros", total_registros)

if "UnidadeConservacao" in df_tetos.columns:
    total_ucs = df_tetos["UnidadeConservacao"].nunique()
    col1.metric("Total de UCs", total_ucs)

# Total de Iniciativas
if "Nome da Proposta/Iniciativa Estruturante" in df_tetos.columns:
    total_iniciativas = df_tetos["Nome da Proposta/Iniciativa Estruturante"].nunique()
    col1.metric("Total de Iniciativas", total_iniciativas)

# Soma do TetoTotalDisponivel
if "TetoTotalDisponivel" in df_tetos.columns:
    soma_teto = df_tetos["TetoTotalDisponivel"].fillna(0).sum()
    col2.metric("Soma Teto Total", f"R$ {soma_teto:,.2f}")

# Soma do Teto Saldo Disponível
if "TetoSaldoDisponivel" in df_tetos.columns:
    soma_saldoDisp = df_tetos["TetoSaldoDisponivel"].fillna(0).sum()
    col3.metric("Teto Saldo Disponível (Soma)", f"R$ {soma_saldoDisp:,.2f}")

# Soma do Teto Previsto 2025
if "TetoPrevisto2025" in df_tetos.columns:
    soma_previsto2025 = df_tetos["TetoPrevisto2025"].fillna(0).sum()
    col3.metric("Teto Previsto 2025 (Soma)", f"R$ {soma_previsto2025:,.2f}")

# Soma do Teto Previsto 2026
if "TetoPrevisto2026" in df_tetos.columns:
    soma_previsto2026 = df_tetos["TetoPrevisto2026"].fillna(0).sum()
    col3.metric("Teto Previsto 2026 (Soma)", f"R$ {soma_previsto2026:,.2f}")

# Soma do Teto Previsto 2027
if "TetoPrevisto2027" in df_tetos.columns:
    soma_previsto2027 = df_tetos["TetoPrevisto2027"].fillna(0).sum()
    col3.metric("Teto Previsto 2027 (Soma)", f"R$ {soma_previsto2027:,.2f}")

# Soma do Saldo a Distribuir
if "SaldoADistribuir" in df_tetos.columns:
    soma_saldo = df_tetos["SaldoADistribuir"].fillna(0).sum()
    col2.metric("Soma do Saldo a Distribuir por Eixo Temático", f"R$ {soma_saldo:,.2f}")

# metrica calculando a porcentagem a distribuir em relação ao teto total
if "TetoTotalDisponivel" in df_tetos.columns and "SaldoADistribuir" in df_tetos.columns:
    df_tetos["percentual_distribuicao"] = (df_tetos["SaldoADistribuir"].fillna(0) / df_tetos["TetoTotalDisponivel"].fillna(1)) * 100
    percentual_distribuicao = df_tetos["percentual_distribuicao"].mean()
    col2.metric("Percentual a Distribuir (%)", f"{percentual_distribuicao:.2f} %")

# metrica calculando a porcentagem de tetos previstos em relação ao teto total - saldo disponível
if "TetoSaldoDisponivel" in df_tetos.columns and "TetoTotalDisponivel" in df_tetos.columns:
    df_tetos["percentual_saldo_disponivel"] = (df_tetos["TetoSaldoDisponivel"].fillna(0) / df_tetos["TetoTotalDisponivel"].fillna(1)) * 100
    percentual_saldo_disponivel = df_tetos["percentual_saldo_disponivel"].mean()
    col4.metric("Percentual Saldo Disponível (%)", f"{percentual_saldo_disponivel:.2f} %")

# metrica calculando a porcentagem de tetos previstos em relação ao teto total
if "TetoTotalDisponivel" in df_tetos.columns and "TetoPrevisto2025" in df_tetos.columns:
    df_tetos["percentual_previsto"] = (df_tetos["TetoPrevisto2025"].fillna(0) / df_tetos["TetoTotalDisponivel"].fillna(1)) * 100
    percentual_previsto = df_tetos["percentual_previsto"].mean()
    col4.metric("Percentual Previsto 2025 (%)", f"{percentual_previsto:.2f} %")
# metrica calculando a porcentagem de tetos previstos em relação ao teto total
if "TetoTotalDisponivel" in df_tetos.columns and "TetoPrevisto2026" in df_tetos.columns:
    df_tetos["percentual_previsto"] = (df_tetos["TetoPrevisto2026"].fillna(0) / df_tetos["TetoTotalDisponivel"].fillna(1)) * 100
    percentual_previsto = df_tetos["percentual_previsto"].mean()
    col4.metric("Percentual Previsto 2026 (%)", f"{percentual_previsto:.2f} %")
# metrica calculando a porcentagem de tetos previstos em relação ao teto total
if "TetoTotalDisponivel" in df_tetos.columns and "TetoPrevisto2027" in df_tetos.columns:
    df_tetos["percentual_previsto"] = (df_tetos["TetoPrevisto2027"].fillna(0) / df_tetos["TetoTotalDisponivel"].fillna(1)) * 100
    percentual_previsto = df_tetos["percentual_previsto"].mean()
    col4.metric("Percentual Previsto 2027 (%)", f"{percentual_previsto:.2f} %")


# Custom CSS for metrics
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 16px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# spinner para indicar carregamento de gráficos
with st.spinner("Carregando gráficos..."):

    # implementa um expander para mostrar gráficos dos tetos de saldo disponível e por ano, de cada iniciativa
    with st.expander("📊 Gráficos de Tetos por Iniciativa", expanded=False):
        if "id_iniciativa" in df_tetos.columns and "Nome da Proposta/Iniciativa Estruturante" in df_tetos.columns:
            iniciativas_unicas = df_tetos[["id_iniciativa", "Nome da Proposta/Iniciativa Estruturante"]].drop_duplicates()

            for _, row in iniciativas_unicas.iterrows():
                iniciativa_id = row["id_iniciativa"]
                iniciativa_nome = row["Nome da Proposta/Iniciativa Estruturante"]

                st.divider()

                st.markdown(f"### **{iniciativa_nome.title()}**")
                df_iniciativa = df_tetos[df_tetos["id_iniciativa"] == iniciativa_id]

                # Gráfico de Teto Saldo Disponível
                if "TetoSaldoDisponivel" in df_iniciativa.columns:
                    df_teto_saldo = df_iniciativa[df_iniciativa["TetoSaldoDisponivel"] > 0]
                    if not df_teto_saldo.empty:
                        fig1 = px.bar(df_teto_saldo.sort_values("TetoSaldoDisponivel"), 
                                    y="UnidadeConservacao", 
                                    x="TetoSaldoDisponivel",
                                    title="Teto Saldo Disponível por UC",
                                    labels={"TetoSaldoDisponivel": "Valor (R$)", "UnidadeConservacao": "Unidade de Conservação"})
                        st.plotly_chart(fig1, use_container_width=True)

                # Gráfico horizontal de Tetos Previsto por Ano
                anos_previstos = ["TetoPrevisto2025", "TetoPrevisto2026", "TetoPrevisto2027"]
                for ano in anos_previstos:
                    if ano in df_iniciativa.columns:
                        df_teto_ano = df_iniciativa[df_iniciativa[ano] > 0]
                        if not df_teto_ano.empty:
                            fig_ano = px.bar(df_teto_ano.sort_values(ano), 
                                            y="UnidadeConservacao", 
                                            x=ano,
                                            title=f"Teto Previsto {ano[-4:]} por UC",
                                            labels={ano: "Valor (R$)", "UnidadeConservacao": "Unidade de Conservação"})
                            st.plotly_chart(fig_ano, use_container_width=True)

                # Melt the DataFrame to long format for plotting
                df_melt = df_iniciativa.melt(
                    id_vars=["UnidadeConservacao"],
                    value_vars=["TetoSaldoDisponivel", "TetoPrevisto2025", "TetoPrevisto2026", "TetoPrevisto2027"],
                    var_name="Categoria",
                    value_name="Valor"
                )

                # Gráfico combinado de barras horizontais agrupadas
                # 1) Ordene por soma total (decida se ascending=True ou False)
                df_melt["TotalTeto"] = df_melt.groupby("UnidadeConservacao")["Valor"].transform("sum") # soma total por UC
                df_melt = df_melt.sort_values("TotalTeto", ascending=True)

                # 2) Transforme a coluna em Categorical para fixar a ordem no DataFrame
                ordered_ucs = df_melt["UnidadeConservacao"].unique().tolist() # lista de UCs na ordem correta
                df_melt["UnidadeConservacao"] = pd.Categorical(
                    df_melt["UnidadeConservacao"], 
                    categories=ordered_ucs, 
                    ordered=True
                )

                # 3) Defina a ordem das categorias de tetos (você já fazia isso)
                categoria_order = ["TetoSaldoDisponivel", "TetoPrevisto2025", "TetoPrevisto2026", "TetoPrevisto2027"]
                df_melt["Categoria"] = pd.Categorical(df_melt["Categoria"], categories=categoria_order, ordered=True)

                # 4) Finalmente, crie o gráfico indicando “category_orders”:
                fig_combo = px.bar(
                    df_melt, 
                    y="UnidadeConservacao", 
                    x="Valor", 
                    color="Categoria",
                    title="Comparativo de Tetos por UC",
                    labels={"Valor": "Valor (R$)", "UnidadeConservacao": "Unidade de Conservação"},
                    category_orders={
                        "UnidadeConservacao": ordered_ucs,    # y-axis
                        "Categoria": categoria_order         # legend
                    },
                    height=800
                )

                # 5) Se quiser o maior valor no TOPO, basta reverter o eixo y:
                fig_combo.update_layout(
                    yaxis=dict(autorange="reversed")
                )

                st.plotly_chart(fig_combo, use_container_width=True)



#############################################
# 9) Expanders com Análises Agrupadas       #
#############################################
st.divider()

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


# Expander por Iniciativa (tabela única)
with st.expander("Agrupado por Iniciativa (Resumo)", expanded=False):
    if "Nome da Proposta/Iniciativa Estruturante" in df_tetos.columns:
        colunas_iniciativa = [
            "Nome da Proposta/Iniciativa Estruturante",
            "TetoTotalDisponivel",
            "TetoSaldoDisponivel",
            "TetoPrevisto2025",
            "TetoPrevisto2026",
            "TetoPrevisto2027",
            "SaldoADistribuir"
        ]
        df_iniciativas = df_tetos.groupby("Nome da Proposta/Iniciativa Estruturante", as_index=False)[colunas_iniciativa].sum(numeric_only=True)
        for c_moeda in colunas_iniciativa[1:]:
            df_iniciativas[c_moeda] = df_iniciativas[c_moeda].apply(fmt_money)
        st.dataframe(df_iniciativas, use_container_width=True)

    # mostra totalizações
    colunas_total = [
        "TetoTotalDisponivel",
        "TetoSaldoDisponivel",
        "TetoPrevisto2025",
        "TetoPrevisto2026",
        "TetoPrevisto2027",
        "SaldoADistribuir"
    ]
    df_total = df_tetos[colunas_total].sum(numeric_only=True).to_frame().T
    for c_moeda in colunas_total:
        df_total[c_moeda] = df_total[c_moeda].apply(fmt_money)
    df_total.insert(0, "Nome da Proposta/Iniciativa Estruturante", "Total Geral")
    st.write("Total Geral:")
    st.dataframe(df_total[colunas_iniciativa], use_container_width=True)


with st.expander("Agrupado por Iniciativa (Detalhado)", expanded=False):
    if (
        "id_iniciativa" in df_tetos.columns 
        and "UnidadeConservacao" in df_tetos.columns 
        and "Nome da Proposta/Iniciativa Estruturante" in df_tetos.columns
    ):
        iniciativas_unicas = df_tetos[["id_iniciativa", "Nome da Proposta/Iniciativa Estruturante"]].drop_duplicates()

        for _, row in iniciativas_unicas.iterrows():
            iniciativa_id = row["id_iniciativa"]
            iniciativa_nome = row["Nome da Proposta/Iniciativa Estruturante"]

            st.subheader(f"Iniciativa: {iniciativa_nome}")
            df_iniciativa = df_tetos[df_tetos["id_iniciativa"] == iniciativa_id]
            # Mostrar totalizações por iniciativa, com cada iniciativa em uma linha
            colunas_iniciativa = [
                "TetoTotalDisponivel",
                "SaldoADistribuir",
                "TetoSaldoDisponivel",
                "TetoPrevisto2025",
                "TetoPrevisto2026",
                "TetoPrevisto2027",
            ]
            df_total = df_iniciativa.groupby("Nome da Proposta/Iniciativa Estruturante", as_index=False)[colunas_iniciativa].sum(numeric_only=True)
            for c_moeda in colunas_iniciativa:
                df_total[c_moeda] = df_total[c_moeda].apply(fmt_money)
            st.write("Total da Iniciativa:")
            st.dataframe(df_total, use_container_width=True)

            # Agrupar e somar apenas as colunas desejadas por unidade
            colunas_desejadas = [
                "UnidadeConservacao",
                "TetoTotalDisponivel",
                "SaldoADistribuir",
                "TetoSaldoDisponivel",
                "TetoPrevisto2025",
                "TetoPrevisto2026",
                "TetoPrevisto2027",
            ]
            df_agrupado = (
                df_iniciativa.groupby("UnidadeConservacao", as_index=False)[colunas_desejadas[1:]]
                .sum(numeric_only=True)
            )
            df_agrupado.insert(0, "UnidadeConservacao", df_agrupado.pop("UnidadeConservacao"))
            for c_moeda in colunas_desejadas[1:]:
                df_agrupado[c_moeda] = df_agrupado[c_moeda].apply(fmt_money)
            st.write("Distribuição por Unidade:")
            st.dataframe(df_agrupado[colunas_desejadas], use_container_width=True)

with st.expander("Agrupado por UC (Unidade de Conservacao)", expanded=False):
    if "UnidadeConservacao" in df_tetos.columns:
        agrupar_e_exibir("UnidadeConservacao")
    else:
        st.info("Coluna 'UnidadeConservacao' não disponível.")

with st.expander("Agrupado por GR (Gerência Regional)", expanded=False):
    if "CNUC" in df_tetos.columns:
        conn = sqlite3.connect(DB_PATH)
        df_unidades = pd.read_sql_query("SELECT cnuc, gr FROM td_unidades", conn)
        conn.close()
        if not df_unidades.empty:
            df_tetos = df_tetos.merge(df_unidades, left_on="CNUC", right_on="cnuc", how="left")
            agrupar_e_exibir("gr")
        else:
            st.info("Tabela 'td_unidades' está vazia.")
    else:
        st.info("Coluna 'CNUC' não disponível.")


# expander por Demandante (Diretoria)
with st.expander("Agrupado por Demandante (Diretoria)", expanded=False):
    if "DEMANDANTE (diretoria)" in df_tetos.columns:
        agrupar_e_exibir("DEMANDANTE (diretoria)")
    else:
        st.info("Coluna 'DEMANDANTE (diretoria)' não disponível.")



# # expander por Eixo Temático
# with st.expander("Agrupado por Eixo Temático", expanded=False):
#     conn = sqlite3.connect(DB_PATH)
#     query = "SELECT * FROM td_samge_processos"
#     df_samge = pd.read_sql_query(query, conn)
#     conn.close()

#     if df_samge.empty:
#         st.info("Nenhum dado encontrado na tabela 'td_samge_processos'.")
#     else:
#         # Lista das colunas numéricas que usaremos para somar/verificar distribuição
#         colunas_monetarias = [
#             "TetoTotalDisponivel",
#             "SaldoADistribuir",
#             "TetoSaldoDisponivel",
#             "TetoPrevisto2025",
#             "TetoPrevisto2026",
#             "TetoPrevisto2027",
#         ]
        
#         # 1) Fazemos um groupby por EixoTematico e somamos as colunas monetárias
#         df_eixos_sum = (
#             df_samge
#             .groupby("EixoTematico")[colunas_monetarias]
#             .sum(numeric_only=True)  # Garante que some apenas colunas numéricas
#             .reset_index()
#         )
        
#         # 2) Criamos uma coluna "Soma" para saber o total por Eixo
#         df_eixos_sum["Soma"] = df_eixos_sum[colunas_monetarias].sum(axis=1)
        
#         # 3) Filtramos apenas Eixos com soma > 0
#         df_eixos_filtrados = df_eixos_sum[df_eixos_sum["Soma"] > 0]
        
#         if df_eixos_filtrados.empty:
#             st.info("Nenhum Eixo com valores distribuídos encontrado.")
#         else:
#             # 4) Para cada eixo que tem soma > 0, exibimos um "subexpander" ou subheader
#             for eixo in df_eixos_filtrados["EixoTematico"]:
#                 # Se quiser cada Eixo em seu próprio "expander", use:
#                 with st.expander(f"Eixo Temático: {eixo}", expanded=False):
                    
#                     # Filtra as linhas do df_samge correspondentes a esse eixo
#                     df_eixo = df_samge[df_samge["EixoTematico"] == eixo].copy()
                    
#                     # 5) Agrupa por UnidadeConservacao
#                     colunas_agrupadas = ["UnidadeConservacao"] + colunas_monetarias
#                     df_agrupado = (
#                         df_eixo
#                         .groupby("UnidadeConservacao", as_index=False)[colunas_monetarias]
#                         .sum(numeric_only=True)
#                     )
                    
#                     # 6) Formata valores monetários
#                     for c_moeda in colunas_monetarias:
#                         if c_moeda in df_agrupado.columns:
#                             df_agrupado[c_moeda] = df_agrupado[c_moeda].apply(fmt_money)
                    
#                     # 7) Exibe a tabela final
#                     st.dataframe(df_agrupado[colunas_agrupadas], use_container_width=True)





#####################################
# 11) CSS e ajustes de estilo extra #
#####################################
# (Opcional) Caso queira reutilizar o estilo de “tags” etc. 
# do outro script, inclua aqui:
st.markdown("""
    <style>
    .tag {
        display: inline-block;
        background-color: #2c3e50;
        color: white;
        padding: 5px 10px;
        margin: 3px;
        border-radius: 12px;
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)





#####################################
# 10) Exibição Detalhada e Download #
#####################################
st.divider()

# expander para mostrar os dados disponíveis para download
with st.expander("📥 Dados Disponíveis para Download", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.info(
            """
            Os dados disponíveis para download incluem os tetos financeiros por unidade de conservação, 
            iniciativa e ano.
            """
        )
    with col2:
        st.info(
            """
            Você pode baixar os dados em formato CSV, JSON ou Excel.
            """
        )

    st.divider()
    st.markdown("##### Tabela de Tetos Financeiros e Distribuição por Eixo Temático")

    # Consultar tf_distribuicao_elegiveis completa
    conn = sqlite3.connect(DB_PATH)
    df_tetos_completo = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
    conn.close()

    df_show = df_tetos_completo.copy().reset_index(drop=True)

    # Insere coluna "No" manual
    df_show.insert(0, "No", range(1, len(df_show) + 1))

    # formatar texto coluna DEMANDANTE (diretoria) com uppercase
    if "DEMANDANTE (diretoria)" in df_show.columns:
        df_show["DEMANDANTE (diretoria)"] = df_show["DEMANDANTE (diretoria)"].str.upper()
    # formatar texto coluna UnidadeConservacao com title case
    if "UnidadeConservacao" in df_show.columns:
        df_show["UnidadeConservacao"] = df_show["UnidadeConservacao"].str.title()
    # formatar texto coluna Nome da Proposta/Iniciativa Estruturante com title case
    if "Nome da Proposta/Iniciativa Estruturante" in df_show.columns:
        df_show["Nome da Proposta/Iniciativa Estruturante"] = df_show["Nome da Proposta/Iniciativa Estruturante"].str.title()

    st.dataframe(df_show, use_container_width=True, hide_index=True, column_config={
        "No": st.column_config.NumberColumn(format="%d"),
        "UnidadeConservacao": st.column_config.TextColumn(),
        "TetoSaldo disponível": st.column_config.NumberColumn(format="accounting", help="R$"),
        "TetoPrevisto 2025": st.column_config.NumberColumn(format="accounting", help="R$"),
        "TetoPrevisto 2026": st.column_config.NumberColumn(format="accounting", help="R$"),
        "TetoPrevisto 2027": st.column_config.NumberColumn(format="accounting", help="R$"),
        "TetoTotalDisponivel": st.column_config.NumberColumn(format="accounting", help="R$"),
        "A Distribuir": st.column_config.NumberColumn(format="accounting", help="R$"),
        "Nome da Proposta/Iniciativa Estruturante": st.column_config.TextColumn(),
        "DEMANDANTE (diretoria)": st.column_config.TextColumn(),
        "CNUC": st.column_config.TextColumn()
    })

    col1, col2, col3 = st.columns(3)

    with col1:
        # Botão de download
        csv_data = df_show.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar CSV",
            data=csv_data,
            file_name="consulta_tetos.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        # Transformar os dados para o formato JSON
        df_json_corrected = df_tetos_completo.to_json(orient="records")
        st.download_button(
            label="Baixar JSON",
            data=df_json_corrected,
            file_name="consulta_tetos.json",
            mime="application/json",
            use_container_width=True
        )

    import io

    with col3:
        # Botão de download em Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_show.to_excel(writer, index=False)
        st.download_button(
            label="Baixar Excel",
            data=buffer,
            file_name="consulta_tetos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
