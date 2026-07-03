# tests/test_rules.py
from holodok_agent.rules import extract_rule_from_message


def test_extract_rule_from_message_with_comma():
    result = extract_rule_from_message("запомни, я никогда не даю скидку больше 10%")
    assert result == "я никогда не даю скидку больше 10%"


def test_extract_rule_from_message_case_insensitive():
    result = extract_rule_from_message("Запомни: гарантия всегда 3 месяца")
    assert result == "гарантия всегда 3 месяца"


def test_extract_rule_from_message_without_separator():
    result = extract_rule_from_message("запомни цена выезда всегда 300 рублей")
    assert result == "цена выезда всегда 300 рублей"


def test_extract_rule_from_message_returns_none_when_empty():
    assert extract_rule_from_message("запомни") is None
    assert extract_rule_from_message("запомни,   ") is None


def test_extract_rule_from_message_returns_none_for_unrelated_text():
    assert extract_rule_from_message("привет, как дела?") is None
