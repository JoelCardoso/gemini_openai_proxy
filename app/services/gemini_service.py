import asyncio
from typing import Optional
from httpx import ReadTimeout

from gemini_webapi import GeminiClient, AuthError, APIError # Importe as exceções relevantes
from gemini_webapi.types import ModelOutput
from loguru import logger # Gemini-API usa loguru

from app.core.config import settings

class GeminiService:
    _client: Optional[GeminiClient] = None
    _lock = asyncio.Lock() # Para garantir que a inicialização seja thread-safe/async-safe

    async def _initialize_client(self) -> GeminiClient:
        async with self._lock: # Adquire o lock antes de verificar/inicializar
            if self._client is None or not self._client.running:
                logger.info("Initializing GeminiClient...")
                if not settings.GEMINI_SECURE_1PSID:
                    logger.error("GEMINI_SECURE_1PSID não configurado.")
                    raise ValueError("GEMINI_SECURE_1PSID é obrigatório.")

                # A biblioteca GeminiClient pode tentar carregar cookies do browser
                # se os valores não forem fornecidos e browser-cookie3 estiver instalado.
                # Aqui, estamos fornecendo explicitamente.
                try:
                    client = GeminiClient(
                        secure_1psid=settings.GEMINI_SECURE_1PSID,
                        secure_1psidts=settings.GEMINI_SECURE_1PSIDTS, # Pode ser None
                        # proxy=settings.PROXY se você tiver um proxy
                    )
                    # O método init lida com a obtenção do token de acesso e validação dos cookies
                    await client.init(
                        timeout=30,
                        auto_close=False, # Manteremos o cliente ativo
                        auto_refresh=True, # Permitir que a biblioteca atualize cookies
                        verbose=settings.LOG_LEVEL.upper() == "DEBUG" # Mais logs se DEBUG
                    )
                    self._client = client
                    logger.success("GeminiClient initialized successfully.")
                except AuthError as e:
                    logger.error(f"Erro de autenticação ao inicializar GeminiClient: {e}")
                    # Você pode querer desligar a aplicação ou tentar novamente após um tempo
                    raise  # Re-lança para ser tratado no endpoint
                except APIError as e:
                    logger.error(f"Erro de API ao inicializar GeminiClient: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Erro inesperado ao inicializar GeminiClient: {e}")
                    raise
            return self._client

    async def get_client(self) -> GeminiClient:
        if self._client is None or not self._client.running:
            return await self._initialize_client()
        # Se o cliente já foi inicializado e está rodando, mas auto_close foi True na lib,
        # e o close_delay passou, ele pode ter sido fechado.
        # A lógica de `running` na GeminiClient deve cobrir isso.
        # Se você definir auto_close=False e auto_refresh=True na init, ele deve permanecer ativo.
        return self._client

    async def generate_content(self, prompt: str, model_name: Optional[str] = None) -> ModelOutput:
        """
        Gera conteúdo usando o Gemini.
        O parâmetro model_name aqui é para o modelo Gemini, não o modelo OpenAI.
        A Gemini-API tem sua própria forma de especificar modelos se necessário.
        """
        client = await self.get_client()
        try:
            # A biblioteca gemini-webapi pode ter seu próprio parâmetro de modelo
            # Veja a documentação da gemini-webapi para como especificar modelos Gemini
            # Exemplo: from gemini_webapi.constants import Model
            # response = await client.generate_content(prompt, model=Model.G_2_5_FLASH)
            logger.debug(f"Enviando prompt para Gemini: '{prompt[:100]}...'")
            response = await client.generate_content(prompt)
            logger.debug(f"Resposta recebida do Gemini: '{response.text[:100]}...'")
            return response
        except ReadTimeout as e: # Import ReadTimeout from httpx
             logger.error(f"Timeout ao chamar Gemini: {e}")
             raise # Ou trate como um erro específico do proxy
        except APIError as e:
            logger.error(f"Erro da API Gemini: {e}")
            # Pode ser que o cliente precise ser re-inicializado se for um erro de autenticação
            if "authentication" in str(e).lower() or "cookie" in str(e).lower():
                 logger.warning("Possível problema de cookie, forçando re-inicialização na próxima chamada.")
                 self._client = None # Força re-inicialização
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao gerar conteúdo com Gemini: {e}")
            raise

# Instância global do serviço para ser usada pela aplicação FastAPI
gemini_service_instance = GeminiService()
