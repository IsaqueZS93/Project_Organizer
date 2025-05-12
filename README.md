# Project Organizer

Sistema de gerenciamento de projetos e contratos desenvolvido em Python com interface Streamlit.

## Funcionalidades

- Gerenciamento de contratos
- Gerenciamento de projetos
- Gerenciamento de usuários
- Integração com Google Drive
- Interface web responsiva

## Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`

## Configuração

1. Crie um arquivo `.env` na raiz do projeto
2. Configure as variáveis de ambiente necessárias:
   - `GOOGLE_DRIVE_CREDENTIALS`: ID da pasta no Google Drive onde estão as credenciais

## Execução

1. Ative o ambiente virtual
2. Execute o comando: `streamlit run main.py`

## Estrutura do Projeto

```
Project_Organizer/
├── backend/
│   ├── Database/
│   ├── Models/
│   └── Services/
├── frontend/
│   └── Screens/
├── venv/
├── .env
├── main.py
└── requirements.txt
``` 