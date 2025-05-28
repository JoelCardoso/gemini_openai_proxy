# Proxy Gemini para OpenAI API

Este projeto é um proxy que expõe a API do Google Gemini através de uma interface compatível com a API OpenAI `/v1/chat/completions`.
Ele permite que aplicações clientes que esperam a API da OpenAI interajam com o Gemini.

## Funcionalidades

- Endpoint `/v1/chat/completions` compatível.
- Suporte para respostas normais (JSON) e streaming (`text/event-stream`).
- Configuração via variáveis de ambiente.
- Utiliza a biblioteca `gemini-webapi` para interagir com o Gemini.

## Configuração

1.  **Clone o repositório (ou crie os arquivos conforme a estrutura).**
2.  **Instale `uv`**: Siga as [instruções oficiais](https://github.com/astral-sh/uv).
3.  **Crie e ative um ambiente virtual:**
    ```bash
    uv venv
    source .venv/bin/activate  # ou .\.venv\Scripts\activate no Windows
    ```
4.  **Instale as dependências:**
    ```bash
    uv pip sync
    ```
5.  **Configure as variáveis de ambiente:**
    Copie `.env.example` para `.env` e preencha os valores:
    ```bash
    cp .env.example .env
    # Edite .env com seus cookies Gemini
    ```
    - `GEMINI_SECURE_1PSID`: Seu cookie __Secure-1PSID do Google.
    - `GEMINI_SECURE_1PSIDTS`: Seu cookie __Secure-1PSIDTS do Google (opcional).

## Uso

Para iniciar o servidor de desenvolvimento:

```bash
uv run start
