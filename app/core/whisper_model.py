import logging
import multiprocessing

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise ImportError("A biblioteca 'faster-whisper' não foi instalada. Use: pip install faster-whisper")

from app.core.config import config

logger = logging.getLogger(__name__)

class GerenciadorModeloIA:
    """
    Gerencia o carregamento do modelo Whisper de forma única (Singleton).
    Isso evita que o modelo seja carregado várias vezes, economizando memória.
    """
    _instancia = None

    @classmethod
    def obter_modelo(cls) -> WhisperModel:
        if cls._instancia is None:
            logger.info(f"🤖 Dnex Engine: Carregando modelo ({config.TAMANHO_MODELO_WHISPER}) em {config.DISPOSITIVO_IA}...")
            try:
                # Otimiza o uso da CPU baseando-se nos núcleos disponíveis
                threads = multiprocessing.cpu_count()
                
                cls._instancia = WhisperModel(
                    config.TAMANHO_MODELO_WHISPER,
                    device=config.DISPOSITIVO_IA,
                    compute_type=config.TIPO_COMPUTACAO,
                    cpu_threads=threads,
                    download_root="./models"
                )
                logger.info(f"✅ Dnex Engine: Pronto com {threads} threads.")
            except Exception as e:
                logger.error(f"❌ Erro ao carregar motor de IA: {e}")
                raise RuntimeError(f"Falha técnica no motor Dnex: {e}")
        return cls._instancia

def carregar_motor_ia() -> WhisperModel:
    """Função auxiliar para obter o motor de transcrição."""
    return GerenciadorModeloIA.obter_modelo()
