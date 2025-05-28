from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    GEMINI_SECURE_1PSID: str
    GEMINI_SECURE_1PSIDTS: str

    LOG_LEVEL: str = "INFO"
    ALLOWED_API_KEYS: List[str] = []

    # Novas configurações para o modelo Gemini
    DEFAULT_GEMINI_MODEL_NAME: str = "unspecified" # Modelo Gemini padrão
    OPENAI_TO_GEMINI_MODEL_MAP_JSON: str = "{}" # Mapeamento como string JSON

    @property
    def OPENAI_TO_GEMINI_MODEL_MAP(self) -> Dict[str, str]:
        try:
            return json.loads(self.OPENAI_TO_GEMINI_MODEL_MAP_JSON)
        except json.JSONDecodeError:
            # Logar um aviso ou erro aqui se o JSON for inválido
            print(f"AVISO: OPENAI_TO_GEMINI_MODEL_MAP_JSON ('{self.OPENAI_TO_GEMINI_MODEL_MAP_JSON}') não é um JSON válido. Usando mapa vazio.")
            return {}

settings = Settings()
