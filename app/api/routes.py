import logging
from flask import Blueprint, request, jsonify, render_template, send_from_directory
from app.core.config import config
from app.services.video_service import ServicoVideo
from app.services.job_service import job_manager

logger = logging.getLogger(__name__)
rotas_principais = Blueprint("principal", __name__)

@rotas_principais.route("/")
def pagina_inicial():
    """Renderiza o site do Dnex IA."""
    limite_mb = config.TAMANHO_MAXIMO_ARQUIVO // (1024 * 1024)
    return render_template("index.html", max_mb=limite_mb)

@rotas_principais.route("/api/process", methods=["POST"])
def processar_video():
    """
    Endpoint principal: recebe o vídeo, cria uma tarefa de processamento
    assíncrono em segundo plano e retorna o ID da tarefa (Job ID).
    """
    arquivo_video = request.files.get("video")
    acao = request.form.get("action", "").strip()
    idioma = request.form.get("language", "auto").strip()
    incluir_timestamps = request.form.get("timestamps", "true") == "true"
    formato_srt = request.form.get("srt_format", "false") == "true"
    
    if not arquivo_video:
        return jsonify({"ok": False, "error": "Você precisa enviar um vídeo."}), 400
        
    if acao not in {"extract_audio", "transcribe"}:
        return jsonify({"ok": False, "error": "Comando desconhecido."}), 400
    
    caminho_video = None
    try:
        # 1. Salva o vídeo enviado no disco (e valida formato/extensão)
        caminho_video = ServicoVideo.salvar_video(arquivo_video)
        
        # 2. Cria a tarefa no gerenciador de jobs
        job_id = job_manager.criar_job(acao)
        
        # 3. Dispara o processamento em segundo plano (Assíncrono)
        job_manager.iniciar_processamento(
            job_id=job_id,
            caminho_video=caminho_video,
            acao=acao,
            idioma=idioma,
            incluir_timestamps=incluir_timestamps,
            formato_srt=formato_srt
        )
        
        return jsonify({
            "ok": True,
            "message": "Upload concluído com sucesso! Iniciando processamento em segundo plano...",
            "job_id": job_id
        })

    except ValueError as e:
        # Se falhar a validação antes de começar o job, remove o arquivo se tiver sido salvo
        if caminho_video and caminho_video.exists():
            try:
                caminho_video.unlink()
            except Exception:
                pass
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("🚨 Falha crítica ao iniciar processamento de mídia:")
        if caminho_video and caminho_video.exists():
            try:
                caminho_video.unlink()
            except Exception:
                pass
        return jsonify({"ok": False, "error": f"Erro interno ao enfileirar: {str(e)}"}), 500

@rotas_principais.route("/api/job/<job_id>", methods=["GET"])
def obter_status_job(job_id):
    """
    Endpoint de polling: retorna o estado atual, progresso (0-100), etapa
    e resultado final do processamento da tarefa.
    """
    job = job_manager.obter_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Tarefa não encontrada."}), 404
    return jsonify({"ok": True, **job})

@rotas_principais.route("/download/<path:nome_arquivo>")
def baixar_arquivo(nome_arquivo):
    """Permite ao usuário baixar o arquivo gerado (MP3 ou TXT)."""
    import os
    # Garante caminho absoluto padrão string para evitar erro 404 no Windows
    pasta_saida_abs = os.path.abspath(str(config.PASTA_SAIDA))
    return send_from_directory(pasta_saida_abs, nome_arquivo, as_attachment=True)
