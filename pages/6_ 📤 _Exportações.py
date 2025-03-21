import streamlit as st
import pandas as pd
import sqlite3
import os
import numpy as np
import plotly.express as px
import plotly 
import json
import io

from init_db import init_database
from init_db import init_samge_database

DB_PATH = "database/app_data.db"  # Ajuste o caminho do seu DB

####################################
# 1) Verificação de Login e Perfil #
####################################
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

# if st.session_state["perfil"] != "admin":
#     st.warning("🔒 Acesso negado! Você não tem permissão para acessar esta seção.")
#     st.stop()

#######################################
# 2) Configurações Gerais da Página   #
#######################################
st.set_page_config(
    page_title="Exportações - Dados para Download",
    page_icon="📤",
    layout="wide"
)

st.subheader("Dados para Download")

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
    
    # Normaliza os dados para comparação
    if "DEMANDANTE (diretoria)" in df.columns and "setor" in st.session_state:
        df["DEMANDANTE (diretoria)"] = df["DEMANDANTE (diretoria)"].str.upper()
        setor_usuario = st.session_state["setor"].upper()
        
        # Verifica se o perfil é admin ou cocam
        if st.session_state["perfil"] not in ["admin", "cocam"]:
            df = df[df["DEMANDANTE (diretoria)"] == setor_usuario]
    
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

# -----------------------------------------------------------------------------
# 12) Exibição detalhada e download dos dados (somente para admin ou cocam)
# -----------------------------------------------------------------------------

# se usuário for admin, exibe o expander abaixo
if st.session_state["usuario_logado"] and (
    st.session_state["perfil"] == "admin" or st.session_state["perfil"] == "cocam"
):

    st.markdown(
        """
        <div style="text-align: center; background-color: #fff3cd; padding: 10px; border-radius: 15px; border: 1px solid #ffeeba;">
        Nesta página, você pode baixar dados detalhados sobre os tetos financeiros disponíveis por ano, 
        distribuídos por unidade de conservação, iniciativa e eixo temático. Também estão disponíveis dados
        sobre as regras de negócio e tetos financeiros, além de informações sobre alocação e resumos SEI.
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div style="text-align: center; background-color: #f8d7da; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
            ⚠️ Seção disponível apenas para usuários com perfil cocam ou admin.
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            """
            <div style="text-align: center; background-color: #d1ecf1; padding: 10px; border-radius: 5px;">
            Dados disponíveis em formato CSV, JSON ou Excel.
            </div>
            """,
            unsafe_allow_html=True
        )
        # caption informando que a exportação de todos os dados em um único arquivo está ao final da página
        st.caption("🔽 Para exportar todos os dados em um único arquivo, role até o final da página.")

    



    #####################################
    # 10) Exibição Detalhada e Download #
    #####################################


    st.divider()

    
    st.markdown("##### Regras de Negócio e Tetos Financeiros")
    

    # expander para mostrar os dados disponíveis para download
    with st.expander("📑 Tabela de Tetos Financeiros e Distribuição por Eixo Temático", expanded=False):
        
        st.divider()
        st.markdown("##### Tetos Financeiros e Distribuição por Eixo Temático")

        # Consultar tf_distribuicao_elegiveis completa
        conn = sqlite3.connect(DB_PATH)
        df_tetos_completo = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
        conn.close()

        df_show = df_tetos_completo.copy().reset_index(drop=True)

        # formatar texto coluna DEMANDANTE (diretoria) com uppercase
        if "DEMANDANTE (diretoria)" in df_show.columns:
            df_show["DEMANDANTE (diretoria)"] = df_show["DEMANDANTE (diretoria)"].str.upper()
        # formatar texto coluna UnidadeConservacao com title case
        if "UnidadeConservacao" in df_show.columns:
            df_show["UnidadeConservacao"] = df_show["UnidadeConservacao"].str.title()
        # formatar texto coluna Nome da Proposta/Iniciativa Estruturante com title case
        if "Nome da Proposta/Iniciativa Estruturante" in df_show.columns:
            df_show["Nome da Proposta/Iniciativa Estruturante"] = df_show["Nome da Proposta/Iniciativa Estruturante"].str.title()

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "UnidadeConservacao": st.column_config.TextColumn(),
                "TetoSaldo disponível": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2025": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2026": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2027": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoTotalDisponivel": st.column_config.NumberColumn(format="localized", help="R$"),
                "A Distribuir": st.column_config.NumberColumn(format="localized", help="R$"),
                "Nome da Proposta/Iniciativa Estruturante": st.column_config.TextColumn(),
                "DEMANDANTE (diretoria)": st.column_config.TextColumn(),
                "CNUC": st.column_config.TextColumn()
            }
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            # Botão de download CSV
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



    # seção de dados do banco de dados : tf_cadastro_regras_negocio
    # gerar exportações excel e json dos cadastros de regras de negócio
    with st.expander("📊 Regras de Negócio", expanded=False):
        st.markdown("##### Tabela Registros dos Cadastro de Regras de Negócio")

        # 1) Ler tabela de regras de negócio (tf_cadastro_regras_negocio) do banco
        conn = sqlite3.connect(DB_PATH)
        df_regras = pd.read_sql_query("SELECT * FROM tf_cadastro_regras_negocio", conn)
        conn.close()

        if df_regras.empty:
            st.warning("Tabela 'tf_cadastro_regras_negocio' está vazia.")

        # 2) Exibir a tabela de regras de negócio
        st.dataframe(df_regras, use_container_width=True, hide_index=True)

        # 3) Botões para download em CSV, JSON e Excel
        col1, col2, col3 = st.columns(3)

        with col1:
            csv_data_regras = df_regras.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Baixar CSV - Regras de Negócio",
                data=csv_data_regras,
                file_name="td_cadastro_regras_negocio.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv_regras"
            )

        with col2:
            json_data_regras = df_regras.to_json(orient="records")
            st.download_button(
                label="Baixar JSON - Regras de Negócio",
                data=json_data_regras,
                file_name="td_cadastro_regras_negocio.json",
                mime="application/json",
                use_container_width=True,
                key="download_json_regras"
            )

        with col3:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_regras.to_excel(writer, index=False)
            st.download_button(
                label="Baixar Excel - Regras de Negócio",
                data=buffer,
                file_name="td_cadastro_regras_negocio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_excel_regras"
            )

        st.divider()
        st.markdown("##### Tabela de Regras de Negócio (Processos, Ações, Insumos)")

        # 1) Ler novamente, além de insumos, iniciativas, etc.
        conn = sqlite3.connect(DB_PATH)
        df_regras = pd.read_sql_query("SELECT * FROM tf_cadastro_regras_negocio", conn)
        df_insumos = pd.read_sql_query("SELECT * FROM td_insumos", conn)
        df_acoes = pd.read_sql_query("SELECT * FROM td_samge_acoes_manejo", conn)
        df_iniciativas = pd.read_sql_query("SELECT * FROM td_iniciativas", conn)
        conn.close()

        if df_regras.empty:
            st.warning("Tabela 'tf_cadastro_regras_negocio' está vazia.")
        else:
            # 2) Filtrar para exibir somente o registro mais recente de cada iniciativa
            df_regras['data_hora'] = pd.to_datetime(df_regras['data_hora'])
            df_regras = df_regras.sort_values('data_hora').groupby('id_iniciativa').tail(1)

            def process_regra(regra_json):
                """Processa a coluna `regra` em formato JSON."""
                regra = json.loads(regra_json)
                objetivo_geral = regra.get("objetivo_geral", "")
                objetivos_especificos = regra.get("objetivos_especificos", [])
                eixos_tematicos = regra.get("eixos_tematicos", [])
                acoes = regra.get("acoes", [])
                insumos = regra.get("insumos", [])
                return objetivo_geral, objetivos_especificos, eixos_tematicos, acoes, insumos

            processed_data = []
            for _, row in df_regras.iterrows():
                (objetivo_geral,
                 objetivos_especificos,
                 eixos_tematicos,
                 acoes,
                 insumos) = process_regra(row['regra'])

                nome_iniciativa = ""
                temp_iniciativa = df_iniciativas[df_iniciativas['id_iniciativa'] == row['id_iniciativa']]
                if not temp_iniciativa.empty:
                    nome_iniciativa = temp_iniciativa['nome_iniciativa'].values[0]

                for objetivo in objetivos_especificos:
                    for eixo in eixos_tematicos:
                        for acao in acoes:
                            temp_acao = df_acoes[df_acoes['id_ac'] == int(acao)]
                            acao_nome = temp_acao['nome'].values[0] if not temp_acao.empty else acao
                            for insumo in insumos:
                                insumo_data = df_insumos[df_insumos['id'] == int(insumo)]
                                if not insumo_data.empty:
                                    insumo_nome = insumo_data['descricao_insumo'].values[0]
                                    elemento_despesa = insumo_data['elemento_despesa'].values[0]
                                    especificacao_padrao = insumo_data['especificacao_padrao'].values[0]
                                    preco_referencia = insumo_data['preco_referencia'].values[0]
                                else:
                                    insumo_nome = insumo
                                    elemento_despesa = ""
                                    especificacao_padrao = ""
                                    preco_referencia = ""

                                processed_data.append([
                                    row['id_iniciativa'], 
                                    nome_iniciativa, 
                                    objetivo_geral, 
                                    objetivo, 
                                    eixo['id_eixo'], 
                                    eixo['nome_eixo'], 
                                    acao, 
                                    acao_nome, 
                                    insumo, 
                                    insumo_nome, 
                                    elemento_despesa, 
                                    especificacao_padrao, 
                                    preco_referencia
                                ])

            df_processed = pd.DataFrame(processed_data, columns=[
                'id_iniciativa', 
                'nome_iniciativa', 
                'objetivo_geral', 
                'objetivo_especifico', 
                'id_eixo_tematico', 
                'eixo_tematico', 
                'id_acao', 
                'acao', 
                'id_insumo', 
                'insumo', 
                'elemento_despesa', 
                'especificacao_padrao', 
                'preco_referencia'
            ])

            # 4) Exibir a tabela de regras de negócio
            st.dataframe(df_processed, use_container_width=True, hide_index=True)

            # 5) colunas para botão de download em CSV, JSON e Excel da tabela inteira
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_regras = df_processed.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Regras de Negócio",
                    data=csv_data_regras,
                    file_name="regras_negocio.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_regras_regras"
                )
            
            with col2:
                json_data_regras = df_processed.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Regras de Negócio",
                    data=json_data_regras,
                    file_name="regras_negocio.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_regras_regras"
                )
            
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_processed.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Regras de Negócio",
                    data=buffer,
                    file_name="regras_negocio.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_regras_regras"
                )

        st.divider()
        st.markdown("##### Tabela de Distribuição por Eixo Temático")
        # 1) Ler tabela de distribuição (tf_distribuicao_elegiveis) do banco
        conn = sqlite3.connect(DB_PATH)
        df_tetos_completo = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
        conn.close()
        if df_tetos_completo.empty:
            st.warning("Tabela 'tf_distribuicao_elegiveis' está vazia.")

        st.dataframe(
            df_tetos_completo,
            use_container_width=True,
            hide_index=True,
            column_config={
                "UnidadeConservacao": st.column_config.TextColumn(),
                "TetoSaldo disponível": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2025": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2026": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoPrevisto 2027": st.column_config.NumberColumn(format="localized", help="R$"),
                "TetoTotalDisponivel": st.column_config.NumberColumn(format="localized", help="R$"),
                "A Distribuir": st.column_config.NumberColumn(format="localized", help="R$"),
                "Nome da Proposta/Iniciativa Estruturante": st.column_config.TextColumn(),
                "DEMANDANTE (diretoria)": st.column_config.TextColumn(),
                "CNUC": st.column_config.TextColumn()
            }
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            csv_data_tetos = df_tetos_completo.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Baixar CSV - Distribuição por Eixo Temático",
                data=csv_data_tetos,
                file_name="distribuicao_eixo_tematico.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv_tetos"
            )
        with col2:
            json_data_tetos = df_tetos_completo.to_json(orient="records")
            st.download_button(
                label="Baixar JSON - Distribuição por Eixo Temático",
                data=json_data_tetos,
                file_name="distribuicao_eixo_tematico.json",
                mime="application/json",
                use_container_width=True,
                key="download_json_tetos"
            )
        with col3:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_tetos_completo.to_excel(writer, index=False)
            st.download_button(
                label="Baixar Excel - Distribuição por Eixo Temático",
                data=buffer,
                file_name="distribuicao_eixo_tematico.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_excel_tetos"
            )

      

    st.divider()

    # -----------------------------------------------------------------------------
    # EXPANDERS PARA TABELAS DE INFORMAÇÕES INICIAIS DAS INICIATIVAS
    # -----------------------------------------------------------------------------

    st.markdown("##### Dados Diversos : Informações Iniciais das Iniciativas e tabelas de referência")

    with st.expander("📊 Tabela de Dados Consolidados da Iniciativas (valores alocados e valores da iniciativas)", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_dados_base_iniciativas = pd.read_sql_query("SELECT * FROM td_dados_base_iniciativas", conn)
        conn.close()
        st.markdown("##### Tabela de Dados Base das Iniciativas")
        if df_dados_base_iniciativas.empty:
            st.warning("Tabela 'td_dados_base_iniciativas' está vazia.")
        else:
            st.dataframe(df_dados_base_iniciativas, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_dados_base = df_dados_base_iniciativas.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Dados Base das Iniciativas",
                    data=csv_data_dados_base,
                    file_name="dados_base_iniciativas.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_dados_base"
                )
            with col2:
                json_data_dados_base = df_dados_base_iniciativas.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Dados Base das Iniciativas",
                    data=json_data_dados_base,
                    file_name="dados_base_iniciativas.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_dados_base"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_dados_base_iniciativas.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Dados Base das Iniciativas",
                    data=buffer,
                    file_name="dados_base_iniciativas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_dados_base"
                )

    with st.expander("📊 Tabela de Resumos (informações SEI)", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_dados_resumos_sei = pd.read_sql_query("SELECT * FROM td_dados_resumos_sei", conn)
        conn.close()
        st.markdown("##### Tabela de Resumos SEI")
        if df_dados_resumos_sei.empty:
            st.warning("Tabela 'td_dados_resumos_sei' está vazia.")
        else:
            st.dataframe(df_dados_resumos_sei, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_resumos = df_dados_resumos_sei.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Resumos SEI",
                    data=csv_data_resumos,
                    file_name="resumos_sei.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_resumos2"
                )
            with col2:
                json_data_resumos = df_dados_resumos_sei.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Resumos SEI",
                    data=json_data_resumos,
                    file_name="resumos_sei.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_resumos2"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_dados_resumos_sei.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Resumos SEI",
                    data=buffer,
                    file_name="resumos_sei.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_resumos2"
                )


# -----------------------------------------------------------------------------
# 13) Exibição de dados do banco de dados (somente para admin)
# -----------------------------------------------------------------------------

# se usuário for admin, exibe o expander abaixo
if st.session_state["usuario_logado"] and st.session_state["perfil"] == "admin":
    # -----------------------------------------------------------------------------
    # EXPANDERS PARA TABELAS DE DIMENSÃO
    # -----------------------------------------------------------------------------

    # Cada tabela em seu próprio expander

    # Demandantes
    with st.expander("📊 Tabela Dimensão: Demandantes", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_demandantes = pd.read_sql_query("SELECT * FROM td_demandantes", conn)
        conn.close()
        st.markdown("##### Tabela de Demandantes")
        if df_demandantes.empty:
            st.warning("Tabela 'td_demandantes' está vazia.")
        else:
            st.dataframe(df_demandantes, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_demandantes = df_demandantes.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Demandantes",
                    data=csv_data_demandantes,
                    file_name="demandantes.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_demandantes"
                )
            with col2:
                json_data_demandantes = df_demandantes.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Demandantes",
                    data=json_data_demandantes,
                    file_name="demandantes.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_demandantes"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_demandantes.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Demandantes",
                    data=buffer,
                    file_name="demandantes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_demandantes"
                )

    # Iniciativas
    with st.expander("📊 Tabela Dimensão: Iniciativas", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_iniciativas = pd.read_sql_query("SELECT * FROM td_iniciativas", conn)
        conn.close()
        st.markdown("##### Tabela de Iniciativas")
        if df_iniciativas.empty:
            st.warning("Tabela 'td_iniciativas' está vazia.")
        else:
            st.dataframe(df_iniciativas, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_iniciativas = df_iniciativas.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Iniciativas",
                    data=csv_data_iniciativas,
                    file_name="iniciativas.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_iniciativas_dim"
                )
            with col2:
                json_data_iniciativas = df_iniciativas.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Iniciativas",
                    data=json_data_iniciativas,
                    file_name="iniciativas.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_iniciativas_dim"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_iniciativas.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Iniciativas",
                    data=buffer,
                    file_name="iniciativas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_iniciativas_dim"
                )

    # Ação de Aplicação (td_acoes_aplicacao)
    with st.expander("📊 Tabela Dimensão: Ação de Aplicação", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_acoes_aplicacao = pd.read_sql_query("SELECT * FROM td_acoes_aplicacao", conn)
        conn.close()
        st.markdown("##### Tabela de Ação de Aplicação")
        if df_acoes_aplicacao.empty:
            st.warning("Tabela 'td_acoes_aplicacao' está vazia.")
        else:
            st.dataframe(df_acoes_aplicacao, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_acoes_aplicacao = df_acoes_aplicacao.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Ação de Aplicação",
                    data=csv_data_acoes_aplicacao,
                    file_name="acoes_aplicacao.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_acoes_aplicacao"
                )
            with col2:
                json_data_acoes_aplicacao = df_acoes_aplicacao.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Ação de Aplicação",
                    data=json_data_acoes_aplicacao,
                    file_name="acoes_aplicacao.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_acoes_aplicacao"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_acoes_aplicacao.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Ação de Aplicação",
                    data=buffer,
                    file_name="acoes_aplicacao.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_acoes_aplicacao"
                )
                

    # Insumos
    with st.expander("📊 Tabela Dimensão: Insumos", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_insumos = pd.read_sql_query("SELECT * FROM td_insumos", conn)
        conn.close()
        st.markdown("##### Tabela de Insumos")
        if df_insumos.empty:
            st.warning("Tabela 'td_insumos' está vazia.")
        else:
            st.dataframe(df_insumos, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_insumos = df_insumos.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Insumos",
                    data=csv_data_insumos,
                    file_name="insumos.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_insumos"
                )
            with col2:
                json_data_insumos = df_insumos.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Insumos",
                    data=json_data_insumos,
                    file_name="insumos.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_insumos"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_insumos.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Insumos",
                    data=buffer,
                    file_name="insumos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_insumos"
                )

    # Ações de Manejo
    with st.expander("📊 Tabela Dimensão: Ações de Manejo", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_acoes = pd.read_sql_query("SELECT * FROM td_samge_acoes_manejo", conn)
        conn.close()
        st.markdown("##### Tabela de Ações de Manejo")
        if df_acoes.empty:
            st.warning("Tabela 'td_samge_acoes_manejo' está vazia.")
        else:
            st.dataframe(df_acoes, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_acoes = df_acoes.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Ações de Manejo",
                    data=csv_data_acoes,
                    file_name="acoes_manejo.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_acoes"
                )
            with col2:
                json_data_acoes = df_acoes.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Ações de Manejo",
                    data=json_data_acoes,
                    file_name="acoes_manejo.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_acoes"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_acoes.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Ações de Manejo",
                    data=buffer,
                    file_name="acoes_manejo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_acoes"
                )

    # Processos
    with st.expander("📊 Tabela Dimensão: Processos", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_processos = pd.read_sql_query("SELECT * FROM td_samge_processos", conn)
        conn.close()
        st.markdown("##### Tabela de Processos")
        if df_processos.empty:
            st.warning("Tabela 'td_samge_processos' está vazia.")
        else:
            st.dataframe(df_processos, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_processos = df_processos.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Processos",
                    data=csv_data_processos,
                    file_name="processos.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_processos"
                )
            with col2:
                json_data_processos = df_processos.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Processos",
                    data=json_data_processos,
                    file_name="processos.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_processos"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_processos.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Processos",
                    data=buffer,
                    file_name="processos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_processos"
                )

    # Macroprocessos
    with st.expander("📊 Tabela Dimensão: Macroprocessos", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_macroprocessos = pd.read_sql_query("SELECT * FROM td_samge_macroprocessos", conn)
        conn.close()
        st.markdown("##### Tabela de Macroprocessos")
        if df_macroprocessos.empty:
            st.warning("Tabela 'td_samge_macroprocessos' está vazia.")
        else:
            st.dataframe(df_macroprocessos, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_macroprocessos = df_macroprocessos.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Macroprocessos",
                    data=csv_data_macroprocessos,
                    file_name="macroprocessos.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_macroprocessos"
                )
            with col2:
                json_data_macroprocessos = df_macroprocessos.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Macroprocessos",
                    data=json_data_macroprocessos,
                    file_name="macroprocessos.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_macroprocessos"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_macroprocessos.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Macroprocessos",
                    data=buffer,
                    file_name="macroprocessos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_macroprocessos"
                )

    # Atividades
    with st.expander("📊 Tabela Dimensão: Atividades", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_atividades = pd.read_sql_query("SELECT * FROM td_samge_atividades", conn)
        conn.close()
        st.markdown("##### Tabela de Atividades")
        if df_atividades.empty:
            st.warning("Tabela 'td_samge_atividades' está vazia.")
        else:
            st.dataframe(df_atividades, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_atividades = df_atividades.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Atividades",
                    data=csv_data_atividades,
                    file_name="atividades.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_atividades"
                )
            with col2:
                json_data_atividades = df_atividades.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Atividades",
                    data=json_data_atividades,
                    file_name="atividades.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_atividades"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_atividades.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Atividades",
                    data=buffer,
                    file_name="atividades.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_atividades"
                )

    # Unidades
    with st.expander("📊 Tabela Dimensão: Unidades", expanded=False):
        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_unidades = pd.read_sql_query("SELECT * FROM td_unidades", conn)
        conn.close()
        st.markdown("##### Tabela de Unidades")
        if df_unidades.empty:
            st.warning("Tabela 'td_unidades' está vazia.")
        else:
            st.dataframe(df_unidades, use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_data_unidades = df_unidades.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV - Unidades",
                    data=csv_data_unidades,
                    file_name="unidades.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_unidades"
                )
            with col2:
                json_data_unidades = df_unidades.to_json(orient="records")
                st.download_button(
                    label="Baixar JSON - Unidades",
                    data=json_data_unidades,
                    file_name="unidades.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_unidades"
                )
            with col3:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_unidades.to_excel(writer, index=False)
                st.download_button(
                    label="Baixar Excel - Unidades",
                    data=buffer,
                    file_name="unidades.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_excel_unidades"
                )


    # -----------------------------------------------------------------------------
    # 12) Debugging - Exibir o estado da sessão (opcional)
    # st.write(st.session_state)
    # -----------------------------------------------------------------------------




    st.divider()

    # seção para download de todos os dados disponíveis em um único arquivo, formatos csv, json e excel. 
    # nos formatos csv e excel, cada tabela deve ser uma aba separada
    st.markdown("##### Download de Todos os Dados Disponíveis")
    st.markdown("""
    Você pode baixar todos os dados disponíveis em um único arquivo. Os dados estão organizados em diferentes tabelas,
    cada uma representando uma parte do sistema. Os formatos disponíveis para download são CSV, JSON e Excel.
    """)

    # aproveitar das consultas já realizadas nas tabelas de dimensão e regras de negócio e disponibilizar o download
    # de todas as tabelas em um único arquivo Excel
    # tabela tetos_completo já foi lida e está disponível na variável df_tetos_completo
    # tabela regras já foi lida e está disponível na variável df_regras
    # tabela dados_base já foi lida e está disponível na variável df_dados_base_iniciativas
    # tabela resumos já foi lida e está disponível na variável df_dados_resumos_sei
    # tabela demandantes já foi lida e está disponível na variável df_demandantes
    # tabela iniciativas já foi lida e está disponível na variável df_iniciativas
    # tabela acoes_aplicacao já foi lida e está disponível na variável df_acoes_aplicacao
    # tabela insumos já foi lida e está disponível na variável df_insumos
    # tabela acoes já foi lida e está disponível na variável df_acoes
    # tabela processos já foi lida e está disponível na variável df_processos
    # tabela macroprocessos já foi lida e está disponível na variável df_macroprocessos
    # tabela atividades já foi lida e está disponível na variável df_atividades
    # tabela unidades já foi lida e está disponível na variável df_unidades
    # tabela regras_negocio_processada já foi lida e está disponível na variável df_processed
    conn = sqlite3.connect(DB_PATH)
    df_regras = pd.read_sql_query("SELECT * FROM tf_cadastro_regras_negocio", conn)
    df_insumos = pd.read_sql_query("SELECT * FROM td_insumos", conn)
    df_acoes = pd.read_sql_query("SELECT * FROM td_samge_acoes_manejo", conn)
    df_iniciativas = pd.read_sql_query("SELECT * FROM td_iniciativas", conn)
    conn.close()

    def process_regra(regra_json):
        """Processa a coluna `regra` em formato JSON."""
        regra = json.loads(regra_json)
        objetivo_geral = regra.get("objetivo_geral", "")
        objetivos_especificos = regra.get("objetivos_especificos", [])
        eixos_tematicos = regra.get("eixos_tematicos", [])
        acoes = regra.get("acoes", [])
        insumos = regra.get("insumos", [])
        return objetivo_geral, objetivos_especificos, eixos_tematicos, acoes, insumos

    processed_data = []
    for _, row in df_regras.iterrows():
        (objetivo_geral,
         objetivos_especificos,
         eixos_tematicos,
         acoes,
         insumos) = process_regra(row['regra'])

        nome_iniciativa = ""
        temp_iniciativa = df_iniciativas[df_iniciativas['id_iniciativa'] == row['id_iniciativa']]
        if not temp_iniciativa.empty:
            nome_iniciativa = temp_iniciativa['nome_iniciativa'].values[0]

        for objetivo in objetivos_especificos:
            for eixo in eixos_tematicos:
                for acao in acoes:
                    temp_acao = df_acoes[df_acoes['id_ac'] == int(acao)]
                    acao_nome = temp_acao['nome'].values[0] if not temp_acao.empty else acao
                    for insumo in insumos:
                        insumo_data = df_insumos[df_insumos['id'] == int(insumo)]
                        if not insumo_data.empty:
                            insumo_nome = insumo_data['descricao_insumo'].values[0]
                            elemento_despesa = insumo_data['elemento_despesa'].values[0]
                            especificacao_padrao = insumo_data['especificacao_padrao'].values[0]
                            preco_referencia = insumo_data['preco_referencia'].values[0]
                        else:
                            insumo_nome = insumo
                            elemento_despesa = ""
                            especificacao_padrao = ""
                            preco_referencia = ""

                        processed_data.append([
                            row['id_iniciativa'], 
                            nome_iniciativa, 
                            objetivo_geral, 
                            objetivo, 
                            eixo['id_eixo'], 
                            eixo['nome_eixo'], 
                            acao, 
                            acao_nome, 
                            insumo, 
                            insumo_nome, 
                            elemento_despesa, 
                            especificacao_padrao, 
                            preco_referencia
                        ])

    df_processed = pd.DataFrame(processed_data, columns=[
        'id_iniciativa', 
        'nome_iniciativa', 
        'objetivo_geral', 
        'objetivo_especifico', 
        'id_eixo_tematico', 
        'eixo_tematico', 
        'id_acao', 
        'acao', 
        'id_insumo', 
        'insumo', 
        'elemento_despesa', 
        'especificacao_padrao', 
        'preco_referencia'
    ])
    # criar um arquivo Excel com todas as tabelas
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_tetos_completo.to_excel(writer, sheet_name='tetos_completo', index=False)
        df_regras.to_excel(writer, sheet_name='regras', index=False)
        df_processed.to_excel(writer, sheet_name='regras_negocio_processada', index=False)
        df_dados_base_iniciativas.to_excel(writer, sheet_name='dados_base_iniciativas', index=False)
        df_dados_resumos_sei.to_excel(writer, sheet_name='dados_resumos_sei', index=False)
        df_demandantes.to_excel(writer, sheet_name='demandantes', index=False)
        df_iniciativas.to_excel(writer, sheet_name='iniciativas', index=False)
        df_acoes_aplicacao.to_excel(writer, sheet_name='acoes_aplicacao', index=False)
        df_insumos.to_excel(writer, sheet_name='insumos', index=False)
        df_acoes.to_excel(writer, sheet_name='acoes', index=False)
        df_processos.to_excel(writer, sheet_name='processos', index=False)
        df_macroprocessos.to_excel(writer, sheet_name='macroprocessos', index=False)
        df_atividades.to_excel(writer, sheet_name='atividades', index=False)
        df_unidades.to_excel(writer, sheet_name='unidades', index=False)
    buffer.seek(0)
    st.download_button(
        label="Baixar Todos os Dados Disponíveis (Excel)",
        data=buffer,
        file_name="todos_dados_disponiveis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
    st.markdown("""
    Você também pode baixar todos os dados disponíveis em um único arquivo CSV ou JSON.
    Os dados estão organizados em diferentes tabelas, cada uma representando uma parte do sistema.
    """)
    # criar um arquivo CSV com todas as tabelas
    buffer_csv = io.StringIO()
    df_tetos_completo.to_csv(buffer_csv, index=False)
    df_regras.to_csv(buffer_csv, index=False)
    df_processed.to_csv(buffer_csv, index=False)
    df_dados_base_iniciativas.to_csv(buffer_csv, index=False)
    df_dados_resumos_sei.to_csv(buffer_csv, index=False)
    df_demandantes.to_csv(buffer_csv, index=False)
    df_iniciativas.to_csv(buffer_csv, index=False)
    df_acoes_aplicacao.to_csv(buffer_csv, index=False)
    df_insumos.to_csv(buffer_csv, index=False)
    df_acoes.to_csv(buffer_csv, index=False)
    df_processos.to_csv(buffer_csv, index=False)
    df_macroprocessos.to_csv(buffer_csv, index=False)
    df_atividades.to_csv(buffer_csv, index=False)
    df_unidades.to_csv(buffer_csv, index=False)
    buffer_csv.seek(0)
    st.download_button(
        label="Baixar Todos os Dados Disponíveis (CSV)",
        data=buffer_csv.getvalue(),
        file_name="todos_dados_disponiveis.csv",
        mime="text/csv",
        use_container_width=True
    )
    # criar um arquivo JSON com todas as tabelas
    def convert_timestamps(data):
        if isinstance(data, dict):
            return {k: convert_timestamps(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [convert_timestamps(v) for v in data]
        elif isinstance(data, pd.Timestamp):
            return data.isoformat()
        else:
            return data

    all_data = {
        "tetos_completo": convert_timestamps(df_tetos_completo.to_dict(orient='records')),
        "regras": convert_timestamps(df_regras.to_dict(orient='records')),
        "regras_negocio_processada": convert_timestamps(df_processed.to_dict(orient='records')),
        "dados_base_iniciativas": convert_timestamps(df_dados_base_iniciativas.to_dict(orient='records')),
        "dados_resumos_sei": convert_timestamps(df_dados_resumos_sei.to_dict(orient='records')),
        "demandantes": convert_timestamps(df_demandantes.to_dict(orient='records')),
        "iniciativas": convert_timestamps(df_iniciativas.to_dict(orient='records')),
        "acoes_aplicacao": convert_timestamps(df_acoes_aplicacao.to_dict(orient='records')),
        "insumos": convert_timestamps(df_insumos.to_dict(orient='records')),
        "acoes": convert_timestamps(df_acoes.to_dict(orient='records')),
        "processos": convert_timestamps(df_processos.to_dict(orient='records')),
        "macroprocessos": convert_timestamps(df_macroprocessos.to_dict(orient='records')),
        "atividades": convert_timestamps(df_atividades.to_dict(orient='records')),
        "unidades": convert_timestamps(df_unidades.to_dict(orient='records'))
    }
    buffer_json = io.StringIO()
    json.dump(all_data, buffer_json)
    buffer_json.seek(0)
    st.download_button(
        label="Baixar Todos os Dados Disponíveis (JSON)",
        data=buffer_json.getvalue(),
        file_name="todos_dados_disponiveis.json",
        mime="application/json",
        use_container_width=True
    )