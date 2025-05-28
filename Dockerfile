FROM python:3.12-slim

# Instala dependências do sistema (ajuste conforme necessário)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY app ./app

# Cria diretório de logs com permissão de escrita
RUN mkdir -p /app/logs

# Expõe a porta padrão do FastAPI/Uvicorn
EXPOSE 8000

# Comando para rodar o servidor FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]