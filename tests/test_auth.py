from holodok_agent.bot.auth import is_owner


def test_is_owner_true_for_matching_id():
    assert is_owner(123, 123) is True


def test_is_owner_false_for_other_id():
    assert is_owner(456, 123) is False
