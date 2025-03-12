###############################################################################
#                       1. IMPORTAÇÕES E CONFIGURAÇÕES                        #
###############################################################################
import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime
import html
import re
import tempfile
from io import BytesIO

# PDF com xhtml2pdf
from xhtml2pdf import pisa

# Visualização de PDF
from streamlit_pdf_viewer import pdf_viewer

# Verificação de login no Streamlit
if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    st.warning("🔒 Acesso negado! Faça login na página principal para acessar esta seção.")
    st.stop()

st.set_page_config(
    page_title="Visualização de Cadastros",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)
st.subheader("📊 Visualização de Cadastros Realizados")

###############################################################################
#                    2. FUNÇÕES DE CARREGAMENTO DE DADOS                      #
###############################################################################
def load_iniciativas(setor: str, perfil: str) -> pd.DataFrame:
    """Carrega iniciativas do banco SQLite conforme setor e perfil."""
    conn = sqlite3.connect("database/app_data.db")
    if perfil in ("admin", "cocam"):
        query = """
        SELECT r.*, i.nome_iniciativa
        FROM tf_cadastro_regras_negocio r
        JOIN td_iniciativas i ON r.id_iniciativa = i.id_iniciativa
        JOIN (
            SELECT id_iniciativa, MAX(data_hora) AS max_data
            FROM tf_cadastro_regras_negocio
            GROUP BY id_iniciativa
        ) sub ON sub.id_iniciativa = r.id_iniciativa
             AND sub.max_data = r.data_hora
        ORDER BY r.data_hora DESC
        """
        df = pd.read_sql_query(query, conn)
    else:
        query = """
        SELECT r.*, i.nome_iniciativa
        FROM tf_cadastro_regras_negocio r
        JOIN td_iniciativas i ON r.id_iniciativa = i.id_iniciativa
        JOIN tf_usuarios u ON r.usuario = u.cpf
        JOIN (
            SELECT id_iniciativa, MAX(data_hora) AS max_data
            FROM tf_cadastro_regras_negocio
            GROUP BY id_iniciativa
        ) sub ON sub.id_iniciativa = r.id_iniciativa
             AND sub.max_data = r.data_hora
        WHERE u.setor_demandante = ?
        ORDER BY r.data_hora DESC
        """
        df = pd.read_sql_query(query, conn, params=[setor])
    conn.close()
    return df

def load_acoes_map():
    """Retorna dict id_acao -> nome_acao."""
    conn = sqlite3.connect("database/app_data.db")
    df = pd.read_sql_query("SELECT id_ac, nome FROM td_samge_acoes_manejo", conn)
    conn.close()
    return {str(row['id_ac']): row['nome'] for _, row in df.iterrows()}

def load_insumos_map():
    """Retorna dict id_insumo -> descricao_insumo."""
    conn = sqlite3.connect("database/app_data.db")
    df = pd.read_sql_query("SELECT id, descricao_insumo FROM td_insumos", conn)
    conn.close()
    return {str(row['id']): row['descricao_insumo'] for _, row in df.iterrows()}

acoes_map = load_acoes_map()
insumos_map = load_insumos_map()

###############################################################################
#                      3. FUNÇÕES DE FORMATAÇÃO DE CONTEÚDO (HTML)           #
###############################################################################
def safe_html(value: str) -> str:
    if value is None:
        value = ""
    return html.escape(str(value)).replace("\n", "<br>")

def format_objetivos_especificos(json_str):
    """Formata JSON de objetivos específicos em HTML (<ul>...</ul>)"""
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            if not data:
                return "Nenhum objetivo específico."
            html_list = "<ul>"
            for item in data:
                item_escaped = html.escape(str(item))
                html_list += f"<li>{item_escaped}</li>"
            html_list += "</ul>"
            return html_list

        elif isinstance(data, dict):
            if not data:
                return "Nenhum objetivo específico."
            html_list = "<ul>"
            for k, v in data.items():
                item_escaped = f"{html.escape(str(k))}: {html.escape(str(v))}"
                html_list += f"<li>{item_escaped}</li>"
            html_list += "</ul>"
            return html_list

        return html.escape(str(data))
    except Exception:
        return html.escape(json_str)

def format_eixos_tematicos_table(json_str):
    """Tabela de Eixos Temáticos (Eixo, Ação de Manejo, Insumos) em HTML."""
    try:
        data = json.loads(json_str)
        if not data:
            return "Nenhum eixo temático cadastrado."

        table_html = """<table>
<thead>
<tr>
<th>Eixo Temático</th>
<th>Ação de Manejo</th>
<th>Insumos</th>
</tr>
</thead>
<tbody>
"""
        for eixo in data:
            nome_eixo = eixo.get("nome_eixo", "Sem nome")
            acoes = eixo.get("acoes_manejo", {})
            if not acoes:
                table_html += f"""
<tr>
<td>{nome_eixo}</td>
<td>Nenhuma ação de manejo</td>
<td>-</td>
</tr>
"""
            else:
                for acao_id, detalhes in acoes.items():
                    nome_acao = acoes_map.get(str(acao_id), f"Ação {acao_id}")
                    insumos_list = detalhes.get("insumos", [])
                    if insumos_list:
                        insumos_html = ", ".join(insumos_map.get(str(i), str(i)) for i in insumos_list)
                    else:
                        insumos_html = "-"
                    table_html += f"""
<tr>
<td>{nome_eixo}</td>
<td>{nome_acao}</td>
<td>{insumos_html}</td>
</tr>
"""
        table_html += "</tbody></table>"
        return table_html.strip()
    except Exception as e:
        return f"Erro ao gerar tabela de Eixos Temáticos: {str(e)}"

def format_formas_contratacao(json_str):
    """Tabelas de Formas de Contratação e detalhes, em HTML."""
    try:
        data = json.loads(json_str)
        if not data:
            return "<p>Nenhuma forma de contratação cadastrada.</p>"

        tabela_formas = data.get("tabela_formas", [])
        if not tabela_formas:
            formas_html = "<p>Nenhuma forma de contratação listada.</p>"
        else:
            formas_html = """
<table>
<thead>
<tr><th>Forma de Contratação</th><th>Status</th></tr>
</thead>
<tbody>
"""
            for item in tabela_formas:
                forma = str(item.get("Forma de Contratação", "Sem descrição"))
                selecionado = item.get("Selecionado", False)
                status = "✅ Selecionado" if selecionado else "❌ Não selecionado"
                formas_html += f"""
<tr>
<td>{html.escape(forma)}</td>
<td>{html.escape(status)}</td>
</tr>
"""
            formas_html += "</tbody></table>"

        detalhes_html = ""
        detalhes_por_forma = data.get("detalhes_por_forma", {})
        for forma, dict_det in detalhes_por_forma.items():
            detalhes_html += f"<h4>{html.escape(forma)}</h4>"
            if not dict_det:
                detalhes_html += "<p>Sem detalhes específicos.</p>"
                continue

            detalhes_html += """
<table>
<thead>
<tr><th>Campo</th><th>Valor</th></tr>
</thead>
<tbody>
"""
            for k, v in dict_det.items():
                if isinstance(v, list):
                    if v:
                        v = "<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in v) + "</ul>"
                    else:
                        v = "Nenhuma opção selecionada"
                detalhes_html += f"""
<tr>
<td>{html.escape(str(k))}</td>
<td>{v}</td>
</tr>
"""
            detalhes_html += "</tbody></table>"

        return formas_html.strip() + "<br>" + detalhes_html.strip()
    except Exception as e:
        return f"<p>Erro ao formatar as formas de contratação: {html.escape(str(e))}</p>"

def format_insumos(json_str):
    """Lista de insumos (IDs -> descrições) ou dict, em HTML."""
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            result = [insumos_map.get(str(insumo), str(insumo)) for insumo in data]
            result = sorted(result, key=lambda x: x.lower())
            if not result:
                return "Nenhum insumo cadastrado."
            return "- " + "<br>- ".join(result)
        elif isinstance(data, dict):
            sorted_items = sorted(data.items(), key=lambda x: str(x[0]).lower())
            lines = []
            for k, v in sorted_items:
                lines.append(f"{k}: {v}")
            return "<br>".join(lines)
        return str(data)
    except Exception:
        return str(json_str)

def process_generic_json(field: str) -> str:
    """Formata JSON simples (list/dict) em bullet ou key:value (HTML)."""
    try:
        data = json.loads(field)
        if isinstance(data, list):
            return "- " + "<br>- ".join(map(str, data))
        elif isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if v is None or v == "":
                    v = "Não informado"
                lines.append(f"{k}: {v}")
            return "<br>".join(lines)
        return str(data)
    except Exception:
        return str(field)

def format_float_br(value_str: str) -> str:
    """Converte float p/ estilo brasileiro (1.234,56)."""
    if not value_str:
        return ""
    try:
        val = float(value_str)
    except ValueError:
        return value_str
    val_en = f"{val:,.2f}"  
    parts = val_en.split(".")
    integer_part = parts[0].replace(",", ".")
    decimal_part = parts[1]
    val_br = integer_part + "," + decimal_part
    return val_br

def format_distribuicao_ucs(json_str: str) -> str:
    """Tabela HTML para distribuição por unidade."""
    try:
        data = json.loads(json_str)
        if not data or not isinstance(data, list):
            return "<p>Nenhuma informação de distribuição.</p>"

        df = pd.DataFrame(data)
        df_aggregated = df.groupby(["Unidade", "Acao"], as_index=False)["Valor Alocado"].sum()

        table_html = """
<table>
<thead>
<tr><th>Unidade</th><th>Ação de Aplicação</th><th style="text-align:right;">Valor Alocado</th></tr>
</thead>
<tbody>
"""
        for _, row_ in df_aggregated.iterrows():
            unidade = html.escape(str(row_["Unidade"]))
            acao = html.escape(str(row_["Acao"]))
            valor_formatado = format_float_br(str(row_["Valor Alocado"]))
            table_html += f"""
<tr><td>{unidade}</td><td>{acao}</td><td style="text-align:right;">{valor_formatado}</td></tr>
"""
        table_html += "</tbody></table>"
        return table_html
    except Exception as e:
        return f"<p>Erro ao formatar distribuição por unidade: {html.escape(str(e))}</p>"

def format_distribuicao_por_eixo(json_str: str) -> str:
    """Tabela(s) HTML da distribuição por eixo."""
    try:
        data = json.loads(json_str)
        if not data or not isinstance(data, list):
            return "<p>Nenhuma informação de distribuição.</p>"

        df = pd.DataFrame(data)
        colunas_base = {"Unidade", "Acao", "Valor Alocado", "Distribuir"}
        eixos_cols = [col for col in df.columns if col not in colunas_base]
        if not eixos_cols:
            return "<p>Nenhum eixo temático identificado.</p>"

        df_aggregated = df.groupby(["Unidade", "Acao"], as_index=False)[eixos_cols + ["Valor Alocado"]].sum()

        html_output = ""
        soma_por_eixo = {}
        for eixo in eixos_cols:
            df_eixo = df_aggregated[df_aggregated[eixo] > 0].copy()
            if df_eixo.empty:
                continue

            table_html = f"""
<h4>Eixo: {html.escape(eixo)}</h4>
<table>
<thead>
<tr><th>Unidade</th><th>Ação</th><th style="text-align:right;">Valor {html.escape(eixo)}</th></tr>
</thead>
<tbody>
"""
            total_eixo = 0.0
            for _, row_ in df_eixo.iterrows():
                unidade = html.escape(str(row_["Unidade"]))
                acao = html.escape(str(row_["Acao"]))
                valor_eixo = float(row_[eixo])
                total_eixo += valor_eixo
                valor_formatado = format_float_br(str(valor_eixo))
                table_html += f"""
<tr><td>{unidade}</td><td>{acao}</td><td style="text-align:right;">{valor_formatado}</td></tr>
"""
            table_html += "</tbody></table>"
            soma_por_eixo[eixo] = total_eixo
            total_eixo_str = format_float_br(str(total_eixo))
            html_output += table_html + f"<p><strong>Total do Eixo</strong>: {total_eixo_str}</p><hr>"

        if soma_por_eixo:
            html_output += "<h4>Resumo por Eixo</h4>"
            table_resumo = """
<table>
<thead>
<tr><th>Eixo</th><th style="text-align:right;">Valor Total</th></tr>
</thead>
<tbody>
"""
            for eixo_nome, valor_total in sorted(soma_por_eixo.items(), key=lambda x: x[0]):
                valor_total_str = format_float_br(str(valor_total))
                table_resumo += f"<tr><td>{html.escape(eixo_nome)}</td><td style='text-align:right;'>{valor_total_str}</td></tr>"
            table_resumo += "</tbody></table>"
            html_output += table_resumo

        return html_output
    except Exception as e:
        return f"<p>Erro ao gerar distribuição: {html.escape(str(e))}</p>"

LABEL_MAP = {
    "diretoria": "Diretoria Responsável",
    "coordenacao_geral": "Coordenação Geral",
    "coordenacao": "Coordenação",
    "demandante": "Setor Demandante"
}

def format_demais_informacoes(json_str: str) -> str:
    """Formata 'Demais Informações' para exibir apenas dados do usuário responsável."""
    try:
        data = json.loads(json_str)
    except:
        return "<p>Erro ao carregar informações.</p>"

    if not data:
        return "<p>Sem informações adicionais.</p>"

    # Ajuste para exibir apenas Diretoria e Usuário Responsável
    html_list = "<ul>"
    html_list += f"<li><strong>📌 Diretoria:</strong> {html.escape(str(data.get('diretoria', 'Não informado')))}</li>"
    html_list += f"<li><strong>👤 Usuário Responsável:</strong> {html.escape(str(data.get('usuario_nome', 'Não informado')))}</li>"
    html_list += f"<li><strong>📧 E-mail:</strong> {html.escape(str(data.get('usuario_email', 'Não informado')))}</li>"
    html_list += f"<li><strong>🔰 Perfil:</strong> {html.escape(str(data.get('perfil', 'Não informado')))}</li>"
    html_list += "</ul>"

    return html_list

###############################################################################
#       4. SELEÇÃO DE INICIATIVA E EXIBIÇÃO NA INTERFACE (HTML)              #
###############################################################################
perfil_usuario = st.session_state.get("perfil", "")
setor_usuario  = st.session_state.get("setor", "")

df_iniciativas = load_iniciativas(setor_usuario, perfil_usuario)
if df_iniciativas.empty:
    st.info("ℹ️ Nenhuma iniciativa encontrada para o seu setor.")
    st.stop()

nomes_iniciativas = df_iniciativas['nome_iniciativa'].unique().tolist()
iniciativa_selecionada = st.selectbox("Selecione a iniciativa", nomes_iniciativas)
df_filtrado = df_iniciativas[df_iniciativas['nome_iniciativa'] == iniciativa_selecionada]

# CSS para layout original no Streamlit
card_css = """
<style>
.card-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(650px, 1fr));
    gap: 25px;
    padding: 20px;
}
.card {
    background: #ffffff;
    border-radius: 15px;
    padding: 25px;
    color: #333;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border-left: 5px solid #00d1b2;
}
.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
}
.card h3 {
    margin-top: 0;
    font-size: 1.8rem;
    color: #00d1b2;
}
.card-section {
    margin-bottom: 15px;
    padding: 12px;
    background: #f9f9f9;
    border-radius: 8px;
}
.card-section-title {
    font-weight: 600;
    color: #00d1b2;
    margin-bottom: 8px;
    font-size: 1.1rem;
}
.badge {
    background: #00d1b233;
    color: #00d1b2;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    margin-right: 10px;
}
table {
    width: 100%;
    border-collapse: collapse;
}
table, th, td {
    border: 1px solid #ddd;
    padding: 8px;
}
th {
    background-color: #00d1b2;
    color: white;
}
</style>
"""
st.markdown(card_css, unsafe_allow_html=True)

# Exibe os cards HTML na interface
st.markdown("<div class='card-container'>", unsafe_allow_html=True)
for _, row in df_filtrado.iterrows():
    nome_iniciativa  = safe_html(row.get('nome_iniciativa', ''))
    objetivo_geral   = safe_html(row.get('objetivo_geral', ''))
    introducao       = safe_html(row.get('introducao', ''))
    justificativa    = safe_html(row.get('justificativa', ''))
    metodologia      = safe_html(row.get('metodologia', ''))
    responsavel      = safe_html(row.get('usuario', ''))

    objetivos_especificos = format_objetivos_especificos(row.get('objetivos_especificos', '') or '')
    eixos_tematicos       = format_eixos_tematicos_table(row.get('eixos_tematicos', '') or '')
    insumos               = format_insumos(row.get('insumos', '') or '')
    distribuicao_ucs      = format_distribuicao_ucs(row.get('distribuicao_ucs', '') or '')
    distribuicao_ucs_eixo = format_distribuicao_por_eixo(row.get('distribuicao_ucs', '') or '')
    formas_contratacao    = format_formas_contratacao(row.get('formas_contratacao', '') or '')
    demais_informacoes    = format_demais_informacoes(row.get('demais_informacoes', '') or '')

    data_hora_str = row.get('data_hora')
    if data_hora_str:
        data_hora_fmt = datetime.strptime(data_hora_str, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
    else:
        data_hora_fmt = "(sem data)"

    card_html = f"""
    <div class="card">
        <div class="card-section">
            <h3>{nome_iniciativa}</h3>
        </div>
        <div class="card-section">
            <div class="card-section-title">Objetivo Geral</div>
            {objetivo_geral}
        </div>
        <div class="card-section">
            <div class="card-section-title">Objetivos Específicos</div>
            {objetivos_especificos}
        </div>
        <div class="card-section">
            <div class="card-section-title">Introdução</div>
            {introducao}
        </div>
        <div class="card-section">
            <div class="card-section-title">Justificativa</div>
            {justificativa}
        </div>
        <div class="card-section">
            <div class="card-section-title">Metodologia</div>
            {metodologia}
        </div>
        <div class="card-section">
            <div class="card-section-title">Eixos Temáticos</div>
            {eixos_tematicos}
        </div>
        <div class="card-section">
            <div class="card-section-title">Lista de Insumos Selecionados</div>
            {insumos}
        </div>
        <div class="card-section">
            <div class="card-section-title">Distribuição por Unidade</div>
            {distribuicao_ucs}
        </div>
        <div class="card-section">
            <div class="card-section-title">Distribuição por Unidade / Eixo</div>
            {distribuicao_ucs_eixo}
        </div>
        <div class="card-section">
            <div class="card-section-title">Formas de Contratação</div>
            {formas_contratacao}
        </div>
        <div class="card-section">
            <div class="card-section-title">Demais Informações</div>
            {demais_informacoes}
        </div>
        <div style="margin-top: 15px;">
            <span class="badge">Responsável: {responsavel}</span>
            <span class="badge">Data/Hora: {data_hora_fmt}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

###############################################################################
#  5. ABORDAGEM XHTML2PDF COM HTML SIMPLIFICADO (PRETO E BRANCO, SEÇÕES)      #
###############################################################################
def generate_html_for_iniciativas(df: pd.DataFrame) -> str:
    minimal_css = """
    <style>
    body {
        font-family: Arial, sans-serif;
        color: #000;
        font-size: 12px;
        margin: 20px;
    }
    h2, h3, h4 {
        color: #000;
        margin-bottom: 8px;
        margin-top: 20px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 15px;
    }
    table, th, td {
        border: 1px solid #000;
        padding: 5px;
        vertical-align: top;
    }
    th {
        background-color: #eee;
    }
    ul {
        margin-bottom: 15px;
        padding-left: 20px;
    }
    .section-title {
        font-weight: bold;
        margin: 10px 0 5px 0;
    }
    .subtitle {
        font-weight: bold;
        margin: 5px 0;
    }
    hr {
        margin: 20px 0;
    }
    </style>
    """

    html_out = f"""
    <html>
    <head>
        <meta charset="utf-8"/>
        {minimal_css}
    </head>
    <body>
    <h2>Relatório de Iniciativas e Regras de Negócio</h2>
    """

    for _, row in df.iterrows():
        nome_iniciativa  = safe_html(row.get('nome_iniciativa', ''))
        objetivo_geral   = safe_html(row.get('objetivo_geral', ''))
        introducao       = safe_html(row.get('introducao', ''))
        justificativa    = safe_html(row.get('justificativa', ''))
        metodologia      = safe_html(row.get('metodologia', ''))
        responsavel      = safe_html(row.get('usuario', ''))

        objetivos_especificos = format_objetivos_especificos(row.get('objetivos_especificos', '') or '')
        eixos_tematicos       = format_eixos_tematicos_table(row.get('eixos_tematicos', '') or '')
        insumos               = format_insumos(row.get('insumos', '') or '')
        distrib_ucs           = format_distribuicao_ucs(row.get('distribuicao_ucs', '') or '')
        distrib_ucs_eixo      = format_distribuicao_por_eixo(row.get('distribuicao_ucs', '') or '')
        formas_contratacao    = format_formas_contratacao(row.get('formas_contratacao', '') or '')
        demais_informacoes    = format_demais_informacoes(row.get('demais_informacoes', '') or '')

        data_hora_str = row.get('data_hora')
        if data_hora_str:
            data_hora_fmt = datetime.strptime(data_hora_str, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        else:
            data_hora_fmt = "(sem data)"

        html_out += f"""
        <hr/>
        <h3>Iniciativa: {nome_iniciativa}</h3>

        <div class="section-title">Objetivo Geral</div>
        <p>{objetivo_geral}</p>

        <div class="section-title">Objetivos Específicos</div>
        {objetivos_especificos}

        <div class="section-title">Introdução</div>
        <p>{introducao}</p>

        <div class="section-title">Justificativa</div>
        <p>{justificativa}</p>

        <div class="section-title">Metodologia</div>
        <p>{metodologia}</p>

        <div class="section-title">Eixos Temáticos</div>
        {eixos_tematicos}

        <div class="section-title">Insumos</div>
        <p>{insumos}</p>

        <div class="section-title">Distribuição por Unidade</div>
        {distrib_ucs}

        <div class="section-title">Distribuição por Unidade / Eixo</div>
        {distrib_ucs_eixo}

        <div class="section-title">Formas de Contratação</div>
        {formas_contratacao}

        <div class="section-title">Demais Informações</div>
        {demais_informacoes}

        <p><strong>Responsável:</strong> {responsavel} |
           <strong>Data/Hora:</strong> {data_hora_fmt}</p>
        """

    html_out += """
    </body>
    </html>
    """
    return html_out

def create_pdf_from_html(html_string: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name
    temp_file.close()

    pisa_status = pisa.CreatePDF(
        src=html_string,
        dest=open(pdf_path, "wb"),
        encoding='utf-8'
    )
    if pisa_status.err:
        raise ValueError("Erro ao gerar PDF com xhtml2pdf")

    return pdf_path

def create_pdf_bytes(html_string: str) -> bytes:
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        src=html_string,
        dest=pdf_buffer,
        encoding='utf-8'
    )
    if pisa_status.err:
        st.error("Erro ao gerar PDF com xhtml2pdf")
        st.write(pisa_status.log)
        raise ValueError("Erro ao gerar PDF com xhtml2pdf")

    pdf_data = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_data

###############################################################################
#  6. GERAR EXCEL COM MÚLTIPLAS ABAS                                          #
###############################################################################
def parse_eixos_tematicos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte a coluna 'eixos_tematicos' (JSON) em um DataFrame tabular:
    id_iniciativa, nome_iniciativa, nome_eixo, acao_id, acao_nome, insumo_id, insumo_nome
    """
    rows = []
    for _, row in df.iterrows():
        eixos_json = row.get('eixos_tematicos', '')
        nome_ini = row.get('nome_iniciativa', '')
        id_ini   = row.get('id_iniciativa', '')
        try:
            data = json.loads(eixos_json)
            for eixo in data:
                nome_eixo = eixo.get("nome_eixo", "")
                acoes = eixo.get("acoes_manejo", {})
                if not acoes:
                    rows.append({
                        "id_iniciativa": id_ini,
                        "nome_iniciativa": nome_ini,
                        "nome_eixo": nome_eixo,
                        "acao_id": None,
                        "acao_nome": None,
                        "insumo_id": None,
                        "insumo_nome": None
                    })
                else:
                    for acao_id, detalhes in acoes.items():
                        nome_acao = acoes_map.get(str(acao_id), f"Ação {acao_id}")
                        insumos_list = detalhes.get("insumos", [])
                        if insumos_list:
                            for ins_id in insumos_list:
                                rows.append({
                                    "id_iniciativa": id_ini,
                                    "nome_iniciativa": nome_ini,
                                    "nome_eixo": nome_eixo,
                                    "acao_id": acao_id,
                                    "acao_nome": nome_acao,
                                    "insumo_id": ins_id,
                                    "insumo_nome": insumos_map.get(str(ins_id), str(ins_id))
                                })
                        else:
                            rows.append({
                                "id_iniciativa": id_ini,
                                "nome_iniciativa": nome_ini,
                                "nome_eixo": nome_eixo,
                                "acao_id": acao_id,
                                "acao_nome": nome_acao,
                                "insumo_id": None,
                                "insumo_nome": None
                            })
        except:
            pass

    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=[
            "id_iniciativa","nome_iniciativa","nome_eixo","acao_id","acao_nome","insumo_id","insumo_nome"
        ])

def parse_distribuicao_ucs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte a coluna 'distribuicao_ucs' (JSON) em um DataFrame tabular:
    id_iniciativa, nome_iniciativa, Unidade, Acao, Valor Alocado
    """
    rows = []
    for _, row in df.iterrows():
        dist_json = row.get('distribuicao_ucs', '')
        nome_ini = row.get('nome_iniciativa', '')
        id_ini   = row.get('id_iniciativa', '')
        try:
            data = json.loads(dist_json)
            if isinstance(data, list):
                for item in data:
                    new_row = {
                        "id_iniciativa": id_ini,
                        "nome_iniciativa": nome_ini,
                        "Unidade": item.get("Unidade", ""),
                        "Acao": item.get("Acao", ""),
                        "Valor Alocado": item.get("Valor Alocado", 0)
                    }
                    rows.append(new_row)
        except:
            pass

    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=[
            "id_iniciativa","nome_iniciativa","Unidade","Acao","Valor Alocado"
        ])

def parse_formas_contratacao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte a coluna 'formas_contratacao' (JSON) em um DataFrame simples:
    Uma linha por forma de contratação selecionada, com possíveis detalhes.
    """
    rows = []
    for _, row in df.iterrows():
        nome_ini = row.get('nome_iniciativa', '')
        id_ini   = row.get('id_iniciativa', '')
        formas_json = row.get('formas_contratacao', '')
        try:
            data = json.loads(formas_json)
            tabela_formas = data.get("tabela_formas", [])
            for item in tabela_formas:
                forma = item.get("Forma de Contratação", "Sem descrição")
                selecionado = item.get("Selecionado", False)
                rows.append({
                    "id_iniciativa": id_ini,
                    "nome_iniciativa": nome_ini,
                    "Forma de Contratação": forma,
                    "Selecionado": selecionado
                })
        except:
            pass

    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=[
            "id_iniciativa","nome_iniciativa","Forma de Contratação","Selecionado"
        ])

def parse_iniciativas_principal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna um subset de colunas principais do df_filtrado (sem JSON).
    """
    cols = [
        "id_iniciativa","nome_iniciativa","usuario","objetivo_geral",
        "introducao","justificativa","metodologia","data_hora"
    ]
    subset = df[cols].copy()
    return subset

def gerar_excel_por_abas(df: pd.DataFrame) -> bytes:
    """
    Converte df_filtrado em várias abas:
      1) Iniciativas (dados principais)
      2) EixosTematicos
      3) DistribuicaoUCs
      4) FormasContratacao
    Retorna os bytes do arquivo Excel.
    """
    df_iniciativas_main = parse_iniciativas_principal(df)
    df_eixos            = parse_eixos_tematicos(df)
    df_distrib          = parse_distribuicao_ucs(df)
    df_formas           = parse_formas_contratacao(df)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_iniciativas_main.to_excel(writer, index=False, sheet_name="Iniciativas")
        df_eixos.to_excel(writer, index=False, sheet_name="EixosTematicos")
        df_distrib.to_excel(writer, index=False, sheet_name="DistribuicaoUCs")
        df_formas.to_excel(writer, index=False, sheet_name="FormasContratacao")
    return output.getvalue()

###############################################################################
#  7. BOTÕES: GERAR EXCEL E GERAR PDF                                          #
###############################################################################
if st.button("📥 Gerar Excel "):
    with st.spinner("Gerando arquivo Excel..."):
        excel_bytes = gerar_excel_por_abas(df_filtrado)
    st.download_button(
        label="Download Excel",
        data=excel_bytes,
        file_name=f"iniciativas_{iniciativa_selecionada}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.button("📄 Gerar Extrato Completo em PDF"):
    with st.spinner("Gerando Extrato em PDF..."):
        html_content = generate_html_for_iniciativas(df_filtrado)
        try:
            pdf_bytes = create_pdf_bytes(html_content)
        except ValueError as e:
            st.error(f"Ocorreu um erro ao gerar o PDF: {e}")
            st.stop()

        st.download_button(
            label="⬇️ Download do Extrato (PDF)",
            data=pdf_bytes,
            file_name=f"extrato_iniciativa_{iniciativa_selecionada}.pdf",
            mime="application/pdf"
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            temp_pdf_path = tmp.name
        pdf_viewer(temp_pdf_path)
