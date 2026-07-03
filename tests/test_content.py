# tests/test_content.py
from unittest.mock import MagicMock

import pytest

from holodok_agent.llm.content import build_system_prompt, generate_content, SCENARIO_INSTRUCTIONS

STYLE_PROFILE = {
    "tone_summary": "дружелюбный",
    "lexicon_notes": "просто",
    "structure_notes": "проблема-решение",
}


def test_build_system_prompt_includes_style_and_rules():
    prompt = build_system_prompt(STYLE_PROFILE, ["никогда не демпинговать"])

    assert "дружелюбный" in prompt
    assert "просто" in prompt
    assert "проблема-решение" in prompt
    assert "никогда не демпинговать" in prompt


def test_build_system_prompt_handles_no_rules():
    prompt = build_system_prompt(STYLE_PROFILE, [])
    assert "правил пока нет" in prompt


def test_generate_content_raises_for_unknown_scenario():
    with pytest.raises(ValueError, match="Неизвестный сценарий"):
        generate_content(MagicMock(), STYLE_PROFILE, [], "unknown_scenario", "")


@pytest.mark.parametrize("scenario", list(SCENARIO_INSTRUCTIONS.keys()))
def test_generate_content_calls_client_for_each_known_scenario(scenario):
    mock_client = MagicMock()
    mock_client.complete.return_value = "готовый текст"

    result = generate_content(mock_client, STYLE_PROFILE, [], scenario, "входные данные")

    assert result == "готовый текст"
    mock_client.complete.assert_called_once()
    _, kwargs = mock_client.complete.call_args
    assert SCENARIO_INSTRUCTIONS[scenario] in kwargs["user_message"]


def test_generate_content_without_user_input_uses_instruction_only():
    mock_client = MagicMock()
    mock_client.complete.return_value = "идеи"

    generate_content(mock_client, STYLE_PROFILE, [], "idea", "")

    _, kwargs = mock_client.complete.call_args
    assert kwargs["user_message"] == SCENARIO_INSTRUCTIONS["idea"]
