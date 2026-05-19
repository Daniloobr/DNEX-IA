import logging
from pathlib import Path
from werkzeug.datastructures import FileStorage
from app.core.config import config
from app.utils.file_utils import arquivo_permitido, gerar_nome_unico
from app.utils.ffmpeg_utils import extrair_audio_mp3, extrair_audio_wav_para_ia

logger = logging.getLogger(__name__)

class ServicoVideo:
    """
    Coordena as operações de recebimento e extração de áudio.
    """
    @staticmethod
    def salvar_video(arquivo: FileStorage) -> Path:
        """Recebe o arquivo enviado via web e guarda na pasta de uploads."""
        if not arquivo or not arquivo.filename:
            raise ValueError("Nenhum arquivo foi recebido.")
        
        if not arquivo_permitido(arquivo.filename):
            extensoes = ", ".join(config.EXTENSOES_PERMITIDAS)
            raise ValueError(f"O Dnex IA aceita apenas os formatos: {extensoes}")
        
        nome_seguro = gerar_nome_unico(arquivo.filename)
        caminho_final = config.PASTA_UPLOADS / nome_seguro
        arquivo.save(str(caminho_final))
        
        logger.info(f"📁 Vídeo arquivado: {caminho_final}")
        return caminho_final

    @staticmethod
    def gerar_mp3(caminho_video: Path) -> Path:
        """Comanda a extração do MP3 final para o usuário."""
        nome_mp3 = gerar_nome_unico(caminho_video.name, sufixo=".mp3")
        caminho_saida = config.PASTA_SAIDA / nome_mp3
        
        extrair_audio_mp3(caminho_video, caminho_saida)
        logger.info(f"🎵 Áudio MP3 gerado: {caminho_saida}")
        return caminho_saida

    @staticmethod
    def preparar_wav_transcricao(caminho_video: Path) -> Path:
        """Cria um arquivo temporário de áudio otimizado para a IA ler."""
        nome_wav = gerar_nome_unico(caminho_video.name, sufixo=".wav")
        caminho_temp = config.PASTA_UPLOADS / nome_wav
        
        extrair_audio_wav_para_ia(caminho_video, caminho_temp)
        return caminho_temp
