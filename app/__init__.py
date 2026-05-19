import logging
import threading
from flask import Flask
from app.core.config import config

def criar_app() -> Flask:
    """
    Constrói a aplicação Dnex IA, configurando logs, pastas e rotas.
    """
    # Configuração de Logs (o que aparece no terminal)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Inicializa o Flask
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )
    
    # Inicializa pastas e configurações
    config.inicializar_pastas()
    app.config["MAX_CONTENT_LENGTH"] = config.TAMANHO_MAXIMO_ARQUIVO
    
    # Registra as rotas (Blueprints)
    from app.api.routes import rotas_principais
    app.register_blueprint(rotas_principais)
    
    # Inicia o motor de IA em segundo plano para não travar a abertura do site
    from app.core.whisper_model import carregar_motor_ia
    threading.Thread(target=carregar_motor_ia, daemon=True).start()
    
    # Gerenciador de erros: Arquivos muito grandes
    @app.errorhandler(413)
    def arquivo_muito_grande(e):
        limite_mb = config.TAMANHO_MAXIMO_ARQUIVO // (1024 * 1024)
        return {"ok": False, "error": f"Arquivo gigante! O limite é {limite_mb} MB."}, 413

    return app
