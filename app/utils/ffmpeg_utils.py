import shutil
import subprocess
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class ErroFFmpeg(Exception):
    """Exceção específica para problemas com o motor FFmpeg."""
    pass


def localizar_caminho_ffmpeg() -> str:
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    dados_locais = os.getenv("LOCALAPPDATA", "")
    if dados_locais:
        base_winget = Path(dados_locais) / "Microsoft" / "WinGet" / "Packages"
        if base_winget.exists():
            encontrados = list(base_winget.glob("**/bin/ffmpeg.exe"))
            if encontrados:
                return str(encontrados[0])
    return ""


def localizar_caminho_ffprobe() -> str:
    caminho = shutil.which("ffprobe")
    if caminho:
        return caminho
    dados_locais = os.getenv("LOCALAPPDATA", "")
    if dados_locais:
        base_winget = Path(dados_locais) / "Microsoft" / "WinGet" / "Packages"
        if base_winget.exists():
            encontrados = list(base_winget.glob("**/bin/ffprobe.exe"))
            if encontrados:
                return str(encontrados[0])
    executavel = localizar_caminho_ffmpeg()
    if executavel and "ffmpeg" in executavel:
        return executavel.replace("ffmpeg", "ffprobe")
    return ""


def _montar_comando(comando: List[str]) -> List[str]:
    executavel = localizar_caminho_ffmpeg()
    if not executavel:
        raise ErroFFmpeg("FFmpeg não foi detectado no seu computador.")
    if comando[0] == "ffmpeg":
        comando[0] = executavel
    return comando


def executar_comando(comando: List[str]) -> str:
    executavel = localizar_caminho_ffmpeg()
    if not executavel:
        raise ErroFFmpeg("FFmpeg não foi detectado no seu computador.")
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


def obter_duracao(caminho_arquivo: Path) -> float:
    """Retorna a duração em segundos de um arquivo de mídia usando ffprobe."""
    executavel = localizar_caminho_ffprobe()
    if not executavel:
        raise ErroFFmpeg("FFprobe não foi detectado no sistema.")

    cmd = [
        executavel,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(caminho_arquivo)
    ]
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(resultado.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        raise ErroFFmpeg(f"Não foi possível obter a duração do vídeo: {e}")


def extrair_audio_mp3(caminho_entrada: Path, caminho_saida: Path):
    comando = [
        "ffmpeg", "-y",
        "-i", str(caminho_entrada),
        "-vn",
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        str(caminho_saida)
    ]
    executar_comando(comando)


def extrair_audio_wav_para_ia(caminho_entrada: Path, caminho_saida: Path):
    comando = [
        "ffmpeg", "-y",
        "-i", str(caminho_entrada),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(caminho_saida)
    ]
    executar_comando(comando)


def extrair_chunk_wav_pipe(
    caminho_video: Path,
    inicio_segundos: float,
    duracao_chunk: float
) -> bytes:
    """
    Extrai um pedaço (chunk) do áudio via pipe (sem salvar em disco).
    Retorna os bytes WAV completos (header + dados).

    - inicio_segundos: onde começar o corte
    - duracao_chunk: quantos segundos pegar a partir do início
    """
    executavel = localizar_caminho_ffmpeg()
    if not executavel:
        raise ErroFFmpeg("FFmpeg não foi detectado no seu computador.")

    cmd = [
        executavel, "-y",
        "-ss", f"{inicio_segundos:.3f}",
        "-i", str(caminho_video),
        "-t", f"{duracao_chunk:.3f}",
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "pipe:1"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
        return proc.stdout
    except subprocess.CalledProcessError as e:
        erro = e.stderr.strip() or str(e)
        raise ErroFFmpeg(f"Falha ao extrair chunk de áudio: {erro}")
