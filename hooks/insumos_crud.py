# ---------------------------------------------------------
# arquivo: database/insumos_crud.py
# ---------------------------------------------------------
import sqlite3
import pandas as pd

def get_connection():
    return sqlite3.connect("database/app_data.db")

def inserir_insumo(elemento_despesa: str, especificacao_padrao: str, descricao_insumo: str,
                   especificacao_tecnica: str, preco_referencia: float) -> None:
    """
    Insere um novo insumo na tabela td_insumos.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO td_insumos (
            elemento_despesa,
            especificacao_padrao,
            descricao_insumo,
            especificacao_tecnica,
            preco_referencia
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (elemento_despesa, especificacao_padrao, descricao_insumo, especificacao_tecnica, preco_referencia)
    )
    conn.commit()
    conn.close()

def listar_insumos() -> pd.DataFrame:
    """
    Retorna todos os insumos em formato de DataFrame.
    """
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM td_insumos ORDER BY id ASC", conn)
    conn.close()
    return df

def atualizar_insumo(
    insumo_id: int,
    elemento_despesa: str,
    especificacao_padrao: str,
    descricao_insumo: str,
    especificacao_tecnica: str,
    preco_referencia: float
) -> None:
    """
    Atualiza os dados de um insumo existente.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE td_insumos
        SET
            elemento_despesa = ?,
            especificacao_padrao = ?,
            descricao_insumo = ?,
            especificacao_tecnica = ?,
            preco_referencia = ?
        WHERE id = ?
        """,
        (elemento_despesa, especificacao_padrao, descricao_insumo, especificacao_tecnica, preco_referencia, insumo_id)
    )
    conn.commit()
    conn.close()

def deletar_insumo(insumo_id: int) -> None:
    """
    Deleta um insumo pelo ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM td_insumos WHERE id = ?", (insumo_id,))
    conn.commit()
    conn.close()
