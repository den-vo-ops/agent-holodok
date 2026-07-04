from holodok_agent.bot.main import build_bot_commands


def test_bot_commands_cover_start_settov_help():
    commands = {c.command: c.description for c in build_bot_commands()}
    assert set(commands) == {"start", "settov", "help"}
    assert all(desc.strip() for desc in commands.values())
