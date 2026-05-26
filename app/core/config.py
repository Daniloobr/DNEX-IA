import os
from pathlib import Path
from typing import Set
from dotenv import load_dotenv

# Define o diretório base do projeto
DIRETORIO_BASE: Path = Path(__file__).resolve().parent.parent.parent

# Carrega as variáveis do arquivo .env usando o caminho absoluto
load_dotenv(dotenv_path=DIRETORIO_BASE / ".env")

class Configuracao:
    """
    Centraliza todas as configurações do sistema Dnex IA.
    Aqui definimos caminhos de pastas, limites de tamanho e modelos.
    """
    # Define o diretório base do projeto
    DIRETORIO_BASE: Path = DIRETORIO_BASE
    
    # Pastas de trabalho
    PASTA_UPLOADS: Path = DIRETORIO_BASE / "uploads"
    PASTA_SAIDA: Path = DIRETORIO_BASE / "outputs"
    
    # Regras de arquivo
    EXTENSOES_PERMITIDAS: Set[str] = {"mp4", "mov", "avi", "mkv", "webm"}
    TAMANHO_MAXIMO_ARQUIVO: int = int(os.getenv("MAX_CONTENT_LENGTH", 2048 * 1024 * 1024))
    
    # Configurações do Motor de IA (Whisper)
    TAMANHO_MODELO_WHISPER: str = os.getenv("WHISPER_MODEL_SIZE", "tiny")
    DISPOSITIVO_IA: str = os.getenv("WHISPER_DEVICE", "cpu")
    TIPO_COMPUTACAO: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # Configurações de performance (transcrição paralela com chunks)
    MAX_WORKERS_PARALELOS: int = int(os.getenv("MAX_WORKERS_PARALELOS", "4"))
    PASTA_CACHE: Path = DIRETORIO_BASE / "cache_transcricao"
    
    @classmethod
    def inicializar_pastas(cls):
        """Cria as pastas de upload, saída e cache se elas não existirem."""
        cls.PASTA_UPLOADS.mkdir(exist_ok=True, parents=True)
        cls.PASTA_SAIDA.mkdir(exist_ok=True, parents=True)
        cls.PASTA_CACHE.mkdir(exist_ok=True, parents=True)

# Instância global de configuração
config = Configuracao()
