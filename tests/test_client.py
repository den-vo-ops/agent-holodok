import logging
from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from holodok_agent.llm.client import ClaudeClient
from holodok_agent.llm.errors import LLMError


def test_complete_sends_correct_request_and_extracts_text():
    with patch("holodok_agent.llm.client.Anthropic") as mock_anthropic_cls:
        mock_sdk_client = MagicMock()
        mock_anthropic_cls.return_value = mock_sdk_client

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Готовый текст ответа"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_sdk_client.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key", model="claude-opus-4-8")
        result = client.complete(system="системный промпт", user_message="пользовательский запрос")

        assert result == "Готовый текст ответа"
        mock_anthropic_cls.assert_called_once_with(api_key="test-key")
        mock_sdk_client.messages.create.assert_called_once_with(
            model="claude-opus-4-8",
            max_tokens=1024,
            system="системный промпт",
            messages=[{"role": "user", "content": "пользовательский запрос"}],
        )


def test_complete_joins_multiple_text_blocks():
    with patch("holodok_agent.llm.client.Anthropic") as mock_anthropic_cls:
        mock_sdk_client = MagicMock()
        mock_anthropic_cls.return_value = mock_sdk_client

        block_a = MagicMock(type="text", text="Часть 1. ")
        block_b = MagicMock(type="text", text="Часть 2.")
        mock_response = MagicMock()
        mock_response.content = [block_a, block_b]
        mock_sdk_client.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="k", model="claude-opus-4-8")
        result = client.complete(system="s", user_message="u")

        assert result == "Часть 1. Часть 2."


def test_complete_raises_llm_error_and_logs_traceback_on_rate_limit(caplog):
    with patch("holodok_agent.llm.client.Anthropic") as mock_anthropic_cls:
        mock_sdk_client = MagicMock()
        mock_anthropic_cls.return_value = mock_sdk_client

        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(status_code=429, request=request)
        mock_sdk_client.messages.create.side_effect = anthropic.RateLimitError(
            "rate limited", response=response, body=None
        )

        client = ClaudeClient(api_key="k", model="claude-opus-4-8")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(LLMError) as exc_info:
                client.complete(system="s", user_message="u")

        assert "слишком много запросов" in exc_info.value.user_message.lower()
        assert any(
            record.levelno == logging.ERROR and record.exc_info is not None
            for record in caplog.records
        )
