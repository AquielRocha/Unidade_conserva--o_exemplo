# Usando uma imagem base do Python
FROM python:3.9

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar os arquivos do projeto para dentro do container
COPY . /app

# Instalar dependências
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expor a porta usada pelo Streamlit
EXPOSE 8501

# Comando para rodar a aplicação
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
