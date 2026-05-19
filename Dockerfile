# Usa uma imagem oficial do Python leve
FROM python:3.10-slim

# Instala dependências do sistema (FFmpeg é essencial!)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho dentro do servidor
WORKDIR /app

# Copia os arquivos de dependências primeiro (otimiza o cache)
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Gunicorn (servidor de produção para Python)
RUN pip install gunicorn

# Copia todo o resto do projeto
COPY . .

# Cria as pastas necessárias
RUN mkdir -p uploads outputs models

# Expõe a porta que o Flask vai usar
EXPOSE 5000

# Comando para iniciar o servidor em modo de produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "main:app"]
