import json
import numpy as np
import pandas as pd
import sqlite3
import os
import streamlit as st


def init_database():
    # 📌 Caminhos dos arquivos de dados e do banco
    json_path = "dados/base_iniciativas_consolidada.json"
    excel_path = "dados/base_iniciativas_resumos_sei.xlsx"
    excel_path_elegiveis = "dados/base_iniciativas_elegiveis.xlsx"
    db_path = "database/app_data.db"

    # Credenciais do usuário admin (vêm do [Secrets] do Streamlit)
    admin_cpf = st.secrets["ADMIN_CPF"]
    admin_nome = st.secrets["ADMIN_NOME"]
    admin_email = st.secrets["ADMIN_EMAIL"]
    admin_setor = st.secrets["ADMIN_SETOR"]
    admin_perfil = st.secrets["ADMIN_PERFIL"]

    # 📌 Criando diretório do banco de dados se não existir
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ----------------------------------------------------------------------------
    # 1) TABELA DE USUÁRIOS
    # ----------------------------------------------------------------------------
    # cursor.execute(""" DROP TABLE IF EXISTS tf_usuarios """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tf_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            email TEXT NOT NULL,
            setor_demandante TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'comum' -- Pode ser 'comum' ou 'admin'
        )
    """)

    # Cria (ou ignora) um usuário admin master
    cursor.execute("""
        INSERT OR IGNORE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, (admin_cpf, admin_nome, admin_email, admin_setor, admin_perfil))

    # Cria (ou ignora) um usuário com perfil cocam
    cursor.execute("""
        INSERT OR IGNORE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, ("11111111111", "COCAM", " ", "COCAM", "cocam"))



    # Cria (ou ignora) um usuário com perfil cocam
    cursor.execute("""
        INSERT OR REPLACE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, ("08672224760", "Luiz Felipe de Luca de Souza", "luiz-felipe.souza@icmbio.gov.br ", "DIMAN", "comum"))



    # Cria (ou ignora) um usuário com perfil cocam (se o usuário não existir, ele será criado)
    cursor.execute("""
        INSERT OR REPLACE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, ("78789710134", "Renata Cesário", "renata.gomes@icmbio.gov.br", "DIMAN", "comum"))


    # Cria (ou ignora) um usuário com perfil cocam (se o usuário não existir, ele será criado)
    # 02705050167
    cursor.execute("""
        INSERT OR REPLACE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, ("02705050167", "Pedro Henrique Pereira Costa", "pedro.costa@icmbio.gov.br", "DIMAN", "comum"))

    
    cursor.execute("""
        INSERT OR REPLACE INTO tf_usuarios (cpf, nome_completo, email, setor_demandante, perfil)
        VALUES (?, ?, ?, ?, ?)
    """, ("07916703688", "Pedro Simões Soares", "pedro.soares@icmbio.gov.br", "DIMAN", "admin"))





    # Caminho do arquivo carregado
    file_path = "dados/base_iniciativas_consolidada.xlsx"

    # Carregar o arquivo Excel
    xls = pd.ExcelFile(file_path)

    # Listar as planilhas disponíveis
    xls.sheet_names

    # Carregar a planilha específica
    df = pd.read_excel(xls, sheet_name="BASE_INICIATIVAS_CONSOLIDADA")

    # Exibir as primeiras linhas e colunas disponíveis
    df.head(), df.columns


    # Converter o DataFrame para uma estrutura de dicionários
    json_data = df.to_dict(orient="records")

    # Caminho para salvar o arquivo JSON
    json_file_path = "dados/base_iniciativas_consolidada.json"

    # Salvar como JSON formatado
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)
    

    # Retornar o caminho do arquivo JSON gerado
    # json_file_path



    # ----------------------------------------------------------------------------
    # 2) LEITURA DA BASE JSON (df_base) E CRIAÇÃO DE TABELAS DE APOIO
    # ----------------------------------------------------------------------------
    df_base = pd.read_json(json_path)

    # Converter "Nº SEI" para numérico, tratar "-" como NaN
    df_base["Nº SEI"] = df_base["Nº SEI"].astype(str).replace("-", np.nan)
    df_base["Nº SEI"] = pd.to_numeric(df_base["Nº SEI"], errors="coerce")

    # Selecionar colunas relevantes
    colunas_base = [
        "DEMANDANTE",
        "Nome da Proposta/Iniciativa Estruturante",
        "Unidade de Conservação",
        "Observações",
        "VALOR TOTAL ALOCADO",
        "Valor da Iniciativa (R$)",
        "Valor Total da Iniciativa",
        "SALDO",
        "Nº SEI",
        "AÇÃO DE APLICAÇÃO",
        "CATEGORIA UC",
        "CNUC",
        "GR",
        "BIOMA",
        "UF"
    ]
    df_base = df_base[colunas_base]

    # Criar tabela fixa de consulta
    cursor.execute(""" DROP TABLE IF EXISTS td_dados_base_iniciativas """)
    df_base.to_sql("td_dados_base_iniciativas", conn, if_exists="replace", index=False)

    # ----------------------------------------------------------------------------
    # 3) LEITURA DA PLANILHA (EXCEL) COM RESUMOS SEI
    # ----------------------------------------------------------------------------
    df_resumos = pd.read_excel(excel_path, sheet_name="Planilha1", engine="openpyxl")
    df_resumos.dropna(how="all", inplace=True)

    # Padroniza colunas (minúsculas, underscores)
    df_resumos.columns = [col.strip().lower().replace(" ", "_") for col in df_resumos.columns]

    # Cria tabela para armazenar resumos SEI
    cursor.execute(""" DROP TABLE IF EXISTS td_dados_resumos_sei """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_dados_resumos_sei (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diretoria TEXT,
            coordenacao_geral TEXT,
            coordenacao TEXT,
            demandante TEXT,
            id_resumo TEXT,
            iniciativa TEXT,
            introducao TEXT,
            justificativa TEXT,
            objetivo_geral TEXT,
            unidades_conservacao TEXT,
            metodologia TEXT
        )
    """)
    conn.commit()

    # Salva dados do Excel na tabela
    df_resumos.to_sql("td_dados_resumos_sei", conn, if_exists="replace", index=False)

    # ----------------------------------------------------------------------------
    # 4) CRIAÇÃO DAS TABELAS DIMENSÃO
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS td_demandantes """)
    cursor.execute(""" DROP TABLE IF EXISTS td_iniciativas """)
    cursor.execute(""" DROP TABLE IF EXISTS td_acoes_aplicacao """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_demandantes (
            id_demandante INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_demandante TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_iniciativas (
            id_iniciativa INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_iniciativa TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_acoes_aplicacao (
            id_acao INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_acao TEXT UNIQUE
        )
    """)

    # ----------------------------------------------------------------------------
    # 5) TABELA DE UNIDADES
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS td_unidades """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_unidades (
            cnuc TEXT PRIMARY KEY,
            nome_unidade TEXT,
            gr TEXT,
            categoria_uc TEXT,
            bioma TEXT,
            uf TEXT
        )
    """)

    # ----------------------------------------------------------------------------
    # 6) TABELA FATO - tf_cadastros_iniciativas
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS tf_cadastros_iniciativas """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tf_cadastros_iniciativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_demandante INTEGER,
            id_iniciativa INTEGER,
            id_acao INTEGER,
            cnuc TEXT,
            id_composto TEXT UNIQUE,
            observacoes TEXT,
            saldo REAL,
            valor_total_alocado REAL,
            valor_iniciativa REAL,
            valor_total_iniciativa REAL,
            num_sei TEXT,
            formas_contratacao TEXT,
            FOREIGN KEY (id_demandante) REFERENCES td_demandantes(id_demandante),
            FOREIGN KEY (id_iniciativa) REFERENCES td_iniciativas(id_iniciativa),
            FOREIGN KEY (id_acao) REFERENCES td_acoes_aplicacao(id_acao),
            FOREIGN KEY (cnuc) REFERENCES td_unidades(cnuc)
        )
    """)


    # ----------------------------------------------------------------------------
    # CRIA TABELA tf_distribuicao_elegiveis
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS tf_distribuicao_elegiveis """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tf_distribuicao_elegiveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "DEMANDANTE (diretoria)" TEXT,
            "Nome da Proposta/Iniciativa Estruturante" TEXT,
            "AÇÃO DE APLICAÇÃO" TEXT,
            "Unidade de Conservação" TEXT,
            CNUC TEXT,
            "TetoSaldo disponível" INTEGER,
            "TetoPrevisto 2025" INTEGER,
            "TetoPrevisto 2026" INTEGER,
            "TetoPrevisto 2027" INTEGER,
            "TetoTotalDisponivel" INTEGER,
            "A Distribuir" INTEGER
        )
    """)


    # Lê o arquivo base_iniciativas_elegiveis.xlsx
    df_elegiveis = pd.read_excel(excel_path_elegiveis, engine="openpyxl")

    # Garantir que os valores numéricos tenham até 2 casas decimais
    colunas_numericas = [
        "TetoSaldo disponível",
        "TetoPrevisto 2025",
        "TetoPrevisto 2026",
        "TetoPrevisto 2027"
    ]

    # Converte os valores para float e arredonda para 2 casas decimais
    for col in colunas_numericas:
        df_elegiveis[col] = pd.to_numeric(df_elegiveis[col], errors="coerce").round(2).fillna(0.00)

    # Criar a coluna "TetoTotalDisponivel" antes de inserir no banco
    df_elegiveis["TetoTotalDisponivel"] = (
        df_elegiveis["TetoSaldo disponível"] +
        df_elegiveis["TetoPrevisto 2025"] +
        df_elegiveis["TetoPrevisto 2026"] +
        df_elegiveis["TetoPrevisto 2027"]
    ).round(2)

    # Inicializa a coluna "A Distribuir" como NULL
    df_elegiveis["A Distribuir"] = None

    # Define as colunas necessárias
    colunas_elegiveis = [
        "DEMANDANTE (diretoria)",
        "Nome da Proposta/Iniciativa Estruturante",
        "AÇÃO DE APLICAÇÃO",
        "Unidade de Conservação",
        "CNUC",
        "TetoSaldo disponível",
        "TetoPrevisto 2025",
        "TetoPrevisto 2026",
        "TetoPrevisto 2027",
        "TetoTotalDisponivel",
        "A Distribuir"
    ]

    # Filtra as colunas necessárias (ou renomeie caso sejam diferentes)
    df_distribuicao = df_elegiveis[colunas_elegiveis].copy()

    # (Opcional) Se quiser preencher tetos nulos com zero:
    df_distribuicao[
        [
            "TetoSaldo disponível",
            "TetoPrevisto 2025",
            "TetoPrevisto 2026",
            "TetoPrevisto 2027"
        ]
    ] = df_distribuicao[
        [
            "TetoSaldo disponível",
            "TetoPrevisto 2025",
            "TetoPrevisto 2026",
            "TetoPrevisto 2027"
        ]
    ].fillna(0)


    # se houverem linhas com unidade e ação de aplicação iguais, mas com diferentes tetos,
    # então, agrupe por unidade e ação de aplicação, somando os tetos
    df_distribuicao = df_distribuicao.groupby(
        ["DEMANDANTE (diretoria)", "Nome da Proposta/Iniciativa Estruturante", "AÇÃO DE APLICAÇÃO", "Unidade de Conservação", "CNUC"],
        as_index=False
    ).agg({
        "TetoSaldo disponível": "sum",
        "TetoPrevisto 2025": "sum",
        "TetoPrevisto 2026": "sum",
        "TetoPrevisto 2027": "sum",
        "TetoTotalDisponivel": "sum"
    })
    



    # Popula a nova tabela tf_distribuicao_elegiveis
    df_distribuicao.to_sql("tf_distribuicao_elegiveis", conn, if_exists="append", index=False)


    # ----------------------------------------------------------------------
    # 1️⃣ Recuperar os processos da tabela `td_samge_processos`
    # ----------------------------------------------------------------------
    df_processos = pd.read_sql_query("SELECT nome FROM td_samge_processos", conn)
    nomes_processos = [row["nome"] for _, row in df_processos.iterrows()]

    # ----------------------------------------------------------------------
    # 2️⃣ Adicionar colunas para cada processo na tabela `tf_distribuicao_elegiveis`
    # ----------------------------------------------------------------------
    cursor.execute("PRAGMA table_info(tf_distribuicao_elegiveis)")
    colunas_existentes = {col[1] for col in cursor.fetchall()}

    for processo in nomes_processos:
        if processo not in colunas_existentes:
            cursor.execute(f'ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "{processo}" REAL DEFAULT 0.00')


    # ----------------------------------------------------------------------
    # 3️⃣ Criar a coluna `TetoTotalDisponivel`, se não existir
    # ----------------------------------------------------------------------
    if "TetoTotalDisponivel" not in colunas_existentes:
        cursor.execute('ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "TetoTotalDisponivel" REAL')

    # Atualizar os valores de `TetoTotalDisponivel`
    cursor.execute("""
        UPDATE tf_distribuicao_elegiveis
        SET TetoTotalDisponivel = COALESCE("TetoSaldo disponível", 0) +
                                  COALESCE("TetoPrevisto 2025", 0) +
                                  COALESCE("TetoPrevisto 2026", 0) +
                                  COALESCE("TetoPrevisto 2027", 0)
    """)

    # ----------------------------------------------------------------------
    # 4️⃣ Criar a coluna `"A Distribuir"`, se não existir (mas sem calcular ainda)
    # ----------------------------------------------------------------------
    if "A Distribuir" not in colunas_existentes:
        cursor.execute('ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "A Distribuir" REAL NULL')

    # popular a coluna "A Distribuir" com valores iguais a teto total disponível
    cursor.execute("""
        UPDATE tf_distribuicao_elegiveis
        SET "A Distribuir" = TetoTotalDisponivel
    """)
    

    # ----------------------------------------------------------------------------
    # Ajuste na Tabela tf_distribuicao_elegiveis para incluir os IDs
    # ----------------------------------------------------------------------------
    cursor.execute("PRAGMA table_info(tf_distribuicao_elegiveis)")
    colunas_existentes = {col[1] for col in cursor.fetchall()}

    # Criar as colunas de IDs se ainda não existirem
    if "id_demandante" not in colunas_existentes:
        cursor.execute('ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "id_demandante" INTEGER')

    if "id_iniciativa" not in colunas_existentes:
        cursor.execute('ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "id_iniciativa" INTEGER')

    if "id_acao" not in colunas_existentes:
        cursor.execute('ALTER TABLE tf_distribuicao_elegiveis ADD COLUMN "id_acao" INTEGER')

    conn.commit()
    
    
    print("✅ `tf_distribuicao_elegiveis` atualizado com novas colunas, sem cálculo automático para 'A Distribuir'!")
    print("✅ Banco de dados atualizado com a nova tabela tf_distribuicao_elegiveis!")


    # ----------------------------------------------------------------------------
    # 7) TABELA PRINCIPAL DE REGRAS DE NEGÓCIO
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS tf_cadastro_regras_negocio """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tf_cadastro_regras_negocio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_iniciativa INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            objetivo_geral TEXT NOT NULL,            -- Texto simples
            objetivos_especificos TEXT NOT NULL,     -- JSON (lista de strings)
            introducao TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            metodologia TEXT NOT NULL,
            demais_informacoes TEXT,                 -- JSON (dict)
            eixos_tematicos TEXT NOT NULL,           -- JSON (lista de dicts)
            acoes_manejo TEXT NOT NULL,              -- JSON (dict com ações)
            insumos TEXT NOT NULL,                   -- JSON (dict ou lista com insumos)
            regra TEXT NOT NULL,                     -- JSON consolidado (opcional)
            distribuicao_ucs TEXT,                   -- JSON (DataFrame ou lista)
            formas_contratacao TEXT,                 -- JSON (dict com detalhes)

            FOREIGN KEY (id_iniciativa) REFERENCES td_iniciativas(id_iniciativa)
        )
    """)

    # ----------------------------------------------------------------------------
    # 8) TABELA DE INSUMOS
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS td_insumos """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elemento_despesa TEXT NOT NULL,
            especificacao_padrao TEXT,
            descricao_insumo TEXT,
            especificacao_tecnica TEXT,
            preco_referencia REAL,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


    # verifica se colunas origem, situacao e registrado_por existem na tabela td_insumos
    # se não existirem, cria as colunas com valores default
    cursor.execute("PRAGMA table_info(td_insumos)")
    columns = cursor.fetchall()
    columns = [col[1] for col in columns]
    if "origem" not in columns:
        cursor.execute(""" ALTER TABLE td_insumos ADD COLUMN origem TEXT DEFAULT 'base_funbio' """)
    if "situacao" not in columns:
        cursor.execute(""" ALTER TABLE td_insumos ADD COLUMN situacao TEXT DEFAULT 'ativo' """)
    if "registrado_por" not in columns:
        cursor.execute(""" ALTER TABLE td_insumos ADD COLUMN registrado_por TEXT DEFAULT 'admin' """)
    conn.commit()


    # ----------------------------------------------------------------------------
    # 9) POPULA AS TABELAS DIMENSÃO (demandantes, iniciativas, ações, unidades)
    # ----------------------------------------------------------------------------
    # Insere valores únicos
    for table, column, name_col in [
        ("td_demandantes", "DEMANDANTE", "nome_demandante"),
        ("td_iniciativas", "Nome da Proposta/Iniciativa Estruturante", "nome_iniciativa"),
        ("td_acoes_aplicacao", "AÇÃO DE APLICAÇÃO", "nome_acao")
    ]:
        unique_values = df_base[column].dropna().unique()
        for value in unique_values:
            cursor.execute(f"INSERT OR IGNORE INTO {table} ({name_col}) VALUES (?)", (value,))

    # Popula td_unidades
    unidades_unicas = df_base[["CNUC", "Unidade de Conservação", "GR", "CATEGORIA UC", "BIOMA", "UF"]].drop_duplicates()
    for _, row in unidades_unicas.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO td_unidades (cnuc, nome_unidade, gr, categoria_uc, bioma, uf)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row["CNUC"],
            row["Unidade de Conservação"],
            row["GR"],
            row["CATEGORIA UC"],
            row["BIOMA"],
            row["UF"]
        ))

    conn.commit()

    # ----------------------------------------------------------------------------
    # 10) CRIA MAPEAMENTOS DE ID (p/ relacionar no tf_cadastros_iniciativas)
    # ----------------------------------------------------------------------------
    id_maps = {}
    for table, column, id_col, name_col in [
        ("td_demandantes", "DEMANDANTE", "id_demandante", "nome_demandante"),
        ("td_iniciativas", "Nome da Proposta/Iniciativa Estruturante", "id_iniciativa", "nome_iniciativa"),
        ("td_acoes_aplicacao", "AÇÃO DE APLICAÇÃO", "id_acao", "nome_acao")
    ]:
        df_map = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        id_maps[table] = df_map.set_index(name_col)[id_col].to_dict()

    # Preenche colunas ID na df_base
    df_base["id_demandante"] = df_base["DEMANDANTE"].map(id_maps["td_demandantes"]).fillna(-1)
    df_base["id_iniciativa"] = df_base["Nome da Proposta/Iniciativa Estruturante"].map(id_maps["td_iniciativas"]).fillna(-1)
    df_base["id_acao"] = df_base["AÇÃO DE APLICAÇÃO"].map(id_maps["td_acoes_aplicacao"]).fillna(-1)

    # Salva na tabela fato
    df_base.to_sql("tf_cadastros_iniciativas", conn, if_exists="replace", index=False)



    # ----------------------------------------------------------------------------
    # Criar Mapeamento de IDs (para relacionar na tf_distribuicao_elegiveis)
    # ----------------------------------------------------------------------------
    id_maps = {}

    for table, column_in_distribuicao, id_col, name_col in [
        ("td_demandantes", "DEMANDANTE (diretoria)", "id_demandante", "nome_demandante"),
        ("td_iniciativas", "Nome da Proposta/Iniciativa Estruturante", "id_iniciativa", "nome_iniciativa"),
        ("td_acoes_aplicacao", "AÇÃO DE APLICAÇÃO", "id_acao", "nome_acao")
    ]:
        df_map = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        
        # 🔹 Normaliza os nomes para evitar erros por espaços extras ou maiúsculas/minúsculas
        df_map[name_col] = df_map[name_col].astype(str).str.strip().str.lower()
        
        id_maps[table] = df_map.set_index(name_col)[id_col].to_dict()

    # 🔍 Carregar os dados da tabela `tf_distribuicao_elegiveis`
    df_distribuicao = pd.read_sql_query("SELECT * FROM tf_distribuicao_elegiveis", conn)

    # 🔹 Normalizar os nomes das colunas na tabela de distribuição de elegíveis
    df_distribuicao["DEMANDANTE (diretoria)"] = df_distribuicao["DEMANDANTE (diretoria)"].astype(str).str.strip().str.lower()
    df_distribuicao["Nome da Proposta/Iniciativa Estruturante"] = df_distribuicao["Nome da Proposta/Iniciativa Estruturante"].astype(str).str.strip().str.lower()
    df_distribuicao["AÇÃO DE APLICAÇÃO"] = df_distribuicao["AÇÃO DE APLICAÇÃO"].astype(str).str.strip().str.lower()

    # 🔹 Substitui os valores por IDs corretos
    df_distribuicao["id_demandante"] = df_distribuicao["DEMANDANTE (diretoria)"].map(id_maps["td_demandantes"]).fillna(-1).astype(int)
    df_distribuicao["id_iniciativa"] = df_distribuicao["Nome da Proposta/Iniciativa Estruturante"].map(id_maps["td_iniciativas"]).fillna(-1).astype(int)
    df_distribuicao["id_acao"] = df_distribuicao["AÇÃO DE APLICAÇÃO"].map(id_maps["td_acoes_aplicacao"]).fillna(-1).astype(int)

    # 🔹 Salvar os dados atualizados na tabela
    df_distribuicao.to_sql("tf_distribuicao_elegiveis", conn, if_exists="replace", index=False)

    # 🔍 Verificar se ainda há IDs inválidos
    df_check = pd.read_sql_query("""
        SELECT * FROM tf_distribuicao_elegiveis 
        WHERE id_demandante = -1 OR id_iniciativa = -1 OR id_acao = -1
    """, conn)

    if df_check.empty:
        print("✅ Todos os IDs foram mapeados corretamente!")
    else:
        print("⚠️ Existem registros sem ID correto! Verifique os nomes na tabela.")

    conn.commit()


    # ----------------------------------------------------------------------------
    # 11) CARREGA INSUMOS A PARTIR DO EXCEL base_insumos.xlsx
    # ----------------------------------------------------------------------------
    try:
        excel_insumos_path = "dados/base_insumos.xlsx"
        df_raw = pd.read_excel(excel_insumos_path, sheet_name=0)

        # Garante colunas mínimas
        if "Especificação Técnica (detalhamento)" not in df_raw.columns:
            df_raw["Especificação Técnica (detalhamento)"] = ""

        df_insumos = df_raw.rename(columns={
            "Elemento de Despesa": "elemento_despesa",
            "Especificação Padrão": "especificacao_padrao",
            "Descrição do Insumo": "descricao_insumo",
            "Especificação Técnica (detalhamento)": "especificacao_tecnica",
            "Valor ATUALIZADO EM Dezembro/2024": "valor_referencia"
        })

        # # Ajusta valores numéricos
        # df_insumos["valor_referencia"] = (
        #     df_insumos["valor_referencia"]
        #     .astype(str)
        #     .str.replace(".", "")   # remove milhar
        #     .str.replace(",", ".")  # vírgula decimal -> ponto
        # )
        df_insumos["valor_referencia"] = pd.to_numeric(df_insumos["valor_referencia"], errors="coerce").fillna(0.0)

        # Seleciona colunas na ordem
        df_insumos = df_insumos[[
            "elemento_despesa",
            "especificacao_padrao",
            "descricao_insumo",
            "especificacao_tecnica",
            "valor_referencia"
        ]]

        # Renomeia "valor_referencia" -> "preco_referencia"
        df_insumos.rename(columns={"valor_referencia": "preco_referencia"}, inplace=True)

        # Adiciona um registro de elemento de despesa para "Bens" e um para "Serviços"
        df_bens = pd.DataFrame({
            "elemento_despesa": ["Bens"],
            "especificacao_padrao": [""],
            "descricao_insumo": [""],
            "especificacao_tecnica": [""],
            "preco_referencia": [0.0]
        })
        df_servicos = pd.DataFrame({
            "elemento_despesa": ["Serviços"],
            "especificacao_padrao": [""],
            "descricao_insumo": [""],
            "especificacao_tecnica": [""],
            "preco_referencia": [0.0]
        })

        # Concatena os DataFrames
        df_insumos = pd.concat([df_insumos, df_bens, df_servicos], ignore_index=True)

        # Insere no banco (append)
        df_insumos.to_sql("td_insumos", conn, if_exists="append", index=False)
        print("✅ Tabela td_insumos populada com sucesso a partir do Excel!")
    except Exception as e:
        print("❌ Erro ao tentar popular td_insumos:", e)

    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")


def init_samge_database():
    # Caminho do arquivo Excel com os dados do SAMGe
    excel_path = "dados/matrizConceitual_linguagemSAMGe.xlsx"
    db_path = "database/app_data.db"

    """Cria as tabelas do SAMGe no banco de dados e popula com os dados do Excel."""
    if not os.path.exists(excel_path):
        print("❌ Arquivo do SAMGe não encontrado!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ----------------------------------------------------------------------------
    # Tabelas do SAMGe: Macroprocessos, Processos, Ações de Manejo, Atividades
    # ----------------------------------------------------------------------------
    cursor.execute(""" DROP TABLE IF EXISTS td_samge_macroprocessos """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_samge_macroprocessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_m TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT
        )
    """)

    cursor.execute(""" DROP TABLE IF EXISTS td_samge_processos """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_samge_processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_p TEXT UNIQUE NOT NULL,
            macroprocesso_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            explicacao TEXT,
            FOREIGN KEY (macroprocesso_id) REFERENCES td_samge_macroprocessos(id_m)
        )
    """)

    cursor.execute(""" DROP TABLE IF EXISTS td_samge_acoes_manejo """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_samge_acoes_manejo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_ac TEXT UNIQUE NOT NULL,
            processo_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            explicacao TEXT,
            entrega TEXT,
            FOREIGN KEY (processo_id) REFERENCES td_samge_processos(id_p)
        )
    """)

    cursor.execute(""" DROP TABLE IF EXISTS td_samge_atividades """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS td_samge_atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_at TEXT UNIQUE NOT NULL,
            acao_manejo_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            explicacao TEXT,
            subentrega TEXT,
            FOREIGN KEY (acao_manejo_id) REFERENCES td_samge_acoes_manejo(id_ac)
        )
    """)

    conn.commit()

    # Lê o Excel do SAMGe
    df = pd.read_excel(excel_path, engine="openpyxl")

    # Padroniza colunas
    df.columns = df.columns.str.strip()

    # ----------------------------------------------------------------------------
    # Insere Macroprocessos
    # ----------------------------------------------------------------------------
    macroprocessos = df[["ID-M", "Macroprocesso"]].drop_duplicates()
    macroprocessos.columns = ["id_m", "nome"]
    macroprocessos["descricao"] = None
    macroprocessos.to_sql("td_samge_macroprocessos", conn, if_exists="replace", index=False)

    # ----------------------------------------------------------------------------
    # Insere Processos
    # ----------------------------------------------------------------------------
    processos = df[["ID-P", "Processo", "Descrição do Processo", "Explicação do Processo", "ID-M"]].drop_duplicates()
    processos.columns = ["id_p", "nome", "descricao", "explicacao", "macroprocesso_id"]
    processos.to_sql("td_samge_processos", conn, if_exists="replace", index=False)

    DB_PATH = "database/app_data.db"
    
    def remover_processos_duplicados():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 🔍 Identificar registros duplicados (com mesmo id_p)
        df_processos = pd.read_sql_query("SELECT * FROM td_samge_processos", conn)

        if df_processos.duplicated(subset=["id_p"]).any():
            print("⚠️ Processos duplicados encontrados! Removendo duplicatas...")

            # Mantemos apenas o primeiro registro de cada `id_p`
            df_processos = df_processos.drop_duplicates(subset=["id_p"], keep="first")

            # Apaga os registros duplicados da tabela
            cursor.execute("DELETE FROM td_samge_processos")

            # Insere novamente os registros sem duplicatas
            df_processos.to_sql("td_samge_processos", conn, if_exists="append", index=False)

            conn.commit()
            print("✅ Processos duplicados removidos!")
        else:
            print("✅ Nenhum processo duplicado encontrado.")

        conn.close()

    # Executar a remoção de duplicatas
    remover_processos_duplicados()

    # ----------------------------------------------------------------------------
    # Insere Ações de Manejo
    # ----------------------------------------------------------------------------
    acoes_manejo = df[["ID-AC", "Ação de Manejo", "Descrição da Ação de Manejo", "Explicação da Ação de Manejo", "Entrega", "ID-P"]].drop_duplicates()
    acoes_manejo.columns = ["id_ac", "nome", "descricao", "explicacao", "entrega", "processo_id"]
    acoes_manejo.to_sql("td_samge_acoes_manejo", conn, if_exists="replace", index=False)

    # ----------------------------------------------------------------------------
    # Insere Atividades
    # ----------------------------------------------------------------------------
    atividades = df[["ID-AT", "Atividade", "Descrição da Atividade", "Explicação da Atividade", "Subentrega", "ID-AC"]].drop_duplicates()
    atividades.columns = ["id_at", "nome", "descricao", "explicacao", "subentrega", "acao_manejo_id"]
    atividades.to_sql("td_samge_atividades", conn, if_exists="replace", index=False)

    conn.close()
    print("✅ Banco de dados SAMGe atualizado com sucesso!")


if __name__ == "__main__":
    init_samge_database()
    init_database()
