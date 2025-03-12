import streamlit as st
import pandas as pd
import sqlite3
import os
import numpy as np

from init_db import init_database
from init_db import init_samge_database


db_path = "database/app_data.db"

# 📌 Verifica se o usuário está logado antes de permitir acesso à página
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

# não mostrar página se o perfil for diferente de admin
if st.session_state["perfil"] != "admin":
    st.warning("🔒 Acesso negado! Você não tem permissão para acessar esta seção.")
    st.stop()


st.set_page_config(
    page_title="Consultar Tetos FCA 2025",
    page_icon="♾️",
    layout="wide"
    )



st.subheader("Informações sobre as Iniciativas Estruturantes")

@st.cache_data
def load_data_from_db():
    """Carrega os dados da tabela 'td_dados_base_iniciativas' do SQLite."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM td_dados_base_iniciativas", conn)
    conn.close()
    return df



# 📌 Verifica se o banco de dados existe antes de continuar
if not os.path.exists(db_path):
    st.warning("Banco de dados não encontrado. Verifique se executou o init_db.py.")
else:
    df = load_data_from_db()  # ⬅️ Agora `df` é carregado antes dos filtros

    if st.session_state["perfil"] == "admin":
        df_filtrado = df  # Admin vê todos os registros
        df = df_filtrado
    else:
        df_filtrado = df[df["DEMANDANTE"] == st.session_state["setor"]]
        df = df_filtrado


 



    if df.empty:
        st.warning("Nenhum dado encontrado no banco de dados.")
    else:
        # 📌 Layout para Filtros: Título + Botão "Limpar Filtros" ao lado
        col1, col2 = st.sidebar.columns([3, 1])
        col1.header("Filtros")

        with col2:
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
                # Resetando os filtros para "Todos"
                st.session_state["filtro_demandante"] = "Todos"
                st.session_state["filtro_uc"] = "Todas"
                st.session_state["filtro_gr"] = "Todos"
                st.session_state["filtro_uf"] = "Todas"
                st.session_state["filtro_bioma"] = "Todos"
                st.session_state["filtro_categoria"] = "Todas"
                st.session_state["iniciativa_selecionada"] = "Selecione uma opção..."
                st.rerun()

        # 📌 Aplicação de Filtros no Menu Lateral
        filtro_demandante = st.sidebar.selectbox("📌 Demandante", ["Todos"] + sorted(df["DEMANDANTE"].dropna().unique().tolist()), key="filtro_demandante")
        if filtro_demandante != "Todos":
            df = df[df["DEMANDANTE"] == filtro_demandante]

        filtro_uc = st.sidebar.selectbox("🏞 Unidade de Conservação", ["Todas"] + sorted(df["Unidade de Conservação"].dropna().unique().tolist()), key="filtro_uc")
        if filtro_uc != "Todas":
            df = df[df["Unidade de Conservação"] == filtro_uc]

        filtro_acao = st.sidebar.selectbox("🎯 Ação de Aplicação", ["Todas"] + sorted(df["AÇÃO DE APLICAÇÃO"].dropna().unique().tolist()), key="filtro_acao")
        if filtro_acao != "Todas":
            df = df[df["AÇÃO DE APLICAÇÃO"] == filtro_acao]

        filtro_gr = st.sidebar.selectbox("🏢 Gerência Regional", ["Todos"] + sorted(df["GR"].dropna().unique().tolist()), key="filtro_gr")
        if filtro_gr != "Todos":
            df = df[df["GR"] == filtro_gr]

        filtro_uf = st.sidebar.selectbox("📍 UF (Estado)", ["Todas"] + sorted(df["UF"].dropna().unique().tolist()), key="filtro_uf")
        if filtro_uf != "Todas":
            df = df[df["UF"] == filtro_uf]

        filtro_bioma = st.sidebar.selectbox("🌱 Bioma", ["Todos"] + sorted(df["BIOMA"].dropna().unique().tolist()), key="filtro_bioma")
        if filtro_bioma != "Todos":
            df = df[df["BIOMA"] == filtro_bioma]

        filtro_categoria = st.sidebar.selectbox("🏷 Categoria UC", ["Todas"] + sorted(df["CATEGORIA UC"].dropna().unique().tolist()), key="filtro_categoria")
        if filtro_categoria != "Todas":
            df = df[df["CATEGORIA UC"] == filtro_categoria]

        


        # 📌 Verifica se o usuário logado tem permissão para visualizar as configurações
        if st.session_state.get("usuario_logado") and st.session_state.get("perfil") == "admin":
            # 📌 Expander de Configurações (agora no final)
            with st.sidebar.expander("⚙️ Configurações", expanded=False):
                if st.button("🔄 Recriar Banco de Dados"):
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    try:
                        init_database()
                        init_samge_database()
                        st.success("Banco de dados recriado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao recriar o banco: {e}")

                if st.button("🗑 Limpar Cache"):
                    st.cache_data.clear()
                    st.success("Cache limpo com sucesso!")
                    st.rerun()

                # # ✅ Toggle para ativar/desativar a exibição de "Itens Omissos na Soma"
                # exibir_itens_omissos = st.checkbox("🔎 Exibir Itens Omissos na Soma", value=False)

        exibir_itens_omissos = False

        # 📊 Estatísticas Dinâmicas dentro de Expanders
        with st.expander("📊 Estatísticas Gerais", expanded=True):
            col1, col2, col3, col4, col5 = st.columns(5)  # Adicionamos uma 5ª coluna para o saldo
            
            total_iniciativas = df["Nome da Proposta/Iniciativa Estruturante"].nunique()
            total_ucs = df["Unidade de Conservação"].nunique()
            valor_alocado = df["VALOR TOTAL ALOCADO"].astype(float).sum()
            valor_total_iniciativa = df["Valor Total da Iniciativa"].astype(float).sum()
            saldo_total = df["SALDO"].astype(float).sum()  # Adicionamos o saldo total

            # 📌 Cálculo da % de valor alocado em relação ao total da iniciativa
            percentual_alocado = (valor_alocado / valor_total_iniciativa) * 100 if valor_total_iniciativa > 0 else 0

            col1.metric("📌 Total de Iniciativas", total_iniciativas)
            col2.metric("🏞 Total de UCs", total_ucs)
            col3.metric("💰 Valor Alocado", f"R$ {valor_alocado:,.2f}")
            col4.metric("💰 Valor Total da Iniciativa", f"R$ {valor_total_iniciativa:,.2f}")
            col5.metric("💰 Saldo", f"R$ {saldo_total:,.2f}")  # Mostra o saldo total

            # 📌 Exibição da % e da Progress Bar
            col4.markdown(f"💹 % Alocado: {percentual_alocado:.2f}%")
            col3.progress(min(percentual_alocado / 100, 1.0))  # 🔥 Garante que a progress bar não ultrapasse 100%

            st.markdown(
                """
                <style>
                div[data-testid="stMetricValue"] {
                    font-size: 16px !important;
                    font-weight: bold;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

        # 📌 Função para Destacar Totais na Tabela e Identificar Itens Omissos
        def destacar_totais(df, coluna_grupo):
            df_total = df.groupby(coluna_grupo).agg({
                "Nome da Proposta/Iniciativa Estruturante": "nunique",
                "Unidade de Conservação": "nunique",
                "VALOR TOTAL ALOCADO": lambda x: x.astype(float).sum(),
                "Valor Total da Iniciativa": lambda x: x.astype(float).sum(),
                "SALDO": lambda x: x.astype(float).sum()  # Adicionamos o saldo na agregação
            }).rename(columns={
                "Nome da Proposta/Iniciativa Estruturante": "Total de Iniciativas",
                "Unidade de Conservação": "Total de UCs"
            }).reset_index()

            # 📌 Evitar divisão por zero ao calcular a % de Valor Alocado
            df_total["% Valor Alocado"] = np.where(
                df_total["Valor Total da Iniciativa"] > 0,
                (df_total["VALOR TOTAL ALOCADO"] / df_total["Valor Total da Iniciativa"]) * 100,
                0  # Se "Valor Total da Iniciativa" for 0, define como 0%
            )

            # 🔥 Garante que os valores sejam numéricos e sem infinitos
            df_total["% Valor Alocado"] = df_total["% Valor Alocado"].replace([np.inf, -np.inf], 0).fillna(0).round(2)

            # 📌 Criando a barra de progresso com valores limitados entre 0 e 100
            def gerar_barra_progresso(perc):
                total_blocos = 10  # Define a quantidade de blocos para a barra
                preenchidos = max(0, min(int((perc / 100) * total_blocos), total_blocos))  # Evita valores inválidos

                if perc > 100:
                    return "🟧" * preenchidos + "⬜" * (total_blocos - preenchidos)  # 🔥 Excesso em laranja
                return "🟩" * preenchidos + "⬜" * (total_blocos - preenchidos)  # 🔥 Normal em verde

            df_total["Progresso"] = df_total["% Valor Alocado"].apply(gerar_barra_progresso)


            total_geral = pd.DataFrame({
                coluna_grupo: ["Total Geral"],
                "Total de Iniciativas": [df_total["Total de Iniciativas"].sum()],
                "Total de UCs": [df_total["Total de UCs"].sum()],
                "VALOR TOTAL ALOCADO": [df_total["VALOR TOTAL ALOCADO"].sum()],
                "Valor Total da Iniciativa": [df_total["Valor Total da Iniciativa"].sum()],
                "SALDO": [df_total["SALDO"].sum()],  # Adicionamos o saldo total geral
                "% Valor Alocado": [(df_total["VALOR TOTAL ALOCADO"].sum() / df_total["Valor Total da Iniciativa"].sum()) * 100]
            })
            
            df_total = pd.concat([df_total, total_geral], ignore_index=True)

            # 🔎 Identificando Registros que Estão Fora da Soma
            itens_omissos = df[df["VALOR TOTAL ALOCADO"].astype(float) + df["Valor Total da Iniciativa"].astype(float) == 0]

            return df_total.style.format({
                "VALOR TOTAL ALOCADO": "R$ {:,.2f}",
                "Valor Total da Iniciativa": "R$ {:,.2f}",
                "SALDO": "R$ {:,.2f}",
                "% Valor Alocado": "{:.2f}%"
            }).set_properties(subset=["Progresso"], **{"text-align": "center"}), itens_omissos

        # 📊 Estatísticas Agregadas
        for nome, coluna in [
            ("📌   por Demandante", "DEMANDANTE"),
            ("📌   por Iniciativa", "Nome da Proposta/Iniciativa Estruturante"),
            ("🎯   por Ação de Aplicação","AÇÃO DE APLICAÇÃO"),
            ("🏞   por Unidade de Conservação", "Unidade de Conservação"),
            ("🏢   por Gerência Regional", "GR"),
            ("🌱   por Bioma", "BIOMA"),
            ("🏷   por Categoria UC", "CATEGORIA UC"),
            ("📍   por UF", "UF"),
            
        ]:
            with st.expander(nome):
                df_agregado, itens_fora = destacar_totais(df, coluna)
                st.dataframe(df_agregado, use_container_width=True)

                # ✅ Exibir Itens Omissos somente se o toggle estiver ativado
                if exibir_itens_omissos and not itens_fora.empty:
                    st.subheader(f"🔎 Itens Omissos na Soma - {coluna}")
                    st.dataframe(itens_fora, use_container_width=True)


        st.caption(":small_red_triangle_down: Role a página para baixo para visualizar mais informações.")
#################################################################################################


        # 📌 Seção de visualização detalhada da iniciativa selecionada
        st.divider()
        
        # 📌 Seção de visualização detalhada da iniciativa selecionada
        st.subheader("📋 Resumo Executivo da Iniciativa")

        iniciativa_selecionada = st.selectbox(
            "Selecione uma iniciativa:", 
            ["Selecione uma opção..."] + df["Nome da Proposta/Iniciativa Estruturante"].dropna().unique().tolist()
        )

        # Filtra apenas se uma iniciativa for selecionada
        if iniciativa_selecionada != "Selecione uma opção...":
            df_iniciativa = df[df["Nome da Proposta/Iniciativa Estruturante"] == iniciativa_selecionada]


        df_iniciativa = df[df["Nome da Proposta/Iniciativa Estruturante"] == iniciativa_selecionada]

        if not df_iniciativa.empty:
            demandante = df_iniciativa["DEMANDANTE"].iloc[0]
            gr_list = sorted(df_iniciativa["GR"].dropna().astype(str).unique())
            bioma_list = sorted(df_iniciativa["BIOMA"].dropna().astype(str).unique())
            uf_list = sorted(df_iniciativa["UF"].dropna().astype(str).unique())
            valor_total_alocado = df_iniciativa["VALOR TOTAL ALOCADO"].sum()
            valor_total_iniciativa = df_iniciativa["Valor Total da Iniciativa"].sum()
            # 📌 Extraindo valores únicos da coluna "Observações"
            observacoes_list = df_iniciativa["Observações"].dropna().astype(str).unique().tolist()

            unidades = df_iniciativa[["Unidade de Conservação", "VALOR TOTAL ALOCADO", "Valor Total da Iniciativa"]]
            
            st.divider()
            st.markdown("#### Nome da Iniciativa Estruturante")
            st.markdown(df_iniciativa["Nome da Proposta/Iniciativa Estruturante"].iloc[0])

            # 📌 Layout do relatório
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Informações Gerais")
                st.markdown(f"**📌 Demandante:** {demandante}")

                # 📌 Exibição dos números SEI
                sei_list = df_iniciativa["Nº SEI"].dropna().astype(int).astype(str).unique().tolist()
                if sei_list:
                    st.markdown("**📜 Nº SEI:**", unsafe_allow_html=True)
                    st.markdown(" ".join([f"<span class='tag'>{sei}</span>" for sei in sei_list]), unsafe_allow_html=True)

                # 📌 Exibição compacta de listas com tags estilizadas
                st.markdown("**📍 Gerências Regionais:**", unsafe_allow_html=True)
                st.markdown(" ".join([f"<span class='tag'>{gr}</span>" for gr in gr_list]), unsafe_allow_html=True)

                st.markdown("**🌿 Biomas:**", unsafe_allow_html=True)
                st.markdown(" ".join([f"<span class='tag'>{bioma}</span>" for bioma in bioma_list]), unsafe_allow_html=True)

                st.markdown("**📍 UFs:**", unsafe_allow_html=True)
                st.markdown(" ".join([f"<span class='tag'>{uf}</span>" for uf in uf_list]), unsafe_allow_html=True)

                # 📌 Exibição das Observações
                if observacoes_list:
                    st.markdown("**📝 Observações:**", unsafe_allow_html=True)
                    for obs in observacoes_list:
                        st.markdown(f"- {obs}")

            with col2:
                st.markdown("#### 📊 Valores Financeiros")
                st.metric(label="💰 Valor Total Alocado", value=f"R$ {valor_total_alocado:,.2f}")
                st.metric(label="🏗 Valor Total da Iniciativa", value=f"R$ {valor_total_iniciativa:,.2f}")

                # 📌 Cálculo do percentual do valor alocado
                percentual_valor_alocado = (valor_total_alocado / valor_total_iniciativa) * 100 if valor_total_iniciativa > 0 else 0
                percentual_valor_alocado = round(percentual_valor_alocado, 2)

                # 📌 Exibir percentual formatado
                st.markdown(f"**📊 Percentual de Valor Alocado: {percentual_valor_alocado}%**")

                # 📌 Ajuste para progress bar:
                if percentual_valor_alocado > 100:
                    st.warning("❕ O valor alocado ultrapassa 100% do total da iniciativa!")
                    st.progress(1.0)  # Mantém a barra cheia para valores acima de 100%
                else:
                    st.progress(percentual_valor_alocado / 100)  # Mantém o valor correto para ≤100%

                # 📌 Exibição das Ações de Aplicação
                acoes_list = sorted(df_iniciativa["AÇÃO DE APLICAÇÃO"].dropna().astype(str).unique())
                if acoes_list:
                    st.markdown("**🎯 Ações de Aplicação:**", unsafe_allow_html=True)
                    st.markdown(" ".join([f"<span class='tag'>{acao}</span>" for acao in acoes_list]), unsafe_allow_html=True)


                st.divider()

                # 📌 Tabela de Estatísticas dentro da mesma coluna
                st.markdown("##### 📊 Estatísticas da Iniciativa")
                uc_list = sorted(df_iniciativa["Unidade de Conservação"].unique())

                estatisticas = pd.DataFrame({
                    "Indicador": ["Gerências Regionais", "Unidades de Conservação", "Biomas", "UFs", "Ações de Aplicação"],
                    "Quantidade": [len(gr_list), len(uc_list), len(bioma_list), len(uf_list), len(acoes_list)]
                })

                # Aplicando um estilo mais compacto
                st.dataframe(
                    estatisticas.style.set_properties(**{
                        "border": "1px solid #444",
                        "font-size": "10px"
                    }),
                    hide_index=True,
                    use_container_width=True
                )


            # 📌 Tabelas de Unidades de Conservação
            st.markdown("#### 🌍 Unidades de Conservação e Valores")

            unidades_alocadas = unidades[unidades["VALOR TOTAL ALOCADO"] > 0].copy()
            unidades_iniciativa = unidades[unidades["Valor Total da Iniciativa"] > 0].copy()

            # 📌 Cálculo do percentual de valor alocado (evitando divisão por zero e problemas de infinidade)
            unidades_alocadas["% Valor Alocado"] = (unidades_alocadas["VALOR TOTAL ALOCADO"] / unidades_alocadas["Valor Total da Iniciativa"]) * 100
            unidades_alocadas["% Valor Alocado"] = unidades_alocadas["% Valor Alocado"].replace([np.inf, -np.inf], 0).fillna(0).round(2)

            # 📌 Criando uma barra de progresso visual diferenciada
            def gerar_barra_progresso(perc):
                total_blocos = 10  # Define a quantidade de blocos para a barra
                preenchidos = max(0, min(int((perc / 100) * total_blocos), total_blocos))  # Garante que esteja dentro do limite

                if perc > 100:
                    return "🟧" * preenchidos + "⬜" * (total_blocos - preenchidos)  # 🔥 Excesso em laranja
                return "🟩" * preenchidos + "⬜" * (total_blocos - preenchidos)  # 🔥 Normal em verde

            # 📌 Aplicando a barra de progresso na tabela
            unidades_alocadas["Progresso"] = unidades_alocadas["% Valor Alocado"].apply(gerar_barra_progresso)

            # 📌 Criando a linha de total corretamente
            linha_total = pd.DataFrame([{
                "Unidade de Conservação": "TOTAL GERAL",
                "VALOR TOTAL ALOCADO": unidades_alocadas["VALOR TOTAL ALOCADO"].sum(),
                "Valor Total da Iniciativa": unidades_alocadas["Valor Total da Iniciativa"].sum(),
                "% Valor Alocado": round((unidades_alocadas["VALOR TOTAL ALOCADO"].sum() / unidades_alocadas["Valor Total da Iniciativa"].sum()) * 100, 2)
                    if unidades_alocadas["Valor Total da Iniciativa"].sum() > 0 else 0,
                "Progresso": "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛"
            }])

            # 📌 Concatenando a linha de total sem erro
            unidades_alocadas = pd.concat([unidades_alocadas, linha_total], ignore_index=True)

            # 📌 Exibir DataFrame formatado
            with st.expander("💰 Valores Alocados", expanded=False):
                st.dataframe(
                    unidades_alocadas.rename(columns={
                        "VALOR TOTAL ALOCADO": "Valor Alocado (R$)",
                        "Valor Total da Iniciativa": "Valor da Iniciativa (R$)"
                    }),
                    hide_index=True,
                    use_container_width=True
                )

            # 📌 Ajuste para "Valores da Iniciativa" (evitando erros de divisão)
            unidades_iniciativa["% Valor Alocado"] = (unidades_iniciativa["VALOR TOTAL ALOCADO"] / unidades_iniciativa["Valor Total da Iniciativa"]) * 100
            unidades_iniciativa["% Valor Alocado"] = unidades_iniciativa["% Valor Alocado"].replace([np.inf, -np.inf], 0).fillna(0).round(2)
            unidades_iniciativa["Progresso"] = unidades_iniciativa["% Valor Alocado"].apply(gerar_barra_progresso)

            # 📌 Criando a linha de total corretamente para "Valores da Iniciativa"
            linha_total_iniciativa = pd.DataFrame([{
                "Unidade de Conservação": "TOTAL GERAL",
                "VALOR TOTAL ALOCADO": unidades_iniciativa["VALOR TOTAL ALOCADO"].sum(),
                "Valor Total da Iniciativa": unidades_iniciativa["Valor Total da Iniciativa"].sum(),
                "% Valor Alocado": round((unidades_iniciativa["VALOR TOTAL ALOCADO"].sum() / unidades_iniciativa["Valor Total da Iniciativa"].sum()) * 100, 2)
                    if unidades_iniciativa["Valor Total da Iniciativa"].sum() > 0 else 0,
                "Progresso": "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛"
            }])

            # 📌 Concatenando a linha de total corretamente
            unidades_iniciativa = pd.concat([unidades_iniciativa, linha_total_iniciativa], ignore_index=True)

            # with st.expander("💰 Valores da Iniciativa", expanded=False):
            #     st.dataframe(
            #         unidades_iniciativa.rename(columns={
            #             "VALOR TOTAL ALOCADO": "Valor Alocado (R$)",
            #             "Valor Total da Iniciativa": "Valor da Iniciativa (R$)"
            #         }),
            #         hide_index=True,
            #         use_container_width=True
            #     )





        # 📌 CSS para as tags minimalistas
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