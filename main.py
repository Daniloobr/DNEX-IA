from app import criar_app

# Inicializa o aplicativo Dnex IA
app = criar_app()

if __name__ == "__main__":
    """
    Ponto de partida do servidor.
    Dica: Em ambiente real de internet, prefira usar Gunicorn ou Waitress.
    """
    print("🚀 Dnex IA está decolando!")
    app.run(host="0.0.0.0", port=5000, debug=True)
