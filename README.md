# Dnex IA 🚀
> **Transformando suas mídias em dados em tempo real, sem limites e sem complicação.**

O **Dnex IA** é um ecossistema inteligente de alta performance para extração de áudio e transcrição automática de mídias (vídeos e áudios) de qualquer tamanho. Ele combina o poder da biblioteca **faster-whisper** com uma arquitetura web de processamento assíncrono em segundo plano e uma interface de usuário *premium, moderna e fluida*.

Esqueça as ferramentas pagas, burocráticas ou que exigem upload de dados privados para servidores terceiros de forma síncrona. Com o Dnex IA, você processa arquivos de **qualquer tamanho (limite padrão de 2 GB!)** com total privacidade e acompanhamento milimétrico do progresso em tempo real.

---

## 🎨 O Que Torna o Dnex IA Especial?

*   **⚡ Arquitetura Assíncrona e Resiliente:** Acabamos com os erros de timeout (`HTTP 504`)! O arquivo é enviado, a requisição HTTP é concluída imediatamente e o processamento ocorre em segundo plano.
*   **🔄 Pool de Threads Auto-Regenerativo:** Equipado com um gerenciador inteligente (`JobManager`), o motor reinicia e cria novos pools de execução automaticamente se o servidor reiniciar ou atualizar, garantindo que suas tarefas nunca fiquem órfãs.
*   **📊 Progresso Dinâmico Real:** Ao contrário de barras de progresso estáticas que "chutam" a porcentagem, calculamos o progresso real comparando o progresso da fala que a Inteligência Artificial está analisando (`segment.end`) com a duração total da mídia.
*   **🛡️ Privacidade por Design:** Seus vídeos não saem do servidor. O processamento é local, rápido e seguro.
*   **💬 Suporte Completo a SRT e Timestamps:** Escolha entre transcrição simples em texto puro (`.txt`) ou legendas profissionais prontas para edição (`.srt`) com marcações de tempo impecáveis.
*   **🔌 Configuração Simples por `.env`:** Altere limites de tamanho de arquivo, selecione o tamanho do modelo do Whisper (Tiny, Base, Small, Medium, Large) ou ative aceleração por placa de vídeo com apenas uma linha de código.

---

## 🛠 Recursos Principais

1.  **Extração de Áudio Ultra-Fiel:** Extrai o canal de áudio original de qualquer vídeo nos formatos mais comuns (`.mp4`, `.mov`, `.avi`, `.mkv`) e gera um arquivo `.mp3` de alta fidelidade instantaneamente.
2.  **Transcrição com IA Profissional:** Traduz falas de áudios em textos limpos de alta precisão com suporte a múltiplos idiomas e detecção automática de fala.
3.  **Gerador de Legendas `.srt`:** Cria legendas organizadas, formatadas e perfeitamente sincronizadas para os seus vídeos.

---

## 🚀 Começando em 3 Passos (Instalação Local)

### 1. Dependências do Sistema (FFmpeg)
O Dnex IA utiliza o **FFmpeg** para desmembrar vídeos e tratar os fluxos de áudio de forma super veloz.

*   **Windows (Via WinGet):**
    ```powershell
    winget install Gyan.FFmpeg
    ```
*   **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt update && sudo apt install -y ffmpeg
    ```
*   **Mac (Via Homebrew):**
    ```bash
    brew install ffmpeg
    ```

### 2. Configurando o Ambiente Python
Clone este repositório, navegue até a pasta do projeto e instale as dependências:
```bash
# Instala os pacotes necessários
pip install -r requirements.txt
```

### 3. Ajustando Configurações (`.env`)
Criamos um arquivo de configuração **`.env`** na raiz do projeto para você gerenciar o ecossistema livremente:
```env
# Limite de tamanho de upload (neste exemplo, definido para 2 GB)
MAX_CONTENT_LENGTH=2147483648

# Modelo Whisper a utilizar (tiny, base, small, medium, large-v3)
WHISPER_MODEL_SIZE=tiny

# Dispositivo ('cpu' ou 'cuda' para placas de vídeo NVIDIA)
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### 4. Iniciando o Sistema
```bash
python main.py
```
Acesse `http://localhost:5000` no seu navegador de preferência!

> 💡 **Dica de Ouro:** Na primeira vez que você executar uma transcrição, o Dnex IA baixará o modelo de IA do HuggingFace automaticamente. Isso demora cerca de 1 a 2 minutos e é feito apenas uma vez!

---

## 📂 Arquitetura do Projeto

*   `app/core/config.py`: Mapeamento de variáveis globais e caminhos absolutos para o `.env`.
*   `app/services/job_service.py`: Gerenciamento assíncrono das tarefas e fila em segundo plano (`ThreadPoolExecutor`).
*   `app/services/transcription_service.py`: Comunicação com o motor `faster-whisper` e hooks de progresso.
*   `app/services/video_service.py`: Extração e otimização de mídias usando `FFmpeg`.
*   `static/js/app.js`: Frontend premium com upload fracionado, polling inteligente e barra de progresso viva.

---

## ☁️ Deploy na Nuvem (Render / Docker)

Este projeto já está pronto para deploy no **Render** ou em qualquer plataforma VPS via **Docker**:
*   O arquivo `render.yaml` define o deploy automatizado.
*   O arquivo `Dockerfile` constrói uma imagem Linux estável contendo Python, PyTorch, Whisper e FFmpeg já pré-instalados.

*Recomendação para nuvem:* Para transcrever arquivos gigantes com rapidez, escolha um plano de servidor com no mínimo **1 GB ou 2 GB de memória RAM** (como o plano Starter do Render).

---

## 🔮 Próximos Passos (Roadmap)
*   [ ] Tradução automática de legendas para mais de 30 idiomas.
*   [ ] Painel histórico de transcrições anteriores salvas no navegador.
*   [ ] Player de vídeo integrado no preview para sincronização fina de texto e som.

**Dnex IA: Inteligente, veloz, privado e feito por humanos.** 🟢
