# tests/test_errors.py
import anthropic
import httpx
import pytest

from holodok_agent.llm.errors import LLMError, to_llm_error

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=REQUEST)


def test_rate_limit_error_maps_to_russian_text():
    exc = anthropic.RateLimitError("rate limited", response=_response(429), body=None)

    result = to_llm_error(exc)

    assert isinstance(result, LLMError)
    assert result.user_message == (
        "Слишком много запросов к ИИ подряд. Подождите минуту и попробуйте снова."
    )


def test_api_timeout_error_maps_to_russian_text():
    exc = anthropic.APITimeoutError(request=REQUEST)

    result = to_llm_error(exc)

    assert result.user_message == (
        "Не удалось связаться с ИИ — похоже, проблемы с сетью. Попробуйте ещё раз через минуту."
    )


def test_api_connection_error_maps_to_russian_text():
    exc = anthropic.APIConnectionError(message="connection broke", request=REQUEST)

    result = to_llm_error(exc)

    assert result.user_message == (
        "Не удалось связаться с ИИ — похоже, проблемы с сетью. Попробуйте ещё раз через минуту."
    )


def test_authentication_error_maps_to_russian_text():
    exc = anthropic.AuthenticationError("bad key", response=_response(401), body=None)

    result = to_llm_error(exc)

    assert result.user_message == (
        "Не получается обратиться к ИИ из-за настроек доступа. "
        "Я записал проблему в журнал — попробуйте позже."
    )


def test_bad_request_error_maps_to_russian_text():
    exc = anthropic.BadRequestError("too long", response=_response(400), body=None)

    result = to_llm_error(exc)

    assert result.user_message == (
        "Не получилось обработать запрос — возможно, текст слишком длинный. Попробуйте короче."
    )


def test_generic_api_status_error_maps_to_russian_text():
    exc = anthropic.APIStatusError("server error", response=_response(500), body=None)

    result = to_llm_error(exc)

    assert result.user_message == "ИИ временно недоступен. Попробуйте ещё раз чуть позже."


def test_unknown_exception_maps_to_fallback_russian_text():
    exc = Exception("something unexpected")

    result = to_llm_error(exc)

    assert result.user_message == (
        "Извините, не получилось подготовить текст. Попробуйте ещё раз через пару минут."
    )


def test_llm_error_keeps_technical_detail_in_args():
    exc = anthropic.RateLimitError("rate limited", response=_response(429), body=None)

    result = to_llm_error(exc)

    assert "rate limited" in str(result.args)
