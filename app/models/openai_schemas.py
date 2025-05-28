# Adicionar importações no topo do arquivo se necessário:
import time
import uuid
from typing import List

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any, Union

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    # Adicionar outros campos como 'tool_calls', 'tool_call_id' se necessário

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1) # Gemini-API retorna múltiplos candidatos, mas nós formataremos 1 escolha
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    # Adicionar outros campos se precisar de maior compatibilidade

# Para respostas não-streaming
class ResponseMessage(BaseModel):
    role: Literal["assistant"]
    content: Optional[str] = None
    # tool_calls: Optional[List[Any]] = None # Se for implementar tools

class Choice(BaseModel):
    index: int
    message: ResponseMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None
    # logprobs: Optional[Any] = None # Se for implementar logprobs

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:10]}") # Importar uuid
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time())) # Importar time
    model: str
    choices: List[Choice]
    usage: Usage
    # system_fingerprint: Optional[str] = None # Adicionar se necessário

# Para respostas em streaming
class DeltaMessage(BaseModel):
    role: Optional[Literal["assistant"]] = None
    content: Optional[str] = None
    # tool_calls: Optional[List[Any]] = None

class StreamingChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None
    # logprobs: Optional[Any] = None

class ChatCompletionChunkResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:10]}") # Pode ser o mesmo ID da primeira parte
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[StreamingChoice]
    # usage: Optional[Usage] = None # Usage geralmente não é enviado em chunks, mas pode ser no último.
    # system_fingerprint: Optional[str] = None

class OpenAIErrorDetail(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None

class OpenAIErrorResponse(BaseModel):
    error: OpenAIErrorDetail

class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "openai" # Podemos simular isso, ou usar "gemini-proxy"
    # Adicionar outros campos se desejar, como 'permission', 'root', 'parent'
    # mas os acima são os mais comuns.

class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelCard]
