FROM python:3.12-slim

# 2. Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar o resto do código da aplicação
COPY . .

# 5. Comando para executar a aplicação
# O Cloud Run injeta a variável $PORT. O Uvicorn usará por padrão a porta 8080 se a variável não estiver presente.
# O host 0.0.0.0 é essencial para aceitar conexões de fora do contêiner.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]