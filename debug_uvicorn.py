import pudb
from uvicorn import run
from app.main import app  # Ajuste o caminho para o seu arquivo main e objeto app

if __name__ == "__main__":
    pudb.set_trace()
    run(app, host="0.0.0.0", port=8000, reload=True)
