# tests/test_keyboards.py
import pytest

from holodok_agent.bot.keyboards import (
    build_scenario_menu,
    parse_scenario_callback,
    build_regenerate_and_publish_keyboard,
    parse_draft_callback,
)


def test_build_scenario_menu_has_four_buttons_with_expected_callbacks():
    menu = build_scenario_menu()
    buttons = [btn for row in menu.inline_keyboard for btn in row]

    callbacks = {btn.callback_data for btn in buttons}
    assert callbacks == {"scenario:vk_post", "scenario:avito_ad", "scenario:review_reply", "scenario:idea"}


def test_parse_scenario_callback_extracts_key():
    assert parse_scenario_callback("scenario:idea") == "idea"


def test_parse_scenario_callback_rejects_unknown_prefix():
    with pytest.raises(ValueError):
        parse_scenario_callback("publish:5")


def test_build_regenerate_and_publish_keyboard_has_two_buttons():
    keyboard = build_regenerate_and_publish_keyboard(42)
    buttons = keyboard.inline_keyboard[0]

    assert buttons[0].callback_data == "regen:42"
    assert buttons[1].callback_data == "publish:42"


def test_parse_draft_callback_extracts_action_and_id():
    assert parse_draft_callback("publish:42") == ("publish", 42)
    assert parse_draft_callback("regen:7") == ("regen", 7)


def test_parse_draft_callback_rejects_bad_id():
    with pytest.raises(ValueError):
        parse_draft_callback("publish:abc")


def test_parse_draft_callback_rejects_unknown_action():
    with pytest.raises(ValueError):
        parse_draft_callback("delete:1")
