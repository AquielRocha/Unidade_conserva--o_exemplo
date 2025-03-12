# **README - Sistema de Cadastro de Regras de Negócio**

Este repositório contém o código-fonte de um sistema desenvolvido em **Streamlit** que permite gerenciar **regras de negócio** relacionadas a **iniciativas** de um determinado órgão/setor. O sistema possibilita que usuários previamente autenticados realizem:

- Edição e registro de **Objetivos Geral e Específicos**;
- Cadastro e vinculação de **Eixos Temáticos** e **Ações de Manejo**;
- Seleção e distribuição de **Insumos** para cada ação;
- Detalhamento e distribuição de recursos em **Unidades de Conservação**;
- Registro de **Formas de Contratação** associadas aos itens e serviços necessários;
- Visualização de **Informações Originais** (resumos) oriundas de documentos SEI.

---

## **Sumário**

1. [Características Principais](#características-principais)  
2. [Estrutura dos Arquivos](#estrutura-dos-arquivos)  
3. [Pré-Requisitos e Instalação](#pré-requisitos-e-instalação)  
4. [Como Executar](#como-executar)  
5. [Fluxo de Uso](#fluxo-de-uso)  
6. [Detalhes de Funcionamento](#detalhes-de-funcionamento)  
7. [Contribuindo](#contribuindo)  
8. [Licença](#licença)

---

## **Características Principais**

- **Autenticação e Controle de Acesso**  
  Somente usuários logados podem acessar o sistema. Caso o usuário não esteja autenticado, uma mensagem de aviso é exibida e o fluxo é interrompido.

- **Cadastro de Objetivos**  
  O usuário pode adicionar ou editar o **Objetivo Geral** e vários **Objetivos Específicos** para cada iniciativa.  
  - Há recursos para inserir novos objetivos e para editar ou remover objetivos existentes.

- **Eixos Temáticos e Ações de Manejo**  
  Cada iniciativa pode ter vinculados vários **Eixos Temáticos** (processos SAMGe), e cada eixo pode conter um conjunto de **Ações de Manejo**.  
  - Essas ações podem ser consultadas de uma tabela referencial (ex.: `td_samge_acoes_manejo`).

- **Seleção de Insumos**  
  Para cada ação de manejo, o sistema permite selecionar os **insumos** necessários, filtrando por **elemento de despesa** e **especificação padrão**.  
  - A seleção é armazenada e consolidada para cada ação, permitindo ao usuário revisar e salvar suas escolhas.

- **Distribuição de Recursos em Unidades de Conservação**  
  O sistema exibe valores previamente cadastrados para as Unidades de Conservação e possibilita que o usuário distribua o valor total alocado entre diferentes eixos, facilitando o planejamento.

- **Formas de Contratação**  
  O usuário pode indicar **como** serão contratados os serviços/insumos (p. ex., Contrato Caixa, Contrato ICMBio, Fundação de Apoio credenciada, etc.) e registrar justificativas ou detalhes adicionais.

- **Histórico de Alterações**  
  Há um mecanismo para **limitar a 3 versões** de histórico na tabela principal (`tf_cadastro_regras_negocio`). Cada novo registro substitui o mais antigo, caso atinja-se o limite.

- **Visualização de Resumos Originais**  
  Ao final da página, é possível **consultar** as informações originais do **Resumo Executivo** (documentos SEI), caso existam, para auxiliar no preenchimento dos campos.

---

## **Estrutura dos Arquivos**

- **`main.py`**  
  Arquivo com o código principal (pode ter outro nome, dependendo do seu projeto). Nele estão:
  - Configuração da página (`streamlit.set_page_config`)
  - Declarações de funções auxiliares e queries para o banco de dados
  - Estrutura de formulários, abas (tabs) e data_editor para edição

- **`database/app_data.db`**  
  Banco de dados SQLite onde ficam salvos:
  - As tabelas de iniciativas, demandantes, insumos, eixos, ações de manejo etc.
  - A tabela de cadastro de regras de negócio (`tf_cadastro_regras_negocio`)

- **Outros arquivos**  
  - Podem existir scripts SQL de criação de tabelas ou arquivos auxiliares.

---

## **Pré-Requisitos e Instalação**

1. **Python 3.9+** (recomendado)
2. Bibliotecas necessárias (listadas a seguir) devem estar instaladas:
   - [Streamlit](https://streamlit.io/)  
   - [sqlite3](https://docs.python.org/3/library/sqlite3.html) (já incluída na biblioteca padrão do Python)  
   - [pandas](https://pandas.pydata.org/)  
   - [json](https://docs.python.org/3/library/json.html) (padrão do Python)
   - [time](https://docs.python.org/3/library/time.html) (padrão do Python)

Para instalar as dependências adicionais (caso haja um arquivo `requirements.txt`), execute:

```bash
pip install -r requirements.txt
```

Caso contrário, instale manualmente:

```bash
pip install streamlit pandas
```

---

## **Como Executar**

1. **Clonar** ou **baixar** este repositório.
2. **Acessar** a pasta do projeto via terminal.
3. Certifique-se de ter o `Python` instalado e um ambiente virtual ativo (opcional).
4. Execute:
   ```bash
   streamlit run main.py
   ```
   *(supondo que seu arquivo principal se chame `main.py`; caso tenha outro nome, ajuste o comando.)*

5. A aplicação abrirá no navegador padrão, geralmente em `http://localhost:8501`.

---

## **Fluxo de Uso**

1. **Login**  
   - O usuário realiza login e, caso autenticado, é redirecionado à aplicação.
   - Se `st.session_state["usuario_logado"]` for `False` ou não existir, o sistema impede o acesso.

2. **Seleção de Iniciativa**  
   - O usuário escolhe a iniciativa disponível (dependendo do seu `perfil` e `setor`).

3. **Edição / Cadastro das Regras**  
   - **Objetivo Geral e Específicos:** pode adicionar, editar ou remover objetivos.  
   - **Texto de Introdução, Justificativa e Metodologia:** campos de texto livre.
   - **Eixos Temáticos e Ações de Manejo:** permite adicionar e remover eixos, e selecionar ações associadas a cada eixo.
   - **Seleção de Insumos:** para cada ação, é possível escolher insumos de uma lista mesclada via data_editor, com filtros de Elemento de Despesa e Especificação Padrão.
   - **Distribuição de Recursos (Unidades de Conservação):** editar valores já existentes para alocação em cada eixo.
   - **Formas de Contratação:** indicar que tipos de contratos e instituições serão utilizados, detalhando informações complementares (justificativas, número de SEI, etc.).

4. **Salvar/Atualizar**  
   - Ao concluir a edição, o usuário pode clicar em **“Salvar Alterações”** para armazenar tudo no `session_state`.
   - Por fim, ao clicar em **“Finalizar Cadastro”**, as informações são efetivamente **gravadas** (INSERT) na tabela `tf_cadastro_regras_negocio`.

5. **Visualização de Resumos Originais**  
   - Ao final, o usuário pode consultar as informações de **resumo executivo** (diretoria, coordenações, etc.) caso existam no BD (`td_dados_resumos_sei`).

---

## **Detalhes de Funcionamento**

- **Banco de Dados**  
  O sistema utiliza um **SQLite** (`app_data.db`). O caminho está definido na variável `DB_PATH`.  
  É possível modificar esse caminho conforme necessário.

- **Cache de Consultas**  
  Algumas funções são decoradas com `@st.cache_data` para melhorar a performance e evitar leitura repetitiva do banco.

- **Histórico de Registros**  
  A função `salvar_dados_iniciativa()` mantém no máximo **3** versões de cadastro por iniciativa. Se houver mais que 3, o registro mais antigo é excluído.

- **Armazenamento em JSON**  
  Itens como **objetivos específicos**, **eixos temáticos**, **ações de manejo** e **insumos** são armazenados em formato **JSON** no BD, permitindo flexibilidade de dados.

- **Session State**  
  Várias variáveis são persistidas no `st.session_state`, garantindo que mudanças não sejam perdidas enquanto o usuário navega pelas abas.

---

## **Contribuindo**

1. Faça um **fork** do projeto.
2. Crie um branch para sua feature (`git checkout -b feature/nova-funcionalidade`).
3. Faça o commit das alterações (`git commit -m 'Minha nova funcionalidade'`).
4. Faça o push para o branch (`git push origin feature/nova-funcionalidade`).
5. Abra um **Pull Request** no repositório original.

---

## **Licença**

Este projeto pode ser disponibilizado sob os termos de licença de sua instituição ou organização.  
*(Caso queira definir uma licença aberta, utilize alguma das [licenças recomendadas](https://choosealicense.com/).)*

---  

### **Contato**

Em caso de dúvidas ou sugestões, entre em contato com o(s) mantenedor(es) do projeto.  
