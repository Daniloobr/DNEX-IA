import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from app.core.config import config
from app.services.video_service import ServicoVideo
from app.services.transcription_service import ServicoTranscricao

logger = logging.getLogger(__name__)

class JobManager:
    """
    Gerencia as tarefas de processamento de áudio/vídeo em segundo plano.
    Utiliza um ThreadPoolExecutor para garantir processamento controlado
    sem travar o servidor HTTP e sem estourar a RAM/CPU.
    """
    _instancia = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia.jobs = {}
                cls._instancia.jobs_lock = threading.Lock()
                cls._instancia.executor = None
        return cls._instancia

    def _obter_executor(self) -> ThreadPoolExecutor:
        """Garante a entrega de um executor ativo, recriando-o caso tenha sido finalizado."""
        with self.jobs_lock:
            if self.executor is None or getattr(self.executor, "_shutdown", False):
                logger.info("🔧 Inicializando/Recriando ThreadPoolExecutor ativo para Dnex IA...")
                self.executor = ThreadPoolExecutor(max_workers=2)
            return self.executor

    def criar_job(self, acao: str) -> str:
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "status": "pending",
            "step": "queued",
            "progress": 0,
            "message": "Na fila do motor Dnex IA...",
            "error": None,
            "result": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        with self.jobs_lock:
            self.jobs[job_id] = job_data
        return job_id

    def obter_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if job:
                return job.copy()
            return None

    def atualizar_job(self, job_id: str, **kwargs):
        with self.jobs_lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)
                self.jobs[job_id]["updated_at"] = time.time()

    def iniciar_processamento(
        self, 
        job_id: str, 
        caminho_video: Path, 
        acao: str, 
        idioma: str, 
        incluir_timestamps: bool, 
        formato_srt: bool
    ):
        executor = self._obter_executor()
        executor.submit(
            self._executar_job, 
            job_id, 
            caminho_video, 
            acao, 
            idioma, 
            incluir_timestamps, 
            formato_srt
        )

    def _executar_job(
        self, 
        job_id: str, 
        caminho_video: Path, 
        acao: str, 
        idioma: str, 
        incluir_timestamps: bool, 
        formato_srt: bool
    ):
        caminho_wav_temp = None
        try:
            logger.info(f"🚀 Iniciando Job {job_id} ({acao}) para o arquivo {caminho_video.name}")
            self.atualizar_job(
                job_id,
                status="processing",
                step="extracting",
                progress=5,
                message="Extraindo áudio de alta fidelidade da mídia..."
            )

            if acao == "extract_audio":
                caminho_saida = ServicoVideo.gerar_mp3(caminho_video)
                self.atualizar_job(job_id, progress=90, message="Áudio MP3 gerado. Salvando resultado...")
                mensagem = "Sucesso! Seu áudio está pronto para baixar."
            elif acao == "transcribe":
                caminho_wav_temp = ServicoVideo.preparar_wav_transcricao(caminho_video)
                
                self.atualizar_job(
                    job_id,
                    step="transcribing",
                    progress=15,
                    message="Inicializando a engine de inteligência artificial..."
                )
                
                def progresso_whisper(percent_atual):
                    # O progresso de transcrição mapeia a faixa de 15% a 95% do progresso total
                    progresso_real = 15 + int(percent_atual * 0.80)
                    self.atualizar_job(
                        job_id,
                        progress=progresso_real,
                        message=f"Transcrevendo com a IA Dnex... ({percent_atual}%)"
                    )

                caminho_saida = ServicoTranscricao.transcrever(
                    caminho_wav_temp,
                    idioma=idioma,
                    incluir_timestamps=incluir_timestamps,
                    formato_srt=formato_srt,
                    callback_progresso=progresso_whisper
                )
                mensagem = "Sucesso! A transcrição foi concluída."
            else:
                raise ValueError("Ação desconhecida ou inválida.")

            # Limpeza de arquivos antigos para manter o servidor saudável
            from app.utils.file_utils import limpar_arquivos_antigos
            limpar_arquivos_antigos(config.PASTA_SAIDA)

            # Prepara o preview de texto
            conteudo_preview = ""
            if caminho_saida.suffix in [".txt", ".srt"]:
                texto_completo = caminho_saida.read_text(encoding="utf-8")
                conteudo_preview = texto_completo[:1000] # Primeiros 1000 caracteres

            # Sucesso
            download_url = f"/download/{caminho_saida.name}"

            self.atualizar_job(
                job_id,
                status="completed",
                step="completed",
                progress=100,
                message=mensagem,
                result={
                    "filename": caminho_saida.name,
                    "download_url": download_url,
                    "content": conteudo_preview
                }
            )
            logger.info(f"✨ Job {job_id} concluído com sucesso!")

        except Exception as e:
            logger.exception(f"❌ Falha crítica no processamento do Job {job_id}:")
            self.atualizar_job(
                job_id,
                status="failed",
                step="failed",
                progress=0,
                error=f"Erro interno do motor Dnex: {str(e)}",
                message="O processamento falhou de forma inesperada."
            )
        finally:
            # Limpeza rápida de arquivos brutos/temporários para liberar espaço em disco
            if caminho_wav_temp and caminho_wav_temp.exists():
                try:
                    caminho_wav_temp.unlink()
                except Exception:
                    pass
            if caminho_video and caminho_video.exists():
                try:
                    caminho_video.unlink()
                except Exception:
                    pass

# Instância única global do gerenciador de jobs
job_manager = JobManager()
