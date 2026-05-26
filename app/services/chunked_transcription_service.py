import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from app.core.config import config
from app.utils.ffmpeg_utils import (
    extrair_chunk_wav_pipe,
    obter_duracao
)

logger = logging.getLogger(__name__)


DURACAO_CHUNK_SEGUNDOS = 30
SOBREPOSICAO_SEGUNDOS = 3


_thread_local = threading.local()


def _obter_modelo_thread():
    if not hasattr(_thread_local, "modelo"):
        from faster_whisper import WhisperModel
        num_cores = os.cpu_count() or 4
        workers = config.MAX_WORKERS_PARALELOS
        threads_por_modelo = max(1, num_cores // workers)
        _thread_local.modelo = WhisperModel(
            config.TAMANHO_MODELO_WHISPER,
            device=config.DISPOSITIVO_IA,
            compute_type=config.TIPO_COMPUTACAO,
            cpu_threads=threads_por_modelo,
            download_root="./models",
            num_workers=1
        )
    return _thread_local.modelo


def _wav_bytes_to_float32(wav_bytes: bytes) -> np.ndarray:
    raw = wav_bytes[44:]
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


def _transcrever_chunk(
    chunk_index: int,
    wav_bytes: bytes,
    offset_segundos: float,
    duracao_chunk: float,
    idioma: Optional[str]
) -> List[dict]:
    sigla_idioma = None if not idioma or idioma == "auto" else idioma

    inicio_carga = time.perf_counter()
    modelo = _obter_modelo_thread()
    tempo_carga = time.perf_counter() - inicio_carga

    audio = _wav_bytes_to_float32(wav_bytes)
    if len(audio) == 0:
        return []

    tempo_transc = time.perf_counter()
    segmentos, info = modelo.transcribe(
        audio,
        language=sigla_idioma,
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
    )
    segmentos = list(segmentos)
    tempo_total = time.perf_counter() - tempo_transc

    logger.info(
        f"  Chunk {chunk_index:03d}: {len(audio)/16000:.1f}s audio "
        f"-> {len(segmentos)} segmentos em {tempo_total:.1f}s"
    )

    resultados = []
    for s in segmentos:
        texto = s.text.strip()
        if not texto:
            continue
        resultados.append({
            "start": round(s.start + offset_segundos, 3),
            "end": round(s.end + offset_segundos, 3),
            "text": texto,
        })
    return resultados


def _merge_segmentos(
    todos_segmentos: List[dict],
    duracao_total: float,
    num_chunks: int
) -> List[dict]:
    todos_segmentos.sort(key=lambda x: x["start"])

    if not todos_segmentos:
        return []

    merged = [todos_segmentos[0]]
    for s in todos_segmentos[1:]:
        ultimo = merged[-1]
        sobreposicao = ultimo["end"] - s["start"]
        if sobreposicao > 0:
            if sobreposicao > 1.5:
                continuacao = _texto_eh_continuacao(ultimo["text"], s["text"])
                if continuacao:
                    ultimo["end"] = max(ultimo["end"], s["end"])
                    ultimo["text"] = ultimo["text"].rstrip() + " " + s["text"].strip()
                else:
                    if s["end"] > ultimo["end"]:
                        merged.append(s)
            else:
                ultimo["end"] = max(ultimo["end"], s["end"])
                palavras_ultimo = ultimo["text"].rstrip().split()
                palavras_novo = s["text"].strip().split()
                if len(palavras_novo) > len(palavras_ultimo) * 0.5:
                    if not ultimo["text"].strip().endswith(s["text"].strip()):
                        ultimo["text"] = ultimo["text"].rstrip() + " " + s["text"].strip()
        else:
            merged.append(s)

    return merged


def _texto_eh_continuacao(texto_a: str, texto_b: str) -> bool:
    a_clean = texto_a.strip().lower()
    b_clean = texto_b.strip().lower()
    if not a_clean or not b_clean:
        return True
    if a_clean.endswith((".", "!", "?", ":")):
        return False
    palavras_a = a_clean.split()
    palavras_b = b_clean.split()
    if len(palavras_a) > 0 and len(palavras_b) > 0:
        if palavras_a[-1] == palavras_b[0]:
            return True
    return True


def _escrever_resultado(
    segmentos: List[dict],
    nome_base: str,
    formato_srt: bool,
    incluir_timestamps: bool,
) -> str:
    linhas = []

    if formato_srt:
        for i, s in enumerate(segmentos, 1):
            inicio = _formatar_tempo_srt(s["start"])
            fim = _formatar_tempo_srt(s["end"])
            linhas.extend([str(i), f"{inicio} --> {fim}", s["text"], ""])
    else:
        for s in segmentos:
            if incluir_timestamps:
                inicio = _formatar_tempo(s["start"])
                fim = _formatar_tempo(s["end"])
                linhas.append(f"[{inicio} --> {fim}] {s['text']}")
            else:
                linhas.append(s["text"])

    if not linhas:
        linhas.append("Nenhum discurso ou fala foi detectado.")

    return "\n".join(linhas)


def _formatar_tempo(segundos: float) -> str:
    milisegundos = int((segundos - int(segundos)) * 1000)
    segs = int(segundos)
    horas = segs // 3600
    minutos = (segs % 3600) // 60
    return f"{horas:02d}:{minutos:02d}:{segs:02d}.{milisegundos:03d}"


def _formatar_tempo_srt(segundos: float) -> str:
    milisegundos = int((segundos - int(segundos)) * 1000)
    segs = int(segundos)
    horas = segs // 3600
    minutos = (segs % 3600) // 60
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milis:03d}"


def transcrever_com_chunks_paralelos(
    caminho_video: Path,
    caminho_wav_completo: Optional[Path],
    idioma: Optional[str],
    incluir_timestamps: bool,
    formato_srt: bool,
    callback_progresso: Optional[Callable[[int], None]] = None,
) -> Path:
    logger.info("=" * 50)
    logger.info("Modo RAPIDO: transcricao paralela com chunks ativada!")
    logger.info("=" * 50)
    inicio_total = time.perf_counter()

    duracao_video = obter_duracao(caminho_video)
    logger.info(f"Duracao do video: {duracao_video:.1f}s ({duracao_video/60:.1f} min)")

    if duracao_video <= 60:
        logger.info("Video curto (< 60s) — usando transcricao tradicional (sem chunks).")
        from app.services.transcription_service import ServicoTranscricao
        return ServicoTranscricao.transcrever(
            caminho_wav_completo or caminho_video,
            idioma=idioma,
            incluir_timestamps=incluir_timestamps,
            formato_srt=formato_srt,
            callback_progresso=callback_progresso,
        )

    num_chunks = max(1, math.ceil(duracao_video / DURACAO_CHUNK_SEGUNDOS))
    workers = min(config.MAX_WORKERS_PARALELOS, num_chunks)

    logger.info(
        f"Dividindo em {num_chunks} chunks de ~{DURACAO_CHUNK_SEGUNDOS}s "
        f"com {SOBREPOSICAO_SEGUNDOS}s de overlap, "
        f"{workers} workers paralelos"
    )

    def preparar_chunk(i: int) -> dict:
        inicio_chunk = i * DURACAO_CHUNK_SEGUNDOS
        inicio_com_overlap = max(0, inicio_chunk - SOBREPOSICAO_SEGUNDOS)
        duracao_extrair = DURACAO_CHUNK_SEGUNDOS + SOBREPOSICAO_SEGUNDOS
        if inicio_com_overlap + duracao_extrair > duracao_video:
            duracao_extrair = duracao_video - inicio_com_overlap
        return {
            "index": i,
            "offset": inicio_chunk,
            "inicio_pipe": inicio_com_overlap,
            "duracao_pipe": duracao_extrair,
        }

    chunks_info = [preparar_chunk(i) for i in range(num_chunks)]

    todos_segmentos = []
    futures_map = {}
    chunks_lock = threading.Lock()

    executor = ThreadPoolExecutor(max_workers=workers)

    try:
        with executor:
            for chunk in chunks_info:
                future = executor.submit(
                    _processar_chunk_com_retry,
                    chunk,
                    caminho_video,
                    idioma,
                )
                futures_map[future] = chunk["index"]

            for future in as_completed(futures_map):
                chunk_index = futures_map[future]
                try:
                    segmentos = future.result()
                    with chunks_lock:
                        todos_segmentos.extend(segmentos)
                except Exception as e:
                    logger.exception(f"Falha no chunk {chunk_index}: {e}")
                    raise

                if callback_progresso:
                    indices_feitos = {
                        futures_map[f] for f in futures_map
                        if f.done()
                    }
                    pct = int((len(indices_feitos) / num_chunks) * 95) + 2
                    callback_progresso(min(pct, 97))

    except Exception:
        raise

    segmentos_final = _merge_segmentos(todos_segmentos, duracao_video, num_chunks)

    conteudo = _escrever_resultado(
        segmentos_final,
        caminho_video.stem,
        formato_srt,
        incluir_timestamps,
    )

    ext = ".srt" if formato_srt else ".txt"
    from app.utils.file_utils import gerar_nome_unico
    nome_final = gerar_nome_unico(caminho_video.name, sufixo=ext)
    caminho_final = config.PASTA_SAIDA / nome_final
    caminho_final.write_text(conteudo, encoding="utf-8")

    tempo_total = time.perf_counter() - inicio_total
    speedup = duracao_video / tempo_total if tempo_total > 0 else 0
    logger.info(
        f"Transcricao paralela concluida em {tempo_total:.1f}s "
        f"(speedup: {speedup:.1f}x)"
    )

    return caminho_final


def _processar_chunk_com_retry(
    chunk: dict,
    caminho_video: Path,
    idioma: Optional[str],
    tentativas: int = 2,
) -> List[dict]:
    for tentativa in range(tentativas):
        try:
            wav_bytes = extrair_chunk_wav_pipe(
                caminho_video,
                chunk["inicio_pipe"],
                chunk["duracao_pipe"],
            )
            segmentos = _transcrever_chunk(
                chunk["index"],
                wav_bytes,
                chunk["offset"],
                chunk["duracao_pipe"],
                idioma,
            )
            return segmentos
        except Exception as e:
            if tentativa < tentativas - 1:
                logger.warning(
                    f"  Chunk {chunk['index']} falhou (tentativa {tentativa+1}): {e}. "
                    "Tentando novamente..."
                )
                time.sleep(1)
            else:
                raise
    return []
