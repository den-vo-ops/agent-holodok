# tests/test_style.py
from unittest.mock import MagicMock

import pytest

from holodok_agent.llm.style import analyze_style, _parse_style_response


def test_analyze_style_raises_on_empty_samples():
    with pytest.raises(ValueError, match="хотя бы один"):
        analyze_style(MagicMock(), [])


def test_parse_style_response_extracts_three_sections():
    raw = (
        "ТОН: дружелюбный, простой\n"
        "ЛЕКСИКА: короткие слова, без канцелярита\n"
        "СТРУКТУРА: проблема-решение-цена"
    )

    result = _parse_style_response(raw)

    assert result["tone_summary"] == "дружелюбный, простой"
    assert result["lexicon_notes"] == "короткие слова, без канцелярита"
    assert result["structure_notes"] == "проблема-решение-цена"


def test_parse_style_response_appends_continuation_lines():
    raw = "ТОН: дружелюбный\nи открытый\nЛЕКСИКА: просто\nСТРУКТУРА: списком"

    result = _parse_style_response(raw)

    assert result["tone_summary"] == "дружелюбный и открытый"


def test_parse_style_response_raises_when_section_missing():
    with pytest.raises(ValueError, match="ЛЕКСИКА"):
        _parse_style_response("ТОН: дружелюбный\nСТРУКТУРА: просто")


def test_analyze_style_calls_client_with_joined_samples_and_parses_result():
    mock_client = MagicMock()
    mock_client.complete.return_value = "ТОН: деловой\nЛЕКСИКА: техническая\nСТРУКТУРА: списком"

    result = analyze_style(mock_client, ["текст 1", "текст 2"])

    assert result == {
        "tone_summary": "деловой",
        "lexicon_notes": "техническая",
        "structure_notes": "списком",
    }
    args, kwargs = mock_client.complete.call_args
    assert "текст 1" in kwargs["user_message"]
    assert "текст 2" in kwargs["user_message"]
