import shutil
import subprocess
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class ErroFFmpeg(Exception):
    """Exceção específica para problemas com o motor FFmpeg."""
    pass

def localizar_caminho_ffmpeg() -> str:
    """
    Busca o FFmpeg no sistema, incluindo pastas padrão do Windows e WinGet.
    """
    # 1. Tenta o comando padrão do sistema
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    
    # 2. Busca em pastas conhecidas do WinGet
    dados_locais = os.getenv("LOCALAPPDATA", "")
    if dados_locais:
        base_winget = Path(dados_locais) / "Microsoft" / "WinGet" / "Packages"
        if base_winget.exists():
            encontrados = list(base_winget.glob("**/bin/ffmpeg.exe"))
            if encontrados:
                return str(encontrados[0])

    return ""

def executar_comando(comando: List[str]) -> str:
    """
    Executa uma tarefa no FFmpeg e gerencia o resultado.
    """
    executavel = localizar_caminho_ffmpeg()
    if not executavel:
        raise ErroFFmpeg("FFmpeg não foi detectado no seu computador.")
    
    # Ajusta o comando para usar o caminho completo se necessário
    if comando[0] == "ffmpeg":
        comando[0] = executavel

    try:
        logger.debug(f"🎬 Executando: {' '.join(comando)}")
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        return resultado.stdout
    except subprocess.CalledProcessError as e:
        erro = e.stderr.strip() or str(e)
        logger.error(f"❌ Erro FFmpeg: {erro}")
        raise ErroFFmpeg(f"Falha ao processar vídeo: {erro}")

def extrair_audio_mp3(caminho_entrada: Path, caminho_saida: Path):
    """Extrai o som do vídeo em formato MP3 de alta qualidade."""
    comando = [
        "ffmpeg", "-y",
        "-i", str(caminho_entrada),
        "-vn", # Remove o vídeo
        "-codec:a", "libmp3lame",
        "-q:a", "2", # Qualidade alta
        str(caminho_saida)
    ]
    executar_comando(comando)

def extrair_audio_wav_para_ia(caminho_entrada: Path, caminho_saida: Path):
    """Prepara o áudio no formato ideal para a Inteligência Artificial (16kHz, Mono)."""
    comando = [
        "ffmpeg", "-y",
        "-i", str(caminho_entrada),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000", # Frequência exigida pelo Whisper
        "-ac", "1", # Canal único (mono)
        str(caminho_saida)
    ]
    executar_comando(comando)
