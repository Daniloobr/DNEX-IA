import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from app.core.config import config

def arquivo_permitido(nome_arquivo: str) -> bool:
    """Valida se a extensão do arquivo enviado é suportada pelo Dnex IA."""
    return "." in nome_arquivo and \
           nome_arquivo.rsplit(".", 1)[1].lower() in config.EXTENSOES_PERMITIDAS

def gerar_nome_unico(nome_original: str, sufixo: str = None) -> str:
    """
    Cria um nome de arquivo seguro e único para evitar conflitos.
    Exemplo: video_da_praia_a1b2c3d4.mp3
    """
    caminho_limpo = Path(secure_filename(nome_original))
    nome_base = caminho_limpo.stem[:50]  # Mantém os primeiros 50 caracteres
    extensao = sufixo if sufixo else caminho_limpo.suffix
    return f"{nome_base}_{uuid.uuid4().hex}{extensao}"

def formatar_tempo(segundos: float) -> str:
    """
    Converte segundos puros para o formato de relógio legível.
    Exemplo: 00:01:30.500
    """
    milisegundos = int((segundos - int(segundos)) * 1000)
    segundos = int(segundos)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segs:02d}.{milisegundos:03d}"

def limpar_arquivos_antigos(diretorio: Path, horas: int = 24):
    """
    Remove arquivos que foram criados há mais de X horas.
    Mantém o servidor limpo e respeita a privacidade.
    """
    import time
    agora = time.time()
    limite = horas * 3600
    
    for arquivo in diretorio.glob("*"):
        if arquivo.name == ".gitkeep": continue
        if arquivo.is_file():
            idade = agora - arquivo.stat().st_mtime
            if idade > limite:
                try:
                    arquivo.unlink()
                except Exception:
                    pass
