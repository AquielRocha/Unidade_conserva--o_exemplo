###############################################################################
#                          IMPORTS E CONFIGURAÇÕES
###############################################################################

import streamlit as st
import sqlite3
import json
import pandas as pd
import time as time

import streamlit as st
import sqlite3
import json
import pandas as pd
import time as time

# -----------------------------------------------------------------------------
#                     Verificação de Login e Configurações de Página
# -----------------------------------------------------------------------------
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login.")
    st.stop()

st.set_page_config(
    page_title="Cadastro de Regras de Negócio",
    page_icon=":infinity:",
    layout="wide"
)

# CSS Customizado para modais
st.markdown("""
    <style>
        div[data-modal-container='true'] {
            z-index: 1002 !important;
        }
        .stDataEditor div[data-testid="stVerticalBlock"] {
            gap: 0.2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Caminho do banco de dados
DB_PATH = "database/app_data.db"


# -----------------------------------------------------------------------------
#                          FUNÇÕES AUXILIARES / CACHED
# -----------------------------------------------------------------------------
@st.cache_data
def get_iniciativas_usuario(perfil: str, setor: str) -> pd.DataFrame:
    """
    Retorna as iniciativas disponíveis para o usuário,
    filtradas por perfil e setor, se não for 'admin'.
    """
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id_iniciativa, nome_iniciativa FROM td_iniciativas"
    if perfil != "admin":
        query += """
            WHERE id_iniciativa IN (
               SELECT id_iniciativa 
               FROM tf_cadastros_iniciativas 
               WHERE id_demandante = (
                  SELECT id_demandante FROM td_demandantes WHERE nome_demandante = ?
               )
            )
        """
        iniciativas = pd.read_sql_query(query, conn, params=[setor])
    else:
        iniciativas = pd.read_sql_query(query, conn)
    conn.close()
    return iniciativas


@st.cache_data
def carregar_dados_iniciativa(id_iniciativa: int) -> dict | None:
    """
    Carrega a última linha de tf_cadastro_regras_negocio para a iniciativa dada.
    Retorna um dicionário com as colunas esperadas ou None se não existir.
    """
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT *
        FROM tf_cadastro_regras_negocio
        WHERE id_iniciativa = ?
        ORDER BY data_hora DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn, params=[id_iniciativa])
    conn.close()

    if df.empty:
        return None

    row = df.iloc[0]

    # Eixos temáticos salvos em JSON
    try:
        eixos_tematicos = json.loads(
            row["eixos_tematicos"]) if row["eixos_tematicos"] else []
    except:
        eixos_tematicos = []

    # Demais informações salvas em JSON
    info_json = row.get("demais_informacoes", "") or ""
    try:
        info_dict = json.loads(info_json) if info_json else {}
    except:
        info_dict = {}

    return {
        "objetivo_geral":      row["objetivo_geral"],
        "objetivos_especificso": row["objetivos_especificos"],
        "eixos_tematicos":     row["eixos_tematicos"],
        "introducao":          row.get("introducao", ""),
        "justificativa":       row.get("justificativa", ""),
        "metodologia":         row.get("metodologia", ""),
        "demais_informacoes":  info_dict
    }


@st.cache_data
def carregar_resumo_iniciativa(setor: str) -> pd.DataFrame | None:
    """
    Carrega o resumo a partir de td_dados_resumos_sei, filtrando por 'demandante' = setor.
    Retorna um DataFrame ou None se vazio.
    """
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM td_dados_resumos_sei WHERE demandante = ?"
    df = pd.read_sql_query(query, conn, params=[setor])
    conn.close()
    if df.empty:
        return None
    return df


def salvar_dados_iniciativa(
    id_iniciativa: int,
    usuario: str,
    objetivo_geral: str,
    objetivos_especificos: list[str],
    eixos_tematicos: list[dict],
    introducao: str,
    justificativa: str,
    metodologia: str,
    demais_informacoes: dict
):
    """
    Salva registro na tf_cadastro_regras_negocio, mantendo histórico máximo de 3 registros.

    - objetivos_especificos: lista de strings
    - eixos_tematicos: lista de dicts
    - demais_informacoes: dict de informações complementares

    Também atualiza as colunas "acoes_manejo" e "insumos" com base nos eixos.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Limite de 3 históricos por iniciativa
    cursor.execute("""
        SELECT COUNT(*)
        FROM tf_cadastro_regras_negocio
        WHERE id_iniciativa = ?
    """, (id_iniciativa,))
    total_reg = cursor.fetchone()[0]
    if total_reg >= 3:
        cursor.execute("""
            DELETE FROM tf_cadastro_regras_negocio
            WHERE id IN (
                SELECT id
                FROM tf_cadastro_regras_negocio
                WHERE id_iniciativa = ?
                ORDER BY data_hora ASC
                LIMIT 1
            )
        """, (id_iniciativa,))

    # Converte listas/dicts para JSON
    objetivos_json = json.dumps(objetivos_especificos or [])
    eixos_tematicos_corrigidos = [
        {
            "id_eixo": int(e["id_eixo"]) if str(e["id_eixo"]).isdigit() else 0,  # Garantir que seja número
            "nome_eixo": e["nome_eixo"],
            "acoes_manejo": e["acoes_manejo"]
        }
        for e in st.session_state["eixos_tematicos"]
    ]

    eixos_json = json.dumps(eixos_tematicos_corrigidos)

    # Extrai lista de ações e insumos a partir de eixos
    acoes_set = set()
    insumos_set = set()
    for eixo in eixos_tematicos:
        for ac_id, ac_data in eixo.get("acoes_manejo", {}).items():
            acoes_set.add(ac_id)
            for ins_id in ac_data.get("insumos", []):
                insumos_set.add(ins_id)

    acoes_json = json.dumps(list(acoes_set))
    insumos_json = json.dumps(list(insumos_set))

    # Regra consolidada
    final_rule = {
        "objetivo_geral": objetivo_geral,
        "objetivos_especificos": objetivos_especificos,
        "eixos_tematicos": eixos_tematicos,
        "acoes": list(acoes_set),
        "insumos": list(insumos_set)
    }
    regra_json = json.dumps(final_rule)

    # Converte o dicionário 'demais_informacoes' em JSON
    demais_info_json = json.dumps(
        demais_informacoes) if demais_informacoes else "{}"

    # 1) Distribuição UC (df_uc_editado)
    if "df_uc_editado" in st.session_state and not st.session_state["df_uc_editado"].empty:
        distribuicao_ucs_json = st.session_state["df_uc_editado"].to_json(
            orient="records", force_ascii=False)
    else:
        distribuicao_ucs_json = "[]"

    # 2) Formas de Contratação (formas_contratacao_detalhes)
    if "formas_contratacao_detalhes" in st.session_state:
        formas_contratacao_json = json.dumps(
            st.session_state["formas_contratacao_detalhes"], ensure_ascii=False)
    else:
        formas_contratacao_json = "{}"

    # Insere no banco
    cursor.execute("""
        INSERT INTO tf_cadastro_regras_negocio (
            id_iniciativa,
            usuario,
            objetivo_geral,
            objetivos_especificos,
            eixos_tematicos,
            acoes_manejo,
            insumos,
            regra,
            introducao,
            justificativa,
            metodologia,
            demais_informacoes,
            distribuicao_ucs,
            formas_contratacao
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_iniciativa,
        usuario,
        objetivo_geral,
        objetivos_json,
        eixos_json,
        acoes_json,
        insumos_json,
        regra_json,
        introducao,
        justificativa,
        metodologia,
        demais_info_json,
        distribuicao_ucs_json,
        formas_contratacao_json   # Alterado aqui
    ))

    conn.commit()
    conn.close()


@st.cache_data
def get_options_from_table(
    table_name: str,
    id_col: str,
    name_col: str,
    filter_col: str | None = None,
    filter_val: str | None = None
) -> dict[str, str]:
    """
    Lê da tabela `table_name` as colunas `id_col` e `name_col`.
    Opcionalmente filtra por `filter_col = filter_val`.
    Retorna um dict { id_val: name_val }.
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT {id_col}, {name_col} FROM {table_name}"
    params = ()
    if filter_col and filter_val is not None:
        query += f" WHERE {filter_col} = ?"
        params = (str(filter_val),)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return {str(row[id_col]): row[name_col] for _, row in df.iterrows()}


# -----------------------------------------------------------------------------
#            Inicialização para evitar KeyError no session_state
# -----------------------------------------------------------------------------

for key in ["introducao", "justificativa", "metodologia", "objetivo_geral"]:
    if key not in st.session_state:
        st.session_state[key] = ""

if "demais_informacoes" not in st.session_state:
    st.session_state["demais_informacoes"] = {}

if "objetivos_especificos" not in st.session_state:
    st.session_state["objetivos_especificos"] = []

if "eixos_tematicos" not in st.session_state:
    st.session_state["eixos_tematicos"] = []

if "df_uc_editado" not in st.session_state:
    st.session_state["df_uc_editado"] = pd.DataFrame()

if "insumos" not in st.session_state:
    st.session_state["insumos"] = {}


# # -----------------------------------------------------------------------------
# #          Função para exibir informações complementares na barra lateral
# # -----------------------------------------------------------------------------
def exibir_info_lateral(id_iniciativa: int):
    # -----------------------------------------------------------------------------
    #          Exibir apenas informações do usuário logado na barra lateral
    # -----------------------------------------------------------------------------
    st.sidebar.write("### 🔑 Usuário Logado")

    # Recupera as informações do usuário logado do session_state
    cpf_usuario = st.session_state.get("cpf", "(não informado)")
    nome_usuario = st.session_state.get("nome", "(não informado)")
    email_usuario = st.session_state.get("email", "(não informado)")
    setor_usuario = st.session_state.get("setor", "(não informado)")
    perfil_usuario = st.session_state.get("perfil", "comum")

    # Exibe as informações na barra lateral
    st.sidebar.write(f"**👤 Nome:** {nome_usuario}")
    st.sidebar.write(f"**📧 E-mail:** {email_usuario}")
    st.sidebar.write(f"**📌 Diretoria:** {setor_usuario}")
    st.sidebar.write(f"**🔰 Perfil:** {perfil_usuario}")


# -----------------------------------------------------------------------------
#                           Início da Página
# -----------------------------------------------------------------------------
st.subheader("📝 Cadastro de Regras de Negócio")

perfil = st.session_state["perfil"]
setor = st.session_state["setor"]
cpf_usuario = st.session_state["cpf"]

# 1) Seleciona Iniciativa do usuário
iniciativas = get_iniciativas_usuario(perfil, setor)
if iniciativas.empty:
    st.warning("🚫 Nenhuma iniciativa disponível para você.")
    st.stop()

with st.expander("Selecione a Iniciativa para Cadastro"):
    nova_iniciativa = st.selectbox("",

        options=iniciativas["id_iniciativa"],
        format_func=lambda x: iniciativas.set_index(
            "id_iniciativa").loc[x, "nome_iniciativa"],
        key="sel_iniciativa"
    )

# st.caption("ℹ️ Informações Originais do Resumo Executivo de Iniciativas disponíveis no final da página", help="ref.: documentos SEI")

# 2) Carregamento inicial da iniciativa se mudou
if "carregou_iniciativa" not in st.session_state or st.session_state["carregou_iniciativa"] != nova_iniciativa:
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # 1️⃣ BUSCA DADOS NA TABELA PRINCIPAL PRIMEIRO (tf_cadastro_regras_negocio)
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT objetivo_geral, objetivos_especificos, eixos_tematicos,
               introducao, justificativa, metodologia, demais_informacoes
        FROM tf_cadastro_regras_negocio
        WHERE id_iniciativa = ?
        ORDER BY data_hora DESC
        LIMIT 1
    """
    dados_iniciativa = pd.read_sql_query(query, conn, params=[nova_iniciativa])
    conn.close()

    if not dados_iniciativa.empty:
        row = dados_iniciativa.iloc[0]

        # Objetivos Específicos: Sempre carrega do banco primeiro
        try:
            objetivos_especificos = json.loads(
                row["objetivos_especificos"]) if row["objetivos_especificos"] else []
        except:
            objetivos_especificos = []

        st.session_state["objetivo_geral"] = row["objetivo_geral"]
        st.session_state["objetivos_especificos"] = objetivos_especificos

        # Eixos Temáticos
        try:
            st.session_state["eixos_tematicos"] = json.loads(
                row["eixos_tematicos"]) if row["eixos_tematicos"] else []
        except:
            st.session_state["eixos_tematicos"] = []

        # Textos
        st.session_state["introducao"] = row["introducao"]
        st.session_state["justificativa"] = row["justificativa"]
        st.session_state["metodologia"] = row["metodologia"]

        # Demais informações
        try:
            st.session_state["demais_informacoes"] = json.loads(
                row["demais_informacoes"]) if row["demais_informacoes"] else {}
        except:
            st.session_state["demais_informacoes"] = {}

    else:
        # Se não houver dados em `tf_cadastro_regras_negocio`, inicia com valores vazios
        st.session_state["objetivo_geral"] = ""
        st.session_state["objetivos_especificos"] = []
        st.session_state["eixos_tematicos"] = []
        st.session_state["introducao"] = ""
        st.session_state["justificativa"] = ""
        st.session_state["metodologia"] = ""
        st.session_state["demais_informacoes"] = {}

        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # 2️⃣ FALLBACK: BUSCA DADOS NO RESUMO (td_dados_resumos_sei) APENAS SE O PRINCIPAL ESTIVER VAZIO
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        if not st.session_state["objetivo_geral"]:
            conn = sqlite3.connect(DB_PATH)
            row_fallback = conn.execute("""
                SELECT objetivo_geral FROM td_dados_resumos_sei
                WHERE id_resumo = ? LIMIT 1
            """, (nova_iniciativa,)).fetchone()
            conn.close()

            if row_fallback:
                obj_geral_sei = row_fallback[0] or ""
                if obj_geral_sei:
                    st.session_state["objetivo_geral"] = obj_geral_sei

        if not st.session_state["introducao"] or not st.session_state["justificativa"] or not st.session_state["metodologia"]:
            conn = sqlite3.connect(DB_PATH)
            row_resumo_2 = conn.execute("""
                SELECT introdução, justificativa, metodologia
                FROM td_dados_resumos_sei
                WHERE id_resumo = ?
                LIMIT 1
            """, (nova_iniciativa,)).fetchone()
            conn.close()

            if row_resumo_2:
                intro_sei, justif_sei, metod_sei = row_resumo_2

                if not st.session_state["introducao"] and intro_sei:
                    st.session_state["introducao"] = intro_sei
                if not st.session_state["justificativa"] and justif_sei:
                    st.session_state["justificativa"] = justif_sei
                if not st.session_state["metodologia"] and metod_sei:
                    st.session_state["metodologia"] = metod_sei

    # 3️⃣ Finaliza o carregamento
    st.session_state["df_uc_editado_loaded"] = False
    st.session_state["carregou_iniciativa"] = nova_iniciativa


# Exibe na barra lateral (checkbox)
if st.sidebar.checkbox("Exibir informações do usuário", value=False):
    exibir_info_lateral(nova_iniciativa)

st.divider()

st.write(
    f"**Iniciativa Selecionada:** {iniciativas.set_index('id_iniciativa').loc[nova_iniciativa, 'nome_iniciativa']}")

st.divider()


# ---------------------------------------------------------
#  TABS: Introdução / Objetivos / Justificativa / Metodologia
#        e a aba para Demais Informações
# ---------------------------------------------------------
tab_intro, tab_obj, tab_justif, tab_metod, tab_demandante, tab_eixos, tab_insumos, tab_uc, tab_forma_contratacao = st.tabs([
    "Introdução",
    "Objetivos",
    "Justificativa",
    "Metodologia",
    "Demandante",
    "Eixos Temáticos",
    "Insumos",
    "Unidades de Conservação",
    "Formas de Contratação"
])


with st.form("form_textos_resumo"):

    # ---------------------------------------------------------
    # 1) OBJETIVOS
    # (aba separada, pois tem seu próprio form para atualizar
    #  objetivos específicos)
    # ---------------------------------------------------------
    with tab_obj:

        st.subheader("Objetivo Geral")
        st.session_state["objetivo_geral"] = st.text_area(
            "Descreva o Objetivo Geral:",
            value=st.session_state["objetivo_geral"],
            height=140
        )

        st.subheader("Objetivos Específicos")

        # Se não existir, inicializa a lista de objetivos em session_state
        if "objetivos_especificos" not in st.session_state:
            st.session_state["objetivos_especificos"] = []

        # 1) Campo e botão para adicionar NOVO objetivo (acima da lista)
        def adicionar_objetivo_callback():
            texto_novo = st.session_state.txt_novo_objetivo.strip()
            if texto_novo:
                st.session_state["objetivos_especificos"].append(texto_novo)
                st.session_state.txt_novo_objetivo = ""  # limpa a caixa após adicionar
            else:
                st.warning(
                    "O texto do objetivo está vazio. Por favor, digite algo antes de adicionar.")

        st.text_area(
            label="Digite o texto do objetivo específico a ser adicionado e clique no botão:",
            key="txt_novo_objetivo",
            height=80
        )

        st.button(
            label="Adicionar Objetivo",
            on_click=adicionar_objetivo_callback
        )

        st.write("---")

        # 2) Agora exibimos a lista (simulando uma tabela) com Editar/Remover
        st.write("*Objetivos adicionados:*")

        # Cabeçalho tipo tabela
        col1, col2, col3 = st.columns([1, 8, 3])
        col1.write("**#**")
        col2.write("**Objetivo**")
        col3.write("*Edição e Exclusão*")

        # Loop para cada objetivo adicionado
        for i, objetivo in enumerate(st.session_state["objetivos_especificos"]):
            # Criamos uma nova linha em colunas
            c1, c2, c3 = st.columns([1, 6, 3])
            c1.write(f"{i + 1}")
            c2.write(objetivo)  # exibe o texto do objetivo

            # Na terceira coluna, colocamos botões: Editar (via popover) e Remover
            with c3:
                col_edit, col_remove = st.columns([1, 1])
                with col_edit:
                    # 2.1) Botão/Popover de Edição
                    with st.popover(label=f"✏️"):
                        st.subheader(f"Editar Objetivo {i+1}")
                        novo_texto = st.text_area(
                            "Texto do objetivo:", objetivo, key=f"edit_obj_{i}")
                        if st.button("Salvar Edição", key=f"btn_save_edit_{i}"):
                            st.session_state["objetivos_especificos"][i] = novo_texto
                            st.rerun()
                with col_remove:
                    # 2.2) Botão de Remoção
                    if st.button("🗑️", key=f"btn_remove_{i}"):
                        del st.session_state["objetivos_especificos"][i]
                        st.rerun()

    # ---------------------------------------------------------
    # 2) INTRODUÇÃO, JUSTIFICATIVA, METODOLOGIA e
    #    DEMAIS INFORMAÇÕES
    # ---------------------------------------------------------
    # Aba de Introdução
    with tab_intro:
        st.subheader("Introdução")
        st.session_state["introducao"] = st.text_area(
            "Texto de Introdução:",
            value=st.session_state["introducao"],
            height=300
        )





    # Aba de Justificativa
    with tab_justif:
        st.subheader("Justificativa")
        st.session_state["justificativa"] = st.text_area(
            "Texto de Justificativa:",
            value=st.session_state["justificativa"],
            height=300
        )




    # Aba de Metodologia
    with tab_metod:
        st.subheader("Metodologia")
        st.session_state["metodologia"] = st.text_area(
            "Texto de Metodologia:",
            value=st.session_state["metodologia"],
            height=300
        )



    # Aba de Demais Informações
    # Aba de Demandante (somente Diretoria e Usuário Responsável)
    with tab_demandante:
        st.subheader("Informações do Usuário Responsável")

        # Recupera as informações do usuário logado do session_state
        nome_usuario = st.session_state.get("nome", "(não informado)")
        email_usuario = st.session_state.get("email", "(não informado)")
        setor_usuario = st.session_state.get("setor", "(não informado)")
        perfil_usuario = st.session_state.get("perfil", "comum")

        # Exibe apenas informações do usuário responsável pelo preenchimento
        st.write(f"**👤 Nome do Preenchedor:** {nome_usuario}")
        st.write(f"**📧 E-mail:** {email_usuario}")
        st.write(f"**📌 Diretoria:** {setor_usuario}")
        # st.write(f"**🔰 Perfil:** {perfil_usuario}")

        st.divider()
        st.info(
            "Estas informações são registradas automaticamente e não podem ser alteradas.")

        # Salvar informações do usuário logado na sessão
        st.session_state["demais_informacoes"] = {
            "diretoria": st.session_state.get("setor", "Não informado"),
            "usuario_nome": st.session_state.get("nome", "Não informado"),
            "usuario_email": st.session_state.get("email", "Não informado"),
            "perfil": st.session_state.get("perfil", "Não informado"),
        }




















    # -------------------------------------------
    # 4) EIXOS TEMÁTICOS - Seleção de Ações
    # -------------------------------------------
    with tab_eixos:
        
        st.subheader("Eixos Temáticos")

        # 1️⃣ Carregar eixos já cadastrados no banco ao abrir a aba
        if "carregou_eixos" not in st.session_state or st.session_state["carregou_eixos"] != nova_iniciativa:
            conn = sqlite3.connect(DB_PATH)
            query = """
                SELECT eixos_tematicos 
                FROM tf_cadastro_regras_negocio 
                WHERE id_iniciativa = ? 
                ORDER BY data_hora DESC 
                LIMIT 1
            """
            row = conn.execute(query, (nova_iniciativa,)).fetchone()
            conn.close()

            if row and row[0]:  # Se houver eixos cadastrados no banco
                try:
                    st.session_state["eixos_tematicos"] = json.loads(row[0])
                except json.JSONDecodeError:
                    st.session_state["eixos_tematicos"] = []
            else:
                st.session_state["eixos_tematicos"] = []  # Se não houver dados, inicializa lista vazia

            st.session_state["carregou_eixos"] = nova_iniciativa  # Flag para evitar recarregar

        # 2️⃣ Selecionar um novo eixo
        eixos_opcoes = get_options_from_table("td_samge_processos", "id_p", "nome")

        novo_eixo_id = st.selectbox(
            "Escolha um Eixo (Processo SAMGe) para adicionar:",
            options=[None] + sorted(eixos_opcoes.keys(), key=lambda x: eixos_opcoes[x]),
            format_func=lambda x: eixos_opcoes.get(str(x), "Selecione..."),
            key="sel_novo_eixo"
        )

        # 3️⃣ Botão para adicionar novo eixo
        if st.button("➕ Adicionar Eixo Temático", key="btn_add_eixo"):
            if novo_eixo_id is None:
                st.warning("Selecione um eixo válido antes de adicionar.")
            else:
                try:
                    eixo_id_int = int(novo_eixo_id)  # Garante que seja um número
                    ids_existentes = [int(e["id_eixo"]) for e in st.session_state["eixos_tematicos"] if str(e["id_eixo"]).isdigit()]

                    if eixo_id_int not in ids_existentes:
                        novo_eixo = {
                            "id_eixo": eixo_id_int,  
                            "nome_eixo": eixos_opcoes.get(str(novo_eixo_id), "Novo Eixo"),
                            "acoes_manejo": {}  # Inicializa sem ações
                        }
                        st.session_state["eixos_tematicos"].append(novo_eixo)

                        # ✅ Força atualização dos insumos ao adicionar novo eixo
                        st.session_state["insumos"] = {}  

                        st.rerun()
                    else:
                        st.info("Este eixo já está na lista.")
                except ValueError:
                    st.error("Erro ao adicionar o eixo. Verifique se os IDs são numéricos.")

        # 4️⃣ Exibir expanders para cada eixo carregado do banco
        for i, eixo in enumerate(st.session_state["eixos_tematicos"]):
            with st.expander(f"📌 {eixo['nome_eixo']}", expanded=False):
                eixo_id_str = str(eixo["id_eixo"])  # Converte ID para string

                # Buscar ações de manejo associadas ao eixo no banco de dados
                acoes_dict = get_options_from_table(
                    "td_samge_acoes_manejo", "id_ac", "nome",
                    filter_col="processo_id", filter_val=eixo_id_str
                )

                # Se não há ações cadastradas, inicializa o dicionário
                if "acoes_manejo" not in eixo:
                    eixo["acoes_manejo"] = {}

                # Criar DataFrame para edição de ações
                acoes_df = pd.DataFrame([
                    {"ID": ac_id, "Ação": nome, "Selecionado": ac_id in eixo["acoes_manejo"]}
                    for ac_id, nome in acoes_dict.items()
                ])
                if "Selecionado" not in acoes_df.columns:
                    acoes_df["Selecionado"] = False

                with st.form(f"form_acoes_{i}"):
                    edited_acoes = st.data_editor(
                        acoes_df,
                        column_config={
                            "ID": st.column_config.TextColumn(disabled=True),
                            "Ação": st.column_config.TextColumn(disabled=True),
                            "Selecionado": st.column_config.CheckboxColumn("Selecionar")
                        },
                        hide_index=True,
                        use_container_width=True,
                        key=f"editor_acoes_{i}"
                    )

                    if st.form_submit_button("Salvar Ações"):
                        # Atualiza as ações selecionadas no eixo
                        selecionadas = edited_acoes.loc[edited_acoes["Selecionado"], "ID"].tolist()
                        eixo["acoes_manejo"] = {ac_id: {"insumos": []} for ac_id in selecionadas}
                        st.session_state["eixos_tematicos"][i] = eixo
                        st.success("Ações atualizadas!")

                # Botão para excluir eixo
                if st.button("🗑️ Excluir Eixo", key=f"btn_del_{i}"):
                    del st.session_state["eixos_tematicos"][i]
                    st.rerun()


















    # -------------------------------------------
    # 5) INSUMOS - Seleção de Insumos por Ação
    # -------------------------------------------
    with tab_insumos:
        st.subheader("Insumos por Ação")

        # Conectar ao banco para carregar a tabela de insumos
        conn = sqlite3.connect(DB_PATH)
        df_insumos_all = pd.read_sql_query(
            "SELECT id, elemento_despesa, especificacao_padrao, descricao_insumo FROM td_insumos",
            conn
        )
        conn.close()

        # Inicializar estado para armazenar insumos selecionados, se ainda não existir
        if "insumos_selecionados" not in st.session_state:
            st.session_state["insumos_selecionados"] = {}

        for i, eixo in enumerate(st.session_state["eixos_tematicos"]):
            with st.expander(f"📌 {eixo['nome_eixo']}", expanded=False):
                # Percorremos as ações daquele eixo
                for ac_id, ac_data in eixo["acoes_manejo"].items():
                    st.markdown(
                        f"### Ação: {get_options_from_table('td_samge_acoes_manejo', 'id_ac', 'nome').get(ac_id, 'Ação Desconhecida')}"
                    )

                    # Inicializa a lista de insumos selecionados para essa ação, se ainda não existir
                    if ac_id not in st.session_state["insumos_selecionados"]:
                        st.session_state["insumos_selecionados"][ac_id] = set(
                            ac_data.get("insumos", []))

                    # Criar colunas para os filtros
                    col_filtro_elemento, col_filtro_espec = st.columns([5, 5])

                    # Filtro de Elemento de Despesa
                    elementos_unicos = [
                        "Todos"] + sorted(df_insumos_all["elemento_despesa"].dropna().unique())
                    with col_filtro_elemento:
                        elemento_selecionado = st.selectbox(
                            "Selecione o Elemento de Despesa",
                            elementos_unicos,
                            key=f"elemento_{i}_{ac_id}"
                        )

                    # Filtrando os insumos conforme o elemento de despesa selecionado
                    df_filtrado = (
                        df_insumos_all
                        if elemento_selecionado == "Todos"
                        else df_insumos_all[df_insumos_all["elemento_despesa"] == elemento_selecionado]
                    )

                    # Filtro de Especificação Padrão
                    especificacoes_unicas = [
                        "Todos"] + sorted(df_filtrado["especificacao_padrao"].dropna().unique())
                    with col_filtro_espec:
                        especificacao_selecionada = st.selectbox(
                            "Selecione a Especificação Padrão",
                            especificacoes_unicas,
                            key=f"especificacao_{i}_{ac_id}"
                        )

                    # Aplicando o segundo filtro caso o usuário selecione uma especificação
                    if especificacao_selecionada != "Todos":
                        df_filtrado = df_filtrado[df_filtrado["especificacao_padrao"]
                                                  == especificacao_selecionada]

                    # Renomeando colunas para melhor compatibilidade com data_editor
                    df_combo = df_filtrado.rename(
                        columns={
                            "id": "ID",
                            "especificacao_padrao": "Especificação Padrão",
                            "descricao_insumo": "Insumo"
                        }
                    )

                    # Recupera o "master" de insumos já selecionados do estado para essa ação
                    sel_ids = st.session_state["insumos_selecionados"][ac_id]

                    # Marcamos a coluna "Selecionado" com True/False se estiver no "master"
                    df_combo["Selecionado"] = df_combo["ID"].apply(
                        lambda x: x in sel_ids)

                    # Exibir Data Editor dentro de um formulário
                    with st.form(f"form_insumos_{i}_{ac_id}"):
                        edited_ins = st.data_editor(
                            df_combo[["ID","Especificação Padrão", "Insumo", "Selecionado"]],
                            column_config={
                                "ID": st.column_config.TextColumn("Cód. Insumo", disabled=True),
                                "Insumo": st.column_config.TextColumn("Descrição do Insumo", disabled=True),
                                "Selecionado": st.column_config.CheckboxColumn("Selecionar")
                            },
                            hide_index=True,
                            use_container_width=True,
                            key=f"editor_ins_{i}_{ac_id}"
                        )



                        col1, col2 = st.columns([1, 1])
                        with col1:
                            # Botão para salvar as seleções sem perder insumos anteriores
                            # O clique desse botão só controla o subset atual (df_filtrado)
                            if st.form_submit_button("Salvar Insumos"):
                                # "edited_ins" contém apenas o subset filtrado
                                # Precisamos mesclar com o "master" (sel_ids)

                                # 1) Obtemos o conjunto marcado agora:
                                selecionados_agora = set(
                                    edited_ins.loc[edited_ins["Selecionado"], "ID"])

                                # 2) Vamos atualizar o master:
                                #    - adiciona os que foram marcados
                                #    - remove os que foram desmarcados e que estão presentes no df_filtrado
                                # (itens fora do df_filtrado ficam inalterados)
                                for item_id in df_combo["ID"]:
                                    if item_id in selecionados_agora:
                                        # marcado => adiciona ao master
                                        sel_ids.add(item_id)
                                    else:
                                        # se está no master e está no subset filtrado, remove
                                        if item_id in sel_ids:
                                            sel_ids.remove(item_id)

                                # salva de volta no session_state
                                st.session_state["insumos_selecionados"][ac_id] = sel_ids
                                # atualiza o dicionário da ação
                                ac_data["insumos"] = list(sel_ids)

                                st.success(
                                    "Seleção atualizada!")

                        with col2:
                            # informar a importancia de salvar antes de utilizar outro filtro
                            st.warning("Salve as seleções antes de utilizar outro filtro.", icon="⚠️")

                    # # Botão para limpar todas as seleções de insumos dessa ação
                    # if st.button("Limpar Lista de Insumos", key=f"limpar_{i}_{ac_id}"):
                    #     st.session_state["insumos_selecionados"][ac_id] = set()
                    #     ac_data["insumos"] = []
                    #     st.success("Todos os insumos foram removidos para esta ação!")

                    st.write("---")











   























    # ---------------------------------------------------------
    # ABA UC - DISTRIBUIÇÃO DE RECURSOS
    # ---------------------------------------------------------
   

  

    # Conjunto das colunas consideradas "padrão" (não são eixos)
    COL_PADRAO = {
        "id",
        "DEMANDANTE (diretoria)",
        "Nome da Proposta/Iniciativa Estruturante",
        "AÇÃO DE APLICAÇÃO",
        "CNUC",
        "id_demandante",
        "id_iniciativa",
        "id_acao",
        "Unidade de Conservação",
        "TetoSaldo disponível",
        "TetoPrevisto 2025",
        "TetoPrevisto 2026",
        "TetoPrevisto 2027",
        "TetoTotalDisponivel",
        "A Distribuir"
    }
# -----------------------------------------------------------------------------
    def load_data_from_db():
        """Carrega e filtra as linhas da tabela para a iniciativa."""
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)
        conn.close()
        df = df[df["id_iniciativa"] == nova_iniciativa].copy()
        return df
# -----------------------------------------------------------------------------
    def salvar_no_banco(df_edit, col_eixos):
        """Grava no banco as colunas de eixos + 'A Distribuir'."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for idx, row in df_edit.iterrows():
            registro_id = row["id"]
            # Atualiza cada eixo
            for c_eixo in col_eixos:
                val = float(row.get(c_eixo, 0.0))
                cursor.execute(f"""
                    UPDATE tf_distribuicao_elegiveis
                    SET "{c_eixo}" = ?
                    WHERE id = ?
                """, (val, registro_id))
            # Atualiza saldo
            saldo_val = float(row.get("A Distribuir", 0.0))
            cursor.execute("""
                UPDATE tf_distribuicao_elegiveis
                SET "A Distribuir" = ?
                WHERE id = ?
            """, (saldo_val, registro_id))

         

        conn.commit()
        conn.close()
# -----------------------------------------------------------------------------
    def recalcular_saldo(df: pd.DataFrame):
        """Recalcula 'A Distribuir' = TetoTotalDisponivel - soma(eixos). Retorna DataFrame atualizado."""
        if df.empty:
            return df

        col_eixos_db = [c for c in df.columns if c not in COL_PADRAO]

        if "TetoTotalDisponivel" in df.columns:
            df["TetoTotalDisponivel"] = pd.to_numeric(df["TetoTotalDisponivel"], errors="coerce").fillna(0)

        for c_eixo in col_eixos_db:
            df[c_eixo] = pd.to_numeric(df[c_eixo], errors="coerce").fillna(0)

        if "A Distribuir" not in df.columns:
            df["A Distribuir"] = 0.0
        else:
            df["A Distribuir"] = pd.to_numeric(df["A Distribuir"], errors="coerce").fillna(0)

        for idx, row in df.iterrows():
            soma_eixos = sum(row[c_eixo] for c_eixo in col_eixos_db)
            df.at[idx, "A Distribuir"] = row["TetoTotalDisponivel"] - soma_eixos

        return df
    

# -----------------------------------------------------------------------------

    def upsert_eixos_cadastro_regras(id_iniciativa: int, eixos_list: list[str]):
        """
        Atualiza (ou insere) na tabela 'tf_cadastro_regras_negocio'
        o campo 'eixos_tematicos', garantindo que contenha ao menos
        os eixos_list passados.
        """
        import json

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1) Obtém eixos já cadastrados no banco
        cursor.execute("""
            SELECT eixos_tematicos
            FROM tf_cadastro_regras_negocio
            WHERE id_iniciativa = ?
            ORDER BY data_hora DESC
            LIMIT 1
        """, (id_iniciativa,))
        row = cursor.fetchone()

        existing_eixos = json.loads(row[0]) if row and row[0] else []

        # 2) Converte para dicionário para facilitar atualização
        eixos_dict = {str(e["id_eixo"]): e for e in existing_eixos}

        # 3) Atualiza a lista de eixos
        for novo_e in eixos_list:
            id_str = str(novo_e)  # Certifica-se que a chave seja string

            if id_str not in eixos_dict:
                eixos_dict[id_str] = {
                    "id_eixo": novo_e,
                    "nome_eixo": novo_e,
                    "acoes_manejo": {}  # Mantém a estrutura correta
                }

        # 4) Converte de volta para lista e salva no banco
        final_json = json.dumps(list(eixos_dict.values()))

        cursor.execute("""
            UPDATE tf_cadastro_regras_negocio
            SET eixos_tematicos = ?, data_hora = datetime('now'), usuario = ?
            WHERE id = ?
        """, (final_json, st.session_state["usuario_logado"], id_iniciativa))


        conn.commit()
        conn.close()





    def aba_uc_distribuicao(tab_uc):
        

        with tab_uc:


            # Flags de sessão
            if "edit_mode_uc_flag" not in st.session_state:
                st.session_state["edit_mode_uc_flag"] = False
            if "show_eixos_flag" not in st.session_state:
                st.session_state["show_eixos_flag"] = True
            if "show_tetos_flag" not in st.session_state:
                st.session_state["show_tetos_flag"] = False


            col_sup1, col_sup2 = st.columns([10, 7])

            with col_sup1:
                st.subheader("Alocação de Recursos por Eixo Temático")

                

                # 1) Toggle de edição
                edit_mode = st.toggle(
                    "---⚠️--- **Ativar Modo de Edição** ---",
                    value=st.session_state["edit_mode_uc_flag"],
                    key="modo_edicao_uc",
                    help="Clique para ativar ou desativar o modo de edição."
                )
                if edit_mode != st.session_state["edit_mode_uc_flag"]:
                    st.session_state["edit_mode_uc_flag"] = edit_mode
                    st.rerun()

            # 2) Carrega DF do banco
            df_all = load_data_from_db()
            # Remove colunas que não iremos usar
            df_all.drop(columns=[
                "DEMANDANTE (diretoria)",
                "AÇÃO DE APLICAÇÃO",
                "id_demandante",
                "id_acao",
                "Nome da Proposta/Iniciativa Estruturante"
            ], inplace=True, errors='ignore')

            if df_all.empty:
                st.warning("Nenhuma UC disponível para esta iniciativa.")
                return

            # col_warning, col_info = st.columns([10, 7])
            # with col_warning:
            #     st.info("**Atenção:** O modo de edição permite alterar a distribuição de recursos por eixo temático. \n\n **Após editar**, clique no botão **'Salvar Distribuição'** para aplicar as alterações.") 
            # with col_info:
            #     st.info("**Ação de Aplicação:** Implementação da UC.")
            
            # ---------------------------------------------------
            # MODO VISUALIZAÇÃO
            # ---------------------------------------------------
            if not st.session_state["edit_mode_uc_flag"]:

                with col_sup2:
                    
                    # Checkboxes de exibição
                    st.session_state["show_eixos_flag"] = st.toggle(
                        "Exibir Eixos Temáticos",
                        value=st.session_state["show_eixos_flag"], 
                    )

                    # st.toggle(
                    #     "Exibir Eixos Temáticos?",
                    #     value=True,
                    #     key="show_eixos_flag"
                    # )

                    st.session_state["show_tetos_flag"] = st.toggle(
                        "Exibir Tetos",
                        value=st.session_state["show_tetos_flag"]
                    )

                df_viz = df_all.copy()

                # 2.1) Filtra somente colunas de eixos que tenham soma > 0
                col_eixos_db = [c for c in df_viz.columns if c not in COL_PADRAO]
                for c_eixo in col_eixos_db:
                    if df_viz[c_eixo].fillna(0).sum() == 0:
                        df_viz.drop(columns=[c_eixo], inplace=True)

                # 2.2) Filtra somente linhas com TetoTotalDisponivel > 0
                if "TetoTotalDisponivel" in df_viz.columns:
                    df_viz = df_viz[df_viz["TetoTotalDisponivel"] > 0]
                if df_viz.empty:
                    st.warning("Nenhuma UC disponível com teto total maior que 0.")
                    return

                # 2.3) Inserir coluna "No"
                df_viz = df_viz.reset_index(drop=True)
                df_viz.insert(0, "No", range(1, len(df_viz) + 1))

                # 2.4) Reconstruir col_eixos_db após eventuais drops
                col_eixos_db = [c for c in df_viz.columns if c not in COL_PADRAO and c not in ["No"]]

                # 2.5) Monta lista exibir_cols
                exibir_cols = ["No", "Unidade de Conservação", "TetoTotalDisponivel", "A Distribuir"]
                if st.session_state["show_eixos_flag"] and col_eixos_db:
                    exibir_cols += col_eixos_db

                col_tetos = ["TetoSaldo disponível", "TetoPrevisto 2025", "TetoPrevisto 2026", "TetoPrevisto 2027"]
                if st.session_state["show_tetos_flag"]:
                    for c_teto in col_tetos:
                        if c_teto in df_viz.columns:
                            exibir_cols.append(c_teto)

                # Remove duplicadas
                exibir_cols = list(dict.fromkeys(exibir_cols))
                # Filtra só colunas existentes
                exibir_cols = [c for c in exibir_cols if c in df_viz.columns]
                df_viz = df_viz[exibir_cols]

                # 2.6) Formatação monetária
                def fmt_moeda(x):
                    try:
                        return f"<div style='text-align:right;'>R$ {float(x):,.2f}</div>"
                    except:
                        return "<div style='text-align:right;'>R$ 0,00</div>"

                for col_ in df_viz.columns:
                    if col_ not in ["No", "Unidade de Conservação", "info"]:
                        df_viz[col_] = df_viz[col_].apply(fmt_moeda)

                # 2.7) Criar coluna “info” (tooltip)
                def build_tooltip(row):
                    lines = []
                    # Eixos
                    if st.session_state["show_eixos_flag"]:
                        # Quais eixos aparecem no df_viz?
                        for c_eixo in col_eixos_db:
                            if c_eixo in row:
                                val = row[c_eixo]
                                if not isinstance(val, str):
                                    val = fmt_moeda(val)
                                v_clean = val.replace("<div style='text-align:right;'>","").replace("</div>","")
                                lines.append(f"{c_eixo}: <strong>{v_clean}</strong>")
                    # Tetos
                    if st.session_state["show_tetos_flag"]:
                        for c_teto in col_tetos:
                            if c_teto in row:
                                val = row[c_teto]
                                if not isinstance(val, str):
                                    val = fmt_moeda(val)
                                v_clean = val.replace("<div style='text-align:right;'>","").replace("</div>","")
                                lines.append(f"{c_teto}: <strong>{v_clean}</strong>")

                    if not lines:
                        lines.append("Sem dados extras")

                    tooltip_content = "<br>".join(lines)
                    icon_html = f"""
                    <span class="tooltip" style="cursor:pointer;">
                        ℹ️
                        <span class="tooltiptext">{tooltip_content}</span>
                    </span>
                    """
                    return icon_html.strip()

                df_viz["info"] = df_viz.apply(build_tooltip, axis=1)

                # 2.8) Reposiciona “info” como segunda coluna
                col_list = list(df_viz.columns)
                # Remove “info”, remove “No” e reinsera
                if "info" in col_list:
                    col_list.remove("info")
                if "No" in col_list:
                    col_list.remove("No")
                col_list = ["No", "info"] + col_list
                df_viz = df_viz[col_list]

                # exclui coluna info do dataframe para não exibir na tabela
                df_viz.drop(columns=["info"], inplace=True)

                # exclui coluna No do dataframe para não exibir na tabela
                df_viz.drop(columns=["No"], inplace=True)

                # Linha de total
                # Usar df_all (sem formatação)
                df_all_num = df_all.copy()
                df_all_num.reset_index(drop=True, inplace=True)
                df_all_num.insert(0, "No", range(1, len(df_all_num)+1))
                # Converte numérico
                for c_ in df_all_num.columns:
                    if c_ not in ["No", "id", "id_iniciativa", "Unidade de Conservação"]:
                        df_all_num[c_] = pd.to_numeric(df_all_num[c_], errors="coerce").fillna(0)

                def soma_format(col_name):
                    if col_name in df_all_num.columns:
                        return fmt_moeda(df_all_num[col_name].sum())
                    return "<div style='text-align:right;'>R$ 0,00</div>"

                total_row = {}
                for c_ in df_viz.columns:
                    if c_ == "No":
                        total_row[c_] = ""
                    elif c_ == "info":
                        total_row[c_] = ""
                    elif c_ == "Unidade de Conservação":
                        total_row[c_] = "<strong>TOTAL</strong>"
                    else:
                        # Remove tags <div> se preferir
                        total_row[c_] = soma_format(c_)

                df_viz.loc[len(df_viz)] = total_row

                # 2.10) Renomear colunas
                rename_map = {
                    "Unidade de Conservação": "Unidade de Conservação",
                    "TetoSaldo disponível":   "Teto Saldo Disponível",
                    "TetoPrevisto 2025":      "Teto Previsto 2025",
                    "TetoPrevisto 2026":      "Teto Previsto 2026",
                    "TetoPrevisto 2027":      "Teto Previsto 2027",
                    "TetoTotalDisponivel":    "Teto Total",
                    "A Distribuir":           "Saldo a Distribuir"
                }
                df_viz.rename(columns=rename_map, inplace=True)

                # ====== DESTAQUE DAS COLUNAS DE EIXO COM SOMA > 0 ======
                # Precisamos descobrir quais colunas de eixos realmente estão em df_viz.
                eixos_exibidos = [c for c in col_eixos_db if c in df_viz.columns]

                # Verificamos a soma de cada eixo em df_all para saber se > 0
                # (df_viz também é formatação HTML, então melhor usar df_all)
                highlight_eixos = []
                for e_ in eixos_exibidos:
                    if df_all[e_].fillna(0).sum() > 0:
                        highlight_eixos.append(e_)

                # Convert df_viz para Styler
                df_style = df_viz.style

                # Função para destacar colunas inteiras se elas estiverem em highlight_eixos
                def highlight_columns(col, eixos):
                    # Se col.name está em eixos, pintamos
                    if col.name in eixos:
                        return [ "background-color: #ffffcc; font-weight: bold;" ]*len(col)
                    else:
                        return [ "" ]*len(col)

                # Aplica para cada coluna
                df_style = df_style.apply(highlight_columns, axis=0, eixos=highlight_eixos)

                # =========== CSS de Tooltip e Tabela ==============
                custom_css = """
                <style>
                .table-container {
                    max-height: 600px;
                    overflow-y: auto;
                    margin-bottom: 1rem;
                    border: 1px solid #ccc;
                }
                .table-container table {
                    border-collapse: collapse;
                    width: 100%;
                }
                .table-container th, .table-container td {
                    border: 1px solid #ddd;
                    padding: 8px;
                }
                .table-container th {
                    background-color: #f2f2f2;
                    position: sticky;
                    top: 0;
                    z-index: 2;
                    text-align: center;
                }
                .tooltip {
                    position: relative;
                    display: inline-block;
                }
                .tooltip .tooltiptext {
                    visibility: hidden;
                    width: 280px;
                    background-color: #fafafa;
                    color: #000;
                    text-align: left;
                    border: 1px solid #ccc;
                    padding: 5px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    position: absolute;
                    z-index: 1;
                    top: 150%;
                    left: -120%;
                }
                .tooltip:hover .tooltiptext {
                    visibility: visible;
                }
                /* centralizar o ícone de informação */
                .tooltip {
                    text-align: center;
                    display: block;
                    margin: 0 auto;
                }
                /* centralizar primeira coluna (No) */
                .table-container th:first-child, .table-container td:first-child {
                    text-align: center;
                }
                </style>
                """
                st.markdown(custom_css, unsafe_allow_html=True)

                # Renderiza a tabela via Styler
                html_table = df_style.to_html(index=False, escape=False)
                st.markdown(f"<div class='table-container'>{html_table}</div>", unsafe_allow_html=True)

               

            # ---------------------------------------------------
            # MODO EDIÇÃO
            # ---------------------------------------------------
            else:
                st.warning("Modo de Edição: Ajuste valores, clique em 'Calcular Saldo' ou 'Salvar Distribuição'.")

                df_edit = df_all.copy()
                col_eixos_db = [c for c in df_edit.columns if c not in COL_PADRAO]

                # Eixos do session_state
                eixos_cfg = st.session_state.get("eixos_tematicos", [])
                col_eixos_sess = [e["nome_eixo"] for e in eixos_cfg]

                # União
                col_eixos_all = list(set(col_eixos_db + col_eixos_sess))

                for c_eixo in col_eixos_all:
                    if c_eixo not in df_edit.columns:
                        df_edit[c_eixo] = 0.0

                col_fixas = ["id", "Unidade de Conservação", "TetoTotalDisponivel", "A Distribuir"]
                col_fixas = [c for c in col_fixas if c in df_edit.columns]

                cols_editor = col_fixas + col_eixos_all
                df_edit = df_edit[cols_editor].reset_index(drop=True)

                # st.data_editor config
                column_config = {}
                for c in cols_editor:
                    if c == "id":
                        column_config[c] = st.column_config.TextColumn(label="ID (Interno)", disabled=True)
                    elif c == "Unidade de Conservação":
                        column_config[c] = st.column_config.TextColumn(label="Unidade de Conservação", disabled=True)
                    elif c == "TetoTotalDisponivel":
                        column_config[c] = st.column_config.NumberColumn(label="Teto Total", disabled=True, format="accounting")
                    elif c == "A Distribuir":
                        column_config[c] = st.column_config.NumberColumn(label="Saldo a Distribuir", disabled=True, format="accounting")
                    else:
                        # Eixo
                        column_config[c] = st.column_config.NumberColumn(label=c, format="accounting")

                # Se o usuário selecionou eixos específicos, filtra
                if col_eixos_sess:
                    df_edit = df_edit[[c for c in df_edit.columns if c in col_eixos_sess or c in col_fixas]]
                else:
                    df_edit = df_edit[col_fixas]

                # Filtra TetoTotalDisponivel > 0
                if "TetoTotalDisponivel" in df_edit.columns:
                    df_edit = df_edit[df_edit["TetoTotalDisponivel"] > 0]
                if df_edit.empty:
                    st.warning("Nenhuma UC disponível com teto total maior que 0.")
                    return

                edited_df = st.data_editor(
                    df_edit,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True,
                    key="editor_uc"
                )

                col1, col2 = st.columns(2)

                # Botão SALVAR
                with col1:
                    if st.button("Salvar Distribuição de Recursos", type="primary", use_container_width=True):
                        # 1) Salvar no DB (tf_distribuicao_elegiveis)
                        salvar_no_banco(edited_df, col_eixos_all)

                        # 2) Recalcular local, caso queira
                        df_calc = recalcular_saldo(edited_df.copy())

                        # 3) Extrair eixos com valor > 0 (ou simplesmente col_eixos_all)
                        used_eixos = []
                        for c_eixo in col_eixos_all:
                            if c_eixo in df_calc.columns:
                                soma_val = df_calc[c_eixo].fillna(0).sum()
                                if soma_val != 0:
                                    used_eixos.append(c_eixo)


                        # 

                        # 4) Atualizar (ou inserir) em tf_cadastro_regras_negocio
                        upsert_eixos_cadastro_regras(nova_iniciativa, used_eixos)

                        # 5) Mensagens e refresh
                        st.success("Distribuição salva!")
                        st.session_state["edit_mode_uc_flag"] = False
                        time.sleep(1)

                        # spinner para dar tempo de ver a mensagem
                        with st.spinner("Recalculando saldo..."):
                            # notificar que o saldo foi recalculado
                            st.toast("Saldo recalculado com sucesso!")
                            time.sleep(1)


                        df_calc = edited_df.copy()
                        df_calc = recalcular_saldo(df_calc)
                        salvar_no_banco(df_calc, col_eixos_all)
                        st.success("Saldo recalculado e salvo no banco!")
                        time.sleep(1)


                        salvar_dados_iniciativa(
                            id_iniciativa=nova_iniciativa,
                            usuario=cpf_usuario,
                            objetivo_geral=st.session_state["objetivo_geral"],
                            objetivos_especificos=st.session_state["objetivos_especificos"],
                            eixos_tematicos=st.session_state["eixos_tematicos"],
                            introducao=st.session_state["introducao"],
                            justificativa=st.session_state["justificativa"],
                            metodologia=st.session_state["metodologia"],
                            demais_informacoes=st.session_state["demais_informacoes"]
                        )
                        st.success("✅ Cadastro atualizado com sucesso!")

                        st.rerun()

                # Botão CALCULAR SALDO
                with col2:
                    
                    if st.button("Calcular Saldo", type="secondary", use_container_width=True):
                        # 1) Recalcular saldo
                        df_calc = edited_df.copy()
                        df_calc = recalcular_saldo(df_calc)
                        salvar_no_banco(df_calc, col_eixos_all)
                        st.success("Saldo recalculado e salvo no banco!")
                        time.sleep(1)
                        st.rerun()


                



               

    # ---------------------------------------------------------

    aba_uc_distribuicao(tab_uc)
    
    # ---------------------------------------------------------






























    


    # -------------------------------------------
    # 7) FORMAS DE CONTRATAÇÃO - Múltiplas Entradas
    # -------------------------------------------
    with tab_forma_contratacao:
        st.subheader("Formas de Contratação")

        # 1️⃣ Carrega, se ainda não carregamos para esta iniciativa
        if ("formas_carregou_iniciativa" not in st.session_state
                or st.session_state["formas_carregou_iniciativa"] != nova_iniciativa):

            st.session_state["formas_carregou_iniciativa"] = nova_iniciativa

            # Consulta os dados salvos no banco
            conn = sqlite3.connect(DB_PATH)
            row_formas = conn.execute("""
                SELECT formas_contratacao
                FROM tf_cadastro_regras_negocio
                WHERE id_iniciativa = ?
                ORDER BY data_hora DESC
                LIMIT 1
            """, (nova_iniciativa,)).fetchone()
            conn.close()

            # Se houver dados no banco, carregamos
            if row_formas and row_formas[0]:
                try:
                    stored_formas = json.loads(row_formas[0])
                except:
                    stored_formas = {}
            else:
                stored_formas = {}

            # Estrutura padrão para armazenar múltiplas entradas
            st.session_state["formas_contratacao_detalhes"] = stored_formas.get("detalhes_por_forma", {})

        # 2️⃣ Data Editor para seleção de Formas de Contratação
        with st.form("form_formas_contratacao"):
            df_default = pd.DataFrame({
                "Forma de Contratação": [
                    "Contrato Caixa",
                    "Contrato ICMBio",
                    "Fundação de Apoio credenciada pelo ICMBio",
                    "Fundação de Amparo à pesquisa"
                ],
                "Selecionado": [False, False, False, False]
            })

            df_editor = st.data_editor(
                df_default if "df_formas_contratacao" not in st.session_state else st.session_state["df_formas_contratacao"],
                column_config={
                    "Forma de Contratação": st.column_config.TextColumn(disabled=True),
                    "Selecionado": st.column_config.CheckboxColumn("Selecionar")
                },
                hide_index=True,
                key="formas_editor"
            )

            st.session_state["df_formas_contratacao"] = df_editor.copy()
            selected_forms = df_editor.loc[df_editor["Selecionado"], "Forma de Contratação"].tolist()

            if st.form_submit_button("Salvar Formas Selecionadas"):
                st.success("Seleção registrada com sucesso!")

        st.divider()

        # 3️⃣ Expanders dinâmicos conforme os tipos selecionados
        for forma in selected_forms:
            with st.expander(f"📌 {forma}", expanded=False):
                key_prefix = forma.replace(" ", "_").lower()

                # Inicializa estrutura no session_state se ainda não existir
                if forma not in st.session_state["formas_contratacao_detalhes"]:
                    st.session_state["formas_contratacao_detalhes"][forma] = []

                # Lista os registros já inseridos
                registros = st.session_state["formas_contratacao_detalhes"][forma]

                # 🔹 Contrato Caixa: múltiplas observações
                if forma == "Contrato Caixa":
                    nova_observacao = st.text_area("Nova Observação:", key=f"{key_prefix}_nova_observacao")

                    if st.button("➕ Adicionar Observação", key=f"add_{key_prefix}"):
                        if nova_observacao.strip():
                            registros.append({"observacao": nova_observacao.strip()})
                            st.session_state["formas_contratacao_detalhes"][forma] = registros
                            st.rerun()

                    # Exibe as observações em formato de lista
                    for i, obs in enumerate(registros):
                        col1, col2 = st.columns([8, 2])
                        col1.write(f"- {obs['observacao']}")
                        if col2.button("❌", key=f"del_{key_prefix}_{i}"):
                            del registros[i]
                            st.session_state["formas_contratacao_detalhes"][forma] = registros
                            st.rerun()

                # 🔹 Outros casos: Contrato ICMBio, Fundação de Apoio e Fundação de Amparo
                else:
                    novo_registro = {}

                    if forma == "Contrato ICMBio":
                        novo_registro["Contrato"] = st.text_input("Nome do Contrato:", key=f"{key_prefix}_novo_contrato")
                        novo_registro["Coordenação Gestora"] = st.checkbox(
                            "Coordenação Geral é Gestora do Contrato?",
                            key=f"{key_prefix}_coord_gestora"
                        )
                        novo_registro["Justificativa"] = st.text_area("Justificativa:", key=f"{key_prefix}_novo_justificativa")

                    elif forma == "Fundação de Apoio credenciada pelo ICMBio":
                        novo_registro["Projeto"] = st.text_input("Nome do Projeto:", key=f"{key_prefix}_novo_projeto")
                        novo_registro["SEI Projeto"] = st.text_input("Número SEI do Projeto:", key=f"{key_prefix}_novo_sei_projeto")
                        novo_registro["SEI Ata"] = st.text_input("Número SEI da Ata:", key=f"{key_prefix}_novo_sei_ata")
                        novo_registro["Concorda IN 18/2018"] = st.radio(
                            "Concorda com IN 18/2018 e 12/2024?", ["Sim", "Não"], key=f"{key_prefix}_novo_in_concorda"
                        )

                    elif forma == "Fundação de Amparo à pesquisa":
                        novo_registro["Fundação"] = st.text_input("Nome da Fundação:", key=f"{key_prefix}_novo_fundacao")
                        novo_registro["Descrição"] = st.text_area("Descrição:", key=f"{key_prefix}_novo_descricao")
                        novo_registro["IN Amparo"] = st.radio(
                            "A iniciativa está de acordo com IN de Amparo?",
                            ["Sim", "Não"], key=f"{key_prefix}_novo_in_amparo"
                        )

                    if st.button(f"➕ Adicionar {forma}", key=f"add_{key_prefix}"):
                        if all(val.strip() if isinstance(val, str) else True for val in novo_registro.values()):
                            registros.append(novo_registro)
                            st.session_state["formas_contratacao_detalhes"][forma] = registros
                            st.rerun()

                    # Exibe os registros adicionados como tabela (DataFrame)
                    if registros:
                        df_registros = pd.DataFrame(registros)
                        st.dataframe(df_registros, hide_index=True, use_container_width=True)

                        for i in range(len(registros)):
                            col1, col2 = st.columns([8, 2])
                            col1.write(f"📄 {', '.join([f'{k}: {v}' for k, v in registros[i].items()])}")
                            if col2.button("❌ Remover", key=f"del_{key_prefix}_{i}"):
                                del registros[i]
                                st.session_state["formas_contratacao_detalhes"][forma] = registros
                                st.rerun()

        # 4️⃣ Botão para salvar todas as alterações
        if st.button("💾 Salvar Informações de Contratação"):
            formas_dict = {
                "tabela_formas": st.session_state["df_formas_contratacao"].to_dict(orient="records"),
                "detalhes_por_forma": st.session_state["formas_contratacao_detalhes"]
            }
            st.session_state["formas_contratacao_detalhes"] = formas_dict
            st.success("✅ Formas de contratação salvas com sucesso!")















    # botão do form para salvar os dados editados na sessão
    if st.form_submit_button("Salvar Alterações"):

        # Verificação prévia antes de salvar
        if not st.session_state["objetivo_geral"]:
            st.error("O campo 'Objetivo Geral' não pode estar vazio.")
        elif not st.session_state["objetivos_especificos"]:
            st.error("A lista de 'Objetivos Específicos' não pode estar vazia.")
        elif not st.session_state["introducao"]:
            st.error("O campo 'Introdução' não pode estar vazio.")
        elif not st.session_state["justificativa"]:
            st.error("O campo 'Justificativa' não pode estar vazio.")
        elif not st.session_state["metodologia"]:
            st.error("O campo 'Metodologia' não pode estar vazio.")
        else:
            # salvar objetivos geral e específicos
            st.session_state["objetivo_geral"] = st.session_state["objetivo_geral"]

            # salvar textos
            st.session_state["introducao"] = st.session_state["introducao"]
            st.session_state["justificativa"] = st.session_state["justificativa"]
            st.session_state["metodologia"] = st.session_state["metodologia"]

            # salvar eixos temáticos
            st.session_state["eixos_tematicos"] = st.session_state["eixos_tematicos"]

            # salvar insumos
            if "insumos" not in st.session_state:
                st.session_state["insumos"] = {}
            else:
                st.session_state["insumos"] = st.session_state["insumos"]

            # salvar unidades de conservação
            st.session_state["df_uc_editado"] = st.session_state["df_uc_editado"]

            # st.success("Alterações salvas com sucesso!")

        st.success("Alterações salvas com sucesso!")


# -------------------------------------------
# BOTÃO FINAL PARA SALVAR CADASTRO
# -------------------------------------------
st.divider()
col1, col2, col3 = st.columns(3)
with col2:
    if st.button("📝 Enviar Cadastro", key="btn_salvar_geral"):
        salvar_dados_iniciativa(
            id_iniciativa=nova_iniciativa,
            usuario=cpf_usuario,
            objetivo_geral=st.session_state["objetivo_geral"],
            objetivos_especificos=st.session_state["objetivos_especificos"],
            eixos_tematicos=st.session_state["eixos_tematicos"],
            introducao=st.session_state["introducao"],
            justificativa=st.session_state["justificativa"],
            metodologia=st.session_state["metodologia"],
            demais_informacoes=st.session_state["demais_informacoes"]
        )
        st.success("✅ Cadastro atualizado com sucesso!")


st.divider()
# st.caption("ℹ️ Informações Originais do Resumo Executivo de Iniciativas", help="ref.: documentos SEI")

# # 1) Exibe resumos do SETOR
# def tratar_valor(valor):
#     if pd.isna(valor) or valor is None or str(valor).strip().lower() == "null":
#         return "(sem informação)"
#     return str(valor).strip()

# resumos = carregar_resumo_iniciativa(setor)
# if resumos is not None:
#     for _, r in resumos.iterrows():
#         nome_inic = tratar_valor(r.get("iniciativa", "Iniciativa Desconhecida"))
#         with st.expander(f"📖 {nome_inic}", expanded=False):
#             st.divider()
#             st.write(f"**🎯 Objetivo Geral:** {tratar_valor(r.get('objetivo_geral'))}")
#             st.divider()
#             st.write(f"**🏢 Diretoria:** {tratar_valor(r.get('diretoria'))}")
#             st.write(f"**📌 Coordenação Geral:** {tratar_valor(r.get('coordenação_geral'))}")
#             st.write(f"**🗂 Coordenação:** {tratar_valor(r.get('coordenação'))}")
#             st.write(f"**📍 Demandante:** {tratar_valor(r.get('demandante'))}")
#             st.divider()
#             st.write(f"**📝 Introdução:** {tratar_valor(r.get('introdução'))}")
#             st.divider()
#             st.write(f"**💡 Justificativa:** {tratar_valor(r.get('justificativa'))}")
#             st.divider()
#             st.write(f"**🏞 Unidades de Conservação / Benefícios:** {tratar_valor(r.get('unidades_de_conservação_beneficiadas'))}")
#             st.divider()
#             st.write(f"**🔬 Metodologia:** {tratar_valor(r.get('metodologia'))}")

# st.divider()


st.write(st.session_state)