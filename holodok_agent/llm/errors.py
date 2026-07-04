# holodok_agent/llm/errors.py
"""Domain error type for LLM failures, with ready-to-show Russian user messages."""
import groq

_RATE_LIMIT_MESSAGE = "Слишком много запросов к ИИ подряд. Подождите минуту и попробуйте снова."
_CONNECTIVITY_MESSAGE = (
    "Не удалось связаться с ИИ — похоже, проблемы с сетью. Попробуйте ещё раз через минуту."
)
_AUTH_MESSAGE = (
    "Не получается обратиться к ИИ из-за настроек доступа. "
    "Я записал проблему в журнал — попробуйте позже."
)
_BAD_REQUEST_MESSAGE = (
    "Не получилось обработать запрос — возможно, текст слишком длинный. Попробуйте короче."
)
_STATUS_ERROR_MESSAGE = "ИИ временно недоступен. Попробуйте ещё раз чуть позже."

# Public: reused by the global aiogram error handler (bot/main.py) as the last-resort
# message for failures that never reached GroqClient.complete (e.g. bugs in handler code).
FALLBACK_MESSAGE = "Извините, не получилось подготовить текст. Попробуйте ещё раз через пару минут."


class LLMError(Exception):
    """Raised when a call to the LLM fails, carrying a ready Russian message for the user."""

    def __init__(self, *args: object, user_message: str) -> None:
        super().__init__(*args)
        self.user_message = user_message


def to_llm_error(exc: Exception) -> LLMError:
    """Map a Groq SDK exception (or any other) to an LLMError with a Russian user message."""
    if isinstance(exc, groq.RateLimitError):
        return LLMError(str(exc), user_message=_RATE_LIMIT_MESSAGE)
    if isinstance(exc, (groq.APITimeoutError, groq.APIConnectionError)):
        return LLMError(str(exc), user_message=_CONNECTIVITY_MESSAGE)
    if isinstance(exc, groq.AuthenticationError):
        return LLMError(str(exc), user_message=_AUTH_MESSAGE)
    if isinstance(exc, groq.BadRequestError):
        return LLMError(str(exc), user_message=_BAD_REQUEST_MESSAGE)
    if isinstance(exc, groq.APIStatusError):
        return LLMError(str(exc), user_message=_STATUS_ERROR_MESSAGE)
    return LLMError(str(exc), user_message=FALLBACK_MESSAGE)
