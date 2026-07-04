import logging
from unittest.mock import MagicMock, patch

import groq
import httpx
import pytest

from holodok_agent.llm.client import GroqClient
from holodok_agent.llm.errors import LLMError


def _mock_response(text: str) -> MagicMock:
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_complete_sends_correct_request_and_extracts_text():
    with patch("holodok_agent.llm.client.Groq") as mock_groq_cls:
        mock_sdk_client = MagicMock()
        mock_groq_cls.return_value = mock_sdk_client
        mock_sdk_client.chat.completions.create.return_value = _mock_response(
            "Готовый текст ответа"
        )

        client = GroqClient(api_key="test-key", model="llama-3.3-70b-versatile")
        result = client.complete(system="системный промпт", user_message="пользовательский запрос")

        assert result == "Готовый текст ответа"
        mock_groq_cls.assert_called_once_with(api_key="test-key")
        mock_sdk_client.chat.completions.create.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": "системный промпт"},
                {"role": "user", "content": "пользовательский запрос"},
            ],
        )


def test_complete_returns_empty_string_when_content_is_none():
    with patch("holodok_agent.llm.client.Groq") as mock_groq_cls:
        mock_sdk_client = MagicMock()
        mock_groq_cls.return_value = mock_sdk_client
        mock_sdk_client.chat.completions.create.return_value = _mock_response(None)

        client = GroqClient(api_key="k", model="llama-3.3-70b-versatile")
        result = client.complete(system="s", user_message="u")

        assert result == ""


def test_complete_raises_llm_error_and_logs_traceback_on_rate_limit(caplog):
    with patch("holodok_agent.llm.client.Groq") as mock_groq_cls:
        mock_sdk_client = MagicMock()
        mock_groq_cls.return_value = mock_sdk_client

        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(status_code=429, request=request)
        mock_sdk_client.chat.completions.create.side_effect = groq.RateLimitError(
            "rate limited", response=response, body=None
        )

        client = GroqClient(api_key="k", model="llama-3.3-70b-versatile")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(LLMError) as exc_info:
                client.complete(system="s", user_message="u")

        assert "слишком много запросов" in exc_info.value.user_message.lower()
        assert any(
            record.levelno == logging.ERROR and record.exc_info is not None
            for record in caplog.records
        )
