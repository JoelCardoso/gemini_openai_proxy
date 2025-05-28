# -*- coding: utf-8 -*-
import app.core.logging_config
from loguru import logger
import uuid
import time
from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
from httpx import ReadTimeout as HttpxReadTimeout
from app.models.openai_schemas import ModelCard, ModelListResponse # Mantida a importação que você adicionou


# Importações do projeto
from app.core.config import settings
from app.models.openai_schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIErrorResponse,
    OpenAIErrorDetail,
) # Nota: ModelCard e ModelListResponse já estavam importados acima, o Pydantic schemas foram agrupados.
  # Vou manter sua estrutura de importação para minimizar alterações não solicitadas.
from app.services.gemini_service import gemini_service_instance
from app.utils.openai_formatter import (
    format_to_openai_response,
    generate_openai_streaming_chunks,
)

# Importações da gemini-webapi
from gemini_webapi import ChatSession
from gemini_webapi.constants import Model # Corrigido na interação anterior
from gemini_webapi.exceptions import (
    AuthError as GeminiAuthError,
    APIError as GeminiAPIError,
    GeminiError,
    UsageLimitExceeded as GeminiUsageLimitExceeded,
    ModelInvalid as GeminiModelInvalid,
    TemporarilyBlocked as GeminiTemporarilyBlocked,
    TimeoutError as GeminiTimeoutError,
)

# Dicionário para armazenar sessões de chat ativas, mapeando API Key para ChatSession
active_chat_sessions: dict[str, ChatSession] = {}

app = FastAPI(
    title="Gemini OpenAI-Compatible Proxy",
    version="0.1.0",
    description="Proxy para API Gemini com endpoints compatíveis com OpenAI /v1/chat/completions.",
)

# Esquema de segurança para o header de autorização
api_key_header_auth = APIKeyHeader(name="Authorization", auto_error=False)

# Validações de API Key
async def get_api_key(api_key_value: str = Depends(api_key_header_auth)) -> str:
    if not api_key_value:
        logger.warning("Authorization header ausente.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=OpenAIErrorResponse(
                error=OpenAIErrorDetail(
                    message="Authorization header is missing.",
                    type="authentication_error",
                    code="missing_authorization_header"
                )
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = api_key_value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Formato inválido do Authorization header: {api_key_value}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=OpenAIErrorResponse(
                error=OpenAIErrorDetail(
                    message="Invalid authorization header format. Expected 'Bearer <token>'.",
                    type="authentication_error",
                    code="invalid_authorization_format"
                )
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    if token not in settings.ALLOWED_API_KEYS:
        logger.warning(f"Token de API não autorizado: {token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=OpenAIErrorResponse(
                error=OpenAIErrorDetail(
                    message="Invalid API Key.",
                    type="authentication_error",
                    code="invalid_api_key"
                )
            ).model_dump(),
        )
    logger.info(f"Token de API validado com sucesso para: ...{token[-4:]}")
    return token

# --- Manipuladores de Exceção Globais ---
# (Handlers de exceção permanecem os mesmos que você já tinha)
@app.exception_handler(GeminiAuthError)
async def gemini_auth_exception_handler(request: Request, exc: GeminiAuthError):
    logger.error(f"Erro de autenticação com Gemini: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=401,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Authentication error with Gemini service (invalid or expired cookies?): {str(exc)}",
                type="authentication_error",
                code="gemini_auth_failure"
            )
        ).model_dump()
    )

@app.exception_handler(GeminiUsageLimitExceeded)
async def gemini_usage_limit_exception_handler(request: Request, exc: GeminiUsageLimitExceeded):
    logger.warning(f"Limite de uso do Gemini excedido: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=429,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Usage limit for the Gemini model has been exceeded: {str(exc)}",
                type="insufficient_quota",
                code="gemini_usage_limit"
            )
        ).model_dump()
    )

@app.exception_handler(GeminiModelInvalid)
async def gemini_model_invalid_exception_handler(request: Request, exc: GeminiModelInvalid):
    logger.warning(f"Modelo Gemini inválido: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=400,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"The specified Gemini model is invalid or unavailable: {str(exc)}",
                type="invalid_request_error",
                param="model",
                code="gemini_model_invalid"
            )
        ).model_dump()
    )

@app.exception_handler(GeminiTemporarilyBlocked)
async def gemini_temporarily_blocked_exception_handler(request: Request, exc: GeminiTemporarilyBlocked):
    logger.warning(f"Acesso ao Gemini temporariamente bloqueado: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=429,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Access to Gemini service temporarily blocked (possible IP block): {str(exc)}",
                type="rate_limit_exceeded",
                code="gemini_temporarily_blocked"
            )
        ).model_dump()
    )

@app.exception_handler(GeminiTimeoutError)
async def gemini_timeout_exception_handler(request: Request, exc: GeminiTimeoutError):
    logger.error(f"Timeout (Gemini lib) na comunicação com Gemini: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=504,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Timeout (Gemini library) while communicating with Gemini service: {str(exc)}",
                type="api_error",
                code="gemini_timeout"
            )
        ).model_dump()
    )

@app.exception_handler(HttpxReadTimeout)
async def httpx_read_timeout_exception_handler(request: Request, exc: HttpxReadTimeout):
    logger.error(f"Timeout (httpx) na comunicação: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=504,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Timeout (httpx) while communicating with upstream service: {str(exc)}",
                type="api_error",
                code="upstream_read_timeout"
            )
        ).model_dump()
    )


@app.exception_handler(GeminiAPIError)
async def gemini_api_error_exception_handler(request: Request, exc: GeminiAPIError):
    logger.error(f"Erro da API Gemini (biblioteca): {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=502,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Error in the communication library for Gemini API: {str(exc)}",
                type="api_error",
                code="gemini_library_error"
            )
        ).model_dump()
    )

@app.exception_handler(GeminiError)
async def gemini_generic_error_exception_handler(request: Request, exc: GeminiError):
    logger.error(f"Erro genérico do Gemini: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Generic error while interacting with Gemini service: {str(exc)}",
                type="api_error",
                code="gemini_generic_error"
            )
        ).model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception(f"Erro interno não tratado: {exc} na rota {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message=f"Unexpected internal server error in proxy: {str(exc)}",
                type="api_error",
                code="internal_proxy_error"
            )
        ).model_dump()
    )

# --- Middleware ---
@app.middleware("http")
async def log_requests_responses(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    with logger.contextualize(request_id=request_id):
        logger.info(f"Requisição recebida: {request.method} {request.url.path} (Cliente: {request.client.host if request.client else 'N/A'})")
        if settings.LOG_LEVEL.upper() == "DEBUG":
            try:
                logger.debug(f"Headers da requisição: {dict(request.headers)}")
            except Exception as e:
                logger.warning(f"Não foi possível logar headers da requisição: {e}")

        start_time = time.time()
        response_sent = False
        try:
            response = await call_next(request)
            response_sent = True
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Erro durante o processamento da requisição {request.method} {request.url.path} "
                f"(Tempo: {process_time:.2f}ms). Exceção será propagada."
            )
            raise

        process_time = (time.time() - start_time) * 1000

        if response_sent:
            status_code = response.status_code
            current_response_headers = {}
            if hasattr(response, "headers") and isinstance(response.headers, dict):
                current_response_headers = response.headers
            elif isinstance(response, Response):
                current_response_headers = response.headers

            current_response_headers["X-Request-ID"] = request_id

            log_message_suffix = f"(Tempo: {process_time:.2f}ms)"
            if isinstance(response, StreamingResponse):
                logger.info(f"Resposta enviada: {status_code} para {request.method} {request.url.path} (Streaming) {log_message_suffix}")
            else:
                logger.info(f"Resposta enviada: {status_code} para {request.method} {request.url.path} {log_message_suffix}")
        return response

# --- Evento de Startup ---
@app.on_event("startup")
async def startup_event():
    logger.info("Aplicação iniciando...")
    try:
        await gemini_service_instance.get_client()
        logger.info("Verificação inicial do cliente Gemini concluída.")
    except Exception as e:
        logger.critical(f"Falha ao inicializar o cliente Gemini durante o startup: {e}")

# --- Endpoints ---
@app.get("/health", summary="Verifica a saúde da aplicação", tags=["Health"])
async def health_check():
    logger.info("Health check solicitado.")
    return {"status": "ok"}

@app.get("/dashboard/billing/usage", include_in_schema=False, tags=["Mock Endpoints"])
async def mock_billing_usage(start_date: str, end_date: str):
    logger.info(f"Recebida requisição mock para /dashboard/billing/usage?start_date={start_date}&end_date={end_date}")
    return {
        "object": "list",
        "daily_costs": [],
        "total_usage": 0.00
    }

@app.get("/v1/models",
         response_model=ModelListResponse,
         summary="Lista os modelos atualmente disponíveis.",
         tags=["Models"])
async def list_models():
    model_data = []
    created_timestamp = int(time.time())

    if settings.OPENAI_TO_GEMINI_MODEL_MAP:
        for openai_model_name in settings.OPENAI_TO_GEMINI_MODEL_MAP.keys():
            if not any(m.id == openai_model_name for m in model_data):
                model_data.append(ModelCard(
                    id=openai_model_name,
                    created=created_timestamp,
                    owned_by="proxy-engine"
                ))

    if not settings.OPENAI_TO_GEMINI_MODEL_MAP and settings.DEFAULT_GEMINI_MODEL_NAME != "unspecified":
        generic_default_id = "gpt-3.5-turbo"
        if not any(m.id == generic_default_id for m in model_data):
             model_data.append(ModelCard(id=generic_default_id, created=created_timestamp, owned_by="proxy-engine"))

    logger.info(f"Listando modelos: {[model.id for model in model_data]}")
    return ModelListResponse(data=model_data)

@app.post("/v1/chat/completions",
        summary="Gera uma resposta de chat completion",
        response_model=ChatCompletionResponse,
        responses={
            400: {"model": OpenAIErrorResponse},
            401: {"model": OpenAIErrorResponse},
            403: {"model": OpenAIErrorResponse},
            500: {"model": OpenAIErrorResponse},
            502: {"model": OpenAIErrorResponse},
            504: {"model": OpenAIErrorResponse},
        },
        tags=["Chat Completions"])
async def chat_completions(
    request_payload: ChatCompletionRequest,
    http_request_object: Request, # Renomeado para evitar conflito com 'request' dos handlers
    api_key_token: str = Depends(get_api_key)
):
    with open("request_payloads.log", "a", encoding="utf-8") as log_file:
        log_file.write(request_payload.model_dump_json(indent=2, exclude_none=True) + "\n")

    if settings.LOG_LEVEL.upper() == "DEBUG":
        logger.debug(f"Payload da requisição: {request_payload.model_dump_json(indent=2, exclude_none=True)}")

    if not request_payload.messages:
        logger.warning("Requisição sem mensagens.")
        raise HTTPException(status_code=400, detail=OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message="messages is a required field and cannot be empty.",
                type="invalid_request_error",
                param="messages",
                code="missing_messages"
            )
        ).model_dump())

    chat_session: ChatSession
    gemini_client_instance = await gemini_service_instance.get_client()

    requested_openai_model = request_payload.model
    gemini_model_name_to_use = settings.DEFAULT_GEMINI_MODEL_NAME

    if requested_openai_model in settings.OPENAI_TO_GEMINI_MODEL_MAP:
        gemini_model_name_to_use = settings.OPENAI_TO_GEMINI_MODEL_MAP[requested_openai_model]
        logger.info(f"Modelo OpenAI '{requested_openai_model}' mapeado para modelo Gemini '{gemini_model_name_to_use}'.")
    else:
        logger.info(f"Modelo OpenAI '{requested_openai_model}' não encontrado no mapa. Usando modelo Gemini padrão: '{gemini_model_name_to_use}'.")

    try:
        internal_gemini_model_enum = Model.from_name(gemini_model_name_to_use)
    except ValueError as e:
        logger.warning(f"Nome do modelo Gemini configurado ('{gemini_model_name_to_use}') é inválido: {e}. Usando 'unspecified' como fallback.")
        internal_gemini_model_enum = Model.UNSPECIFIED

    # >>> INÍCIO DA LÓGICA DO SYSTEM PROMPT <<<
    is_new_session_instance = False
    if api_key_token not in active_chat_sessions:
        is_new_session_instance = True
        logger.info(f"Criando nova ChatSession para API Key: ...{api_key_token[-4:]} usando modelo Gemini interno: {internal_gemini_model_enum.name}")
        chat_session = gemini_client_instance.start_chat(model=internal_gemini_model_enum)
        active_chat_sessions[api_key_token] = chat_session
    else:
        chat_session = active_chat_sessions[api_key_token]
        if chat_session.geminiclient != gemini_client_instance or chat_session.model != internal_gemini_model_enum:
            is_new_session_instance = True # Tratar como nova instância para o system prompt
            logger.warning(
                f"Recriando ChatSession para API Key ...{api_key_token[-4:]}. "
                f"Motivo: {'Mudança de cliente Gemini' if chat_session.geminiclient != gemini_client_instance else 'Mudança de modelo interno desejado (' + (chat_session.model.name if chat_session.model else 'N/A') + ' -> ' + internal_gemini_model_enum.name + ')'}. "
            )
            chat_session = gemini_client_instance.start_chat(metadata=chat_session.metadata, model=internal_gemini_model_enum)
            active_chat_sessions[api_key_token] = chat_session

    system_prompt_content = None
    for msg in request_payload.messages:
        if msg.role == "system" and msg.content:
            system_prompt_content = msg.content
            break

    current_user_prompt = None # Renomeado de temp_user_prompt para clareza
    for message in reversed(request_payload.messages):
        if message.role == "user" and message.content:
            current_user_prompt = message.content
            break

    if not current_user_prompt:
        if request_payload.messages and request_payload.messages[-1].content:
            current_user_prompt = request_payload.messages[-1].content
        else:
            logger.warning("Requisição sem prompt de usuário válido.")
            # (HTTPException já existente)
            raise HTTPException(status_code=400, detail=OpenAIErrorResponse(
                error=OpenAIErrorDetail(
                    message="Could not extract a valid prompt from the messages provided.",
                    type="invalid_request_error",
                    param="messages",
                    code="invalid_prompt"
                )
            ).model_dump())

    final_prompt_to_send = current_user_prompt
    if is_new_session_instance and system_prompt_content:
        logger.info(f"Primeiro turno para sessão ...{api_key_token[-4:]}. Prefixando com system prompt.")
        final_prompt_to_send = f"{system_prompt_content}\n\n{current_user_prompt}"
    # >>> FIM DA LÓGICA DO SYSTEM PROMPT <<<

    # Sanitize para o log, se necessário (você tinha safe_prompt antes, mantendo a ideia)
    safe_prompt_to_log = final_prompt_to_send.replace("<", "&lt;").replace(">", "&gt;")
    logger.info(f"Prompt final para Gemini (via ChatSession ...{api_key_token[-4:]}): '{safe_prompt_to_log[:200]}...'")

    try:
        gemini_model_output = await chat_session.send_message(final_prompt_to_send)
    except GeminiModelInvalid as e:
        logger.error(f"Erro de Modelo Gemini Inválido com ChatSession para API Key ...{api_key_token[-4:]} usando modelo {chat_session.model.name if chat_session.model else 'N/A'}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro ao chamar Gemini com ChatSession para API Key ...{api_key_token[-4:]}: {e}")
        raise

    gemini_response_text = gemini_model_output.text

    if not gemini_response_text and not gemini_model_output.images:
        logger.warning("Gemini retornou uma resposta vazia via ChatSession.")
        gemini_response_text = ""

    response_chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    if request_payload.stream:
        logger.info("Iniciando streaming de resposta via ChatSession.")
        return StreamingResponse(
            generate_openai_streaming_chunks(
                gemini_response_text=gemini_response_text,
                model_name=request_payload.model,
                original_request_id=response_chat_id
            ),
            media_type="text/event-stream"
        )
    else:
        logger.info("Formatando resposta não-streaming via ChatSession.")
        openai_response = format_to_openai_response(
            prompt_text=current_user_prompt, # Usar o prompt do usuário original do turno atual
            gemini_response_text=gemini_response_text,
            model_name=request_payload.model,
            original_request_id=response_chat_id
        )
        if settings.LOG_LEVEL.upper() == "DEBUG":
            logger.debug(f"Resposta OpenAI formatada (ChatSession): {openai_response.model_dump_json(indent=2, exclude_none=True)}")
        return openai_response
