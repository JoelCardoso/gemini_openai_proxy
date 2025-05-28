# Em app/core/logging_config.py
import sys
import os
from loguru import logger
from app.core.config import settings

def robust_log_formatter(record: dict) -> str:
    """
    Formata um registro de log do Loguru de forma robusta,
    incluindo request_id se presente, ou "N/A" caso contrário.
    Retorna a string de log final, pronta para ser emitida, com tags de formatação Loguru.
    """
    # Obtém o request_id do 'extra' do registro, com "N/A" como padrão.
    request_id_val = record["extra"].get("request_id", "N/A")

    # Constrói a string de formato que o Loguru irá processar internamente
    # ao aplicar esta função como 'format'. Os placeholders {time}, {level.name},
    # {name}, {function}, {line}, {message} são do Loguru.
    # A f-string Python é usada aqui apenas para inserir o request_id_val de forma segura.
    # As tags de cor como <green>, <level>, <cyan>, <yellow> são interpretadas pelo Loguru
    # se colorize=True estiver ativo no handler.

    # O truque é que, quando 'format' é uma função, essa função deve retornar a string *final*.
    # O Loguru então apenas a imprime. Se quisermos que o Loguru processe placeholders
    # *depois* da nossa função, o 'format' deveria ser uma string.
    # Vamos construir a string com os valores do record diretamente.

    # Monta a string de log final com os valores do record
    # e as tags de formatação do Loguru para cores.
    log_parts = [
        f"<green>{record['time']:%Y-%m-%d %H:%M:%S.%f%z}</green>", # Formatação de tempo explícita
        f"<level>{record['level'].name: <8}</level>",
        f"<cyan>{record['name']}</cyan>:<cyan>{record['function']}</cyan>:<cyan>{record['line']}</cyan>",
        f"REQ_ID: <yellow>{request_id_val}</yellow>",
        f"<level>{record['message']}</level>" # Mensagem do log
    ]
    return " | ".join(log_parts) + "\n" # Adiciona uma nova linha no final

def setup_logging():
    """Configura os handlers do Loguru para a aplicação."""
    logger.remove() # Remove handlers padrão ou configurados anteriormente.

    logger.add(
        sys.stderr,
        format=robust_log_formatter, # Passa a FUNÇÃO como formatador
        level=settings.LOG_LEVEL.upper(),
        colorize=True, # Loguru tentará aplicar cores às tags na string retornada
        enqueue=True,
        diagnose=False
    )

    log_file_path = "logs/app_{time:YYYY-MM-DD}.log"
    try:
        os.makedirs("logs", exist_ok=True)
        logger.add(
            log_file_path,
            rotation="1 day",
            retention="7 days",
            compression="zip",
            level=settings.LOG_LEVEL.upper(),
            format=robust_log_formatter, # Passa a FUNÇÃO como formatador
            enqueue=True,
            # Para arquivos de log, colorize=False é geralmente preferido
            # para evitar códigos de escape de cor nos arquivos.
            colorize=False
        )
    except Exception as e:
        print(f"[CRITICAL LOGGING SETUP ERROR] Failed to configure file logging for '{log_file_path}': {e}", file=sys.stderr)

    logger.info("Configuração de logging aplicada (usando formatador de função).")

# Chama a configuração de logging quando este módulo é importado.
setup_logging()