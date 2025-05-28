import time
import uuid
from typing import Optional, Dict, Any, AsyncGenerator, List

from app.models.openai_schemas import (
    ChatCompletionResponse,
    Choice,
    ResponseMessage,
    Usage,
    ChatCompletionChunkResponse,
    StreamingChoice,
    DeltaMessage,
)
from gemini_webapi.types import ModelOutput # Supondo que ModelOutput está acessível

# Placeholder para contagem de tokens, já que Gemini-API não fornece diretamente.
# Você pode querer integrar uma biblioteca como 'tiktoken' se precisar de contagens mais precisas,
# mas lembre-se que a tokenização do Gemini é diferente da do OpenAI.
def count_tokens(text: Optional[str]) -> int:
    if text is None:
        return 0
    # Estimativa muito simples, substitua por algo melhor se necessário
    return len(text.split())


def format_to_openai_response(
    prompt_text: Optional[str],
    gemini_response_text: str,
    model_name: str, # Modelo solicitado ou o modelo Gemini usado
    original_request_id: Optional[str] = None # Para manter o mesmo ID se gerado antes
) -> ChatCompletionResponse:
    """
    Formata a resposta completa do Gemini no padrão OpenAI ChatCompletionResponse.
    """
    completion_id = original_request_id or f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_timestamp = int(time.time())

    prompt_tokens = count_tokens(prompt_text)
    completion_tokens = count_tokens(gemini_response_text)
    total_tokens = prompt_tokens + completion_tokens

    return ChatCompletionResponse(
        id=completion_id,
        object="chat.completion",
        created=created_timestamp,
        model=model_name,
        choices=[
            Choice(
                index=0,
                message=ResponseMessage(role="assistant", content=gemini_response_text),
                finish_reason="stop", # Assumindo que o Gemini sempre para quando termina
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )

async def generate_openai_streaming_chunks(
    gemini_response_text: str,
    model_name: str,
    original_request_id: Optional[str] = None,
    # gemini_model_output: Optional[ModelOutput] = None # Se precisar de mais dados do ModelOutput
) -> AsyncGenerator[str, None]:
    """
    Gera chunks de resposta no formato OpenAI ChatCompletionChunkResponse para streaming.
    Este é um streaming "artificial" da resposta completa.
    """
    completion_id = original_request_id or f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_timestamp = int(time.time())

    # Chunk inicial (opcional, algumas implementações enviam um delta com role)
    # yield f"data: {ChatCompletionChunkResponse(id=completion_id, model=model_name, created=created_timestamp, choices=[StreamingChoice(index=0, delta=DeltaMessage(role='assistant'), finish_reason=None)]).model_dump_json(exclude_none=True)}\n\n"

    # Simplesmente dividindo por palavras para simular o streaming.
    # Para uma melhor simulação, você pode querer quebrar em tokens ou frases menores.
    words = gemini_response_text.split(" ")
    accumulated_content = ""

    for i, word in enumerate(words):
        delta_content = word + (" " if i < len(words) - 1 else "")
        accumulated_content += delta_content

        chunk = ChatCompletionChunkResponse(
            id=completion_id,
            model=model_name,
            created=created_timestamp, # Pode ser o mesmo timestamp ou atualizar
            choices=[
                StreamingChoice(
                    index=0,
                    delta=DeltaMessage(content=delta_content),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
        # Pequeno delay para tornar o streaming mais perceptível, remova para produção
        # await asyncio.sleep(0.02)

    # Chunk final com finish_reason
    final_chunk = ChatCompletionChunkResponse(
        id=completion_id,
        model=model_name,
        created=created_timestamp,
        choices=[
            StreamingChoice(
                index=0,
                delta=DeltaMessage(), # Delta vazio
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {final_chunk.model_dump_json(exclude_none=True)}\n\n"
    yield "data: [DONE]\n\n"
