from unittest.mock import MagicMock, patch

from holodok_agent.llm.client import ClaudeClient


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
