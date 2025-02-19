import psycopg2
import streamlit as st

# Configuração do banco de dados
DB_HOST = "10.197.42.64"
DB_NAME = "teste"
DB_USER = "postgres"
DB_PASSWORD = "asd"
DB_PORT = "6000"  # Altere se necessário



def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        port=DB_PORT,  # Adicionando a porta
        password=DB_PASSWORD
    )

def fetch_processes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM processos")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def insert_process(nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO processos (nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei) VALUES (%s, %s, %s, %s, %s)",
        (nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
def update_process(process_id, nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE processos SET nome = %s, unidade_conservacao = %s, eixo_tematico = %s, numero_sei = %s, no_sei = %s WHERE id = %s",
        (nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei, process_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_process(process_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processos WHERE id = %s", (process_id,))
    conn.commit()
    cursor.close()
    conn.close()
