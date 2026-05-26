import os
import shutil
import subprocess
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 2048 * 1024 * 1024))


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["OUTPUT_FOLDER"] = str(OUTPUT_DIR)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg não foi encontrado no PATH. Instale o FFmpeg antes de processar vídeos.")


def run_ffmpeg(command):
    require_ffmpeg()
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        error = completed.stderr.strip() or "Erro desconhecido ao executar FFmpeg."
        raise RuntimeError(error)


def save_uploaded_video(file_storage):
    original_name = secure_filename(file_storage.filename or "")
    if not original_name:
        raise ValueError("Nenhum arquivo foi enviado.")

    if not allowed_file(original_name):
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Formato inválido. Envie um arquivo: {allowed}.")

    suffix = Path(original_name).suffix.lower()
    safe_stem = Path(original_name).stem[:80] or "video"
    unique_name = f"{safe_stem}-{uuid.uuid4().hex}{suffix}"
    upload_path = UPLOAD_DIR / unique_name
    file_storage.save(upload_path)
    return upload_path, safe_stem


def extract_mp3(video_path, output_stem):
    output_path = OUTPUT_DIR / f"{output_stem}-{uuid.uuid4().hex}.mp3"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def extract_wav_for_transcription(video_path, output_stem):
    output_path = OUTPUT_DIR / f"{output_stem}-{uuid.uuid4().hex}.wav"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def format_timestamp(seconds):
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def transcribe_audio(audio_path, output_stem, language=None, include_timestamps=True, model_size="base"):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Dependência faster-whisper não instalada. Rode: pip install -r requirements.txt") from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    language_arg = language if language and language != "auto" else None
    segments, info = model.transcribe(str(audio_path), language=language_arg, vad_filter=True)

    lines = []
    if language_arg is None and info.language:
        lines.append(f"Idioma detectado: {info.language}")
        lines.append("")

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if include_timestamps:
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            lines.append(f"[{start} - {end}] {text}")
        else:
            lines.append(text)

    output_path = OUTPUT_DIR / f"{output_stem}-{uuid.uuid4().hex}.txt"
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path


@app.route("/")
def index():
    return render_template("index.html", max_mb=MAX_CONTENT_LENGTH // (1024 * 1024))


@app.route("/api/process", methods=["POST"])
def process_video():
    uploaded_file = request.files.get("video")
    action = request.form.get("action", "").strip()
    language = request.form.get("language", "auto").strip()
    include_timestamps = request.form.get("timestamps", "true") == "true"
    model_size = request.form.get("model", "base").strip() or "base"

    if action not in {"extract_audio", "transcribe"}:
        return jsonify({"ok": False, "error": "Ação inválida."}), 400

    if not uploaded_file:
        return jsonify({"ok": False, "error": "Envie um arquivo de vídeo."}), 400

    upload_path = None
    wav_path = None

    try:
        upload_path, safe_stem = save_uploaded_video(uploaded_file)

        if action == "extract_audio":
            output_path = extract_mp3(upload_path, safe_stem)
            message = "Áudio extraído com sucesso."
        else:
            wav_path = extract_wav_for_transcription(upload_path, safe_stem)
            output_path = transcribe_audio(
                wav_path,
                safe_stem,
                language=language,
                include_timestamps=include_timestamps,
                model_size=model_size,
            )
            message = "Transcrição gerada com sucesso."

        return jsonify(
            {
                "ok": True,
                "message": message,
                "filename": output_path.name,
                "download_url": url_for("download_file", filename=output_path.name),
            }
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    except Exception:
        app.logger.exception("Erro inesperado ao processar vídeo")
        return jsonify({"ok": False, "error": "Erro inesperado ao processar o vídeo."}), 500
    finally:
        if wav_path and wav_path.exists():
            wav_path.unlink(missing_ok=True)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.errorhandler(413)
def file_too_large(_error):
    max_mb = MAX_CONTENT_LENGTH // (1024 * 1024)
    return jsonify({"ok": False, "error": f"Arquivo muito grande. Limite: {max_mb} MB."}), 413


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
