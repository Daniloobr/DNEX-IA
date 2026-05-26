import logging
from pathlib import Path
from typing import List, Optional
from app.core.config import config
from app.core.whisper_model import carregar_motor_ia
from app.utils.file_utils import formatar_tempo, gerar_nome_unico

logger = logging.getLogger(__name__)

def formatar_tempo_srt(segundos: float) -> str:
    """Formata segundos para o padrão SRT (00:00:00,000)."""
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milis = int((segundos - int(segundos)) * 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milis:03d}"

class ServicoTranscricao:
    """
    Usa a Inteligência Artificial para converter áudio em texto escrito ou legendas.
    """
    @staticmethod
    def transcrever(
        caminho_audio: Path, 
        idioma: Optional[str] = None, 
        incluir_timestamps: bool = True,
        formato_srt: bool = False,
        callback_progresso = None
    ) -> Path:
        """Processa o áudio e cria um arquivo .txt ou .srt com o resultado."""
        motor = carregar_motor_ia()
        
        logger.info(f"🧠 Dnex IA: Transcrevendo {caminho_audio.name}...")
        
        sigla_idioma = None if not idioma or idioma == "auto" else idioma
        
        segmentos, info = motor.transcribe(
            str(caminho_audio),
            language=sigla_idioma,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )
        
        total_duration = info.duration if info and info.duration else 0.0
        linhas: List[str] = []
        
        if formato_srt:
            # Lógica de Legendas SRT
            for i, s in enumerate(segmentos, 1):
                texto = s.text.strip()
                if not texto: continue
                inicio = formatar_tempo_srt(s.start)
                fim = formatar_tempo_srt(s.end)
                linhas.extend([str(i), f"{inicio} --> {fim}", texto, ""])
                
                # Progresso callback
                if total_duration > 0 and callback_progresso:
                    percent = min(99, int((s.end / total_duration) * 100))
                    callback_progresso(percent)
        else:
            # Lógica de Texto Simples
            if not sigla_idioma and info.language:
                prob = info.language_probability * 100
                linhas.append(f"--- Idioma Detectado: {info.language} ({prob:.1f}%) ---")
                linhas.append("")
 
            for s in segmentos:
                texto = s.text.strip()
                if not texto: continue
                if incluir_timestamps:
                    inicio = formatar_tempo(s.start)
                    fim = formatar_tempo(s.end)
                    linhas.append(f"[{inicio} --> {fim}] {texto}")
                else:
                    linhas.append(texto)
                
                # Progresso callback
                if total_duration > 0 and callback_progresso:
                    percent = min(99, int((s.end / total_duration) * 100))
                    callback_progresso(percent)

        if not linhas:
            linhas.append("Nenhum discurso ou fala foi detectado.")

        # Define extensão e salva
        ext = ".srt" if formato_srt else ".txt"
        nome_final = gerar_nome_unico(caminho_audio.name, sufixo=ext)
        caminho_final = config.PASTA_SAIDA / nome_final
        
        caminho_final.write_text("\n".join(linhas), encoding="utf-8")
        logger.info(f"✨ Processamento finalizado: {caminho_final}")
        
        return caminho_final
