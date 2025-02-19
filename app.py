import streamlit as st

st.set_page_config(page_title="Gestão de Processos", layout="wide")

# CSS para ocultar apenas o item da página principal no sidebar
hide_home_style = """
<style>
/* 
  Cada item de página no menu aparece como um <li> dentro de [data-testid="stSidebarNav"] ul.
  Normalmente, o app principal (este arquivo) é o primeiro item (nth-child(1)).
  A página "Gerenciamento" aparece depois.
*/
[data-testid="stSidebarNav"] ul li:nth-child(1) {
    display: none;
}
</style>
"""
st.markdown(hide_home_style, unsafe_allow_html=True)

st.title("Processos")

