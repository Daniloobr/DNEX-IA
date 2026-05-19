const form = document.querySelector("#videoForm");
const videoInput = document.querySelector("#videoInput");
const dropzone = document.querySelector("#dropzone");
const preview = document.querySelector("#preview");
const statusBox = document.querySelector("#status");
const downloadLink = document.querySelector("#downloadLink");
const progressWrap = document.querySelector("#progressWrap");
const progressBar = document.querySelector("#progressBar");
const progressText = document.querySelector("#progressText");
const buttons = document.querySelectorAll("[data-action]");

let currentPollInterval = null;

function setStatus(message, type = "idle") {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`;
}

function setBusy(isBusy, activeAction = null) {
  buttons.forEach((button) => {
    button.disabled = isBusy;
    const loader = button.querySelector(".btn-loader");
    const text = button.querySelector(".btn-text");
    const icon = button.querySelector(".btn-icon");
    
    if (isBusy && button.dataset.action === activeAction) {
      loader.hidden = false;
      if (icon) icon.hidden = true;
      text.style.opacity = "0.7";
    } else {
      loader.hidden = true;
      if (icon) icon.hidden = false;
      text.style.opacity = "1";
    }
  });
}

function resetResult() {
  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
  document.getElementById("previewContainer").hidden = true;
  document.getElementById("previewText").textContent = "";
}

function updatePreview() {
  const file = videoInput.files[0];
  resetResult();

  if (!file) {
    preview.hidden = true;
    preview.removeAttribute("src");
    setStatus("Aguardando vídeo.");
    return;
  }

  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  setStatus(`Arquivo selecionado: ${file.name}`);
}

function pollJobStatus(jobId, action) {
  if (currentPollInterval) {
    clearInterval(currentPollInterval);
  }

  currentPollInterval = setInterval(() => {
    fetch(`/api/job/${jobId}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error("Erro na resposta do servidor.");
        }
        return res.json();
      })
      .then((payload) => {
        if (!payload.ok) {
          clearInterval(currentPollInterval);
          setBusy(false);
          progressBar.classList.remove("pulse");
          progressText.textContent = "Erro ao obter status do processamento.";
          setStatus(payload.error || "Erro desconhecido.", "error");
          return;
        }

        const progress = payload.progress || 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = payload.message;

        if (payload.status === "completed") {
          clearInterval(currentPollInterval);
          setBusy(false);
          progressBar.classList.remove("pulse");
          progressBar.style.width = "100%";
          progressText.textContent = "Tudo pronto! Seu arquivo foi gerado.";
          setStatus(payload.message, "success");

          // Atualiza Preview se houver conteúdo
          if (payload.result && payload.result.content) {
            document.getElementById("previewText").textContent = payload.result.content;
            document.getElementById("previewContainer").hidden = false;
          } else {
            document.getElementById("previewContainer").hidden = true;
          }

          downloadLink.href = payload.result.download_url;
          downloadLink.textContent = `BAIXAR ${payload.result.filename}`;
          downloadLink.hidden = false;
        } else if (payload.status === "failed") {
          clearInterval(currentPollInterval);
          setBusy(false);
          progressBar.classList.remove("pulse");
          progressText.textContent = "O processamento falhou.";
          setStatus(payload.error || "Erro no motor de processamento.", "error");
        }
      })
      .catch((err) => {
        console.warn("Erro ao buscar status do processamento (tentando novamente...):", err);
      });
  }, 2000);
}

function submitAction(action) {
  const file = videoInput.files[0];
  if (!file) {
    setStatus("Selecione um vídeo antes de continuar.", "error");
    return;
  }

  if (currentPollInterval) {
    clearInterval(currentPollInterval);
  }

  const data = new FormData(form);
  data.set("action", action);
  data.set("timestamps", document.querySelector("#timestamps").checked ? "true" : "false");
  data.set("srt_format", document.querySelector("#srt_format").checked ? "true" : "false");

  const request = new XMLHttpRequest();
  request.open("POST", "/api/process");

  setBusy(true, action);
  resetResult();
  progressWrap.hidden = false;
  progressBar.style.width = "0%";
  progressText.textContent = "Enviando vídeo para o servidor...";
  setStatus(action === "extract_audio" ? "Enviando áudio..." : "Enviando vídeo...");

  request.upload.onprogress = (event) => {
    if (!event.lengthComputable) return;
    const percent = Math.round((event.loaded / event.total) * 100);
    // Upload representará até 100% da primeira fase de progresso visual
    progressBar.style.width = `${percent}%`;
    
    if (percent < 100) {
      progressText.textContent = `Enviando arquivo para o Dnex IA... (${percent}%)`;
    } else {
      progressBar.classList.add("pulse");
      progressText.textContent = "Upload concluído! Entrando na fila de processamento...";
      setStatus("🧠 A Inteligência Artificial está se preparando para trabalhar no seu arquivo...", "success");
    }
  };

  request.onload = () => {
    let payload = {};
    try {
      payload = JSON.parse(request.responseText);
    } catch (_error) {
      setBusy(false);
      progressBar.classList.remove("pulse");
      progressText.textContent = "Erro na resposta do servidor.";
      setStatus("Resposta inválida do motor Dnex.", "error");
      return;
    }

    if (!payload.ok) {
      setBusy(false);
      progressBar.classList.remove("pulse");
      progressText.textContent = "O envio do arquivo falhou.";
      setStatus(payload.error || "Erro desconhecido ao carregar.", "error");
      return;
    }

    // Se recebemos um ID da tarefa em segundo plano, iniciamos o acompanhamento
    if (payload.job_id) {
      pollJobStatus(payload.job_id, action);
    } else {
      setBusy(false);
      progressBar.classList.remove("pulse");
      progressBar.style.width = "100%";
      progressText.textContent = "Tudo pronto! Seu arquivo foi gerado.";
      setStatus(payload.message, "success");
      
      if (payload.content) {
        document.getElementById("previewText").textContent = payload.content;
        document.getElementById("previewContainer").hidden = false;
      }
      downloadLink.href = payload.download_url;
      downloadLink.textContent = `BAIXAR ${payload.filename}`;
      downloadLink.hidden = false;
    }
  };

  request.onerror = () => {
    setBusy(false);
    setStatus("Falha na conexão de rede com o motor Dnex.", "error");
  };

  request.send(data);
}

// Botão Copiar para área de transferência
document.getElementById("copyBtn").addEventListener("click", () => {
  const text = document.getElementById("previewText").textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copyBtn");
    const originalText = btn.textContent;
    btn.textContent = "Copiado! ✅";
    btn.style.background = "var(--accent)";
    btn.style.color = "#000";
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.background = "var(--line)";
      btn.style.color = "#fff";
    }, 2000);
  });
});

videoInput.addEventListener("change", updatePreview);

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
  });
});

dropzone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  videoInput.files = transfer.files;
  updatePreview();
});

buttons.forEach((button) => {
  button.addEventListener("click", () => submitAction(button.dataset.action));
});
