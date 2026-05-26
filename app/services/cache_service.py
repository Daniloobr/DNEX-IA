import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheChunks:
    """
    Cache de segmentos transcritos em disco.
    Usa hash do tamanho + nome do vídeo + chunk_index como chave,
    permitindo retomar transcrições interrompidas sem perder progresso.
    """
    def __init__(self, diretorio_cache: Path):
        self.diretorio = diretorio_cache
        self.diretorio.mkdir(exist_ok=True, parents=True)

    def _chave(self, caminho_video: Path, chunk_index: int) -> str:
        hash_video = hashlib.md5(
            f"{caminho_video.stat().st_size}:{caminho_video.name}".encode()
        ).hexdigest()[:12]
        return f"{hash_video}_{chunk_index:04d}.json"

    def obter(self, caminho_video: Path, chunk_index: int):
        path = self.diretorio / self._chave(caminho_video, chunk_index)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Cache corrompido para chunk {chunk_index}: {e}")
                path.unlink(missing_ok=True)
        return None

    def salvar(self, caminho_video: Path, chunk_index: int, segmentos: list):
        path = self.diretorio / self._chave(caminho_video, chunk_index)
        path.write_text(json.dumps(segmentos, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"Cache salvo: {path.name} ({len(segmentos)} segmentos)")

    def limpar_video(self, caminho_video: Path):
        """Remove todos os chunks cacheados de um vídeo específico."""
        prefixo = hashlib.md5(
            f"{caminho_video.stat().st_size}:{caminho_video.name}".encode()
        ).hexdigest()[:12]
        for path in self.diretorio.glob(f"{prefixo}_*.json"):
            path.unlink(missing_ok=True)
