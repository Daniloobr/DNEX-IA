import os
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
from app.services.chunked_transcription_service import transcrever_com_chunks_paralelos
from app.utils.ffmpeg_utils import obter_duracao

logger = logging.getLogger(__name__)

class JobManager:
    """
    Gerencia as tarefas de processamento de áudio/vídeo em segundo plano.
    Usa um ThreadPoolExecutor dimensionado dinamicamente conforme os núcleos da CPU.
    Para transcrições longas (>60s), ativa o modo paralelo com chunks.
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
        with self.jobs_lock:
            if self.executor is None or getattr(self.executor, "_shutdown", False):
                num_workers = max(2, config.MAX_WORKERS_PARALELOS)
                logger.info(f"🔧 Inicializando ThreadPoolExecutor com {num_workers} workers...")
                self.executor = ThreadPoolExecutor(max_workers=num_workers)
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
                self.atualizar_job(
                    job_id,
                    step="transcribing",
                    progress=10,
                    message="Preparando motor de inteligência artificial..."
                )

                def progresso_whisper(percent_atual):
                    progresso_real = 10 + int(percent_atual * 0.85)
                    self.atualizar_job(
                        job_id,
                        progress=progresso_real,
                        message=f"Transcrevendo com a IA Dnex... ({percent_atual}%)"
                    )

                duracao = obter_duracao(caminho_video)
                logger.info(f"Duração do vídeo: {duracao:.1f}s — {'MODO RÁPIDO (chunks)' if duracao > 60 else 'MODO PADRÃO'}")

                if duracao > 60:
                    caminho_wav_temp = ServicoVideo.preparar_wav_transcricao(caminho_video)
                    caminho_saida = transcrever_com_chunks_paralelos(
                        caminho_video=caminho_video,
                        caminho_wav_completo=caminho_wav_temp,
                        idioma=idioma,
                        incluir_timestamps=incluir_timestamps,
                        formato_srt=formato_srt,
                        callback_progresso=progresso_whisper,
                    )
                else:
                    caminho_wav_temp = ServicoVideo.preparar_wav_transcricao(caminho_video)
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
