# holodok_agent/llm/content.py
from holodok_agent.llm.client import GroqClient

SCENARIO_INSTRUCTIONS = {
    "vk_post": (
        "Напиши пост для ВКонтакте/Telegram от лица мастера по ремонту холодильников. "
        "Пост должен быть готов к публикации без правок."
    ),
    "avito_ad": (
        "Напиши короткий текст объявления для Авито/Юлы о ремонте холодильников. "
        "Кратко, по делу, с УТП в начале."
    ),
    "review_reply": (
        "Ниже — текст отзыва клиента. Напиши вежливый ответ от лица мастера: "
        "поблагодари, при негативе — извинись и предложи решение, без оправданий."
    ),
    "idea": (
        "Предложи 3 темы для поста или объявления на основе контекста ниже. "
        "Для каждой темы — одна строка с сутью и одна строка с тем, как её раскрыть."
    ),
}


def build_system_prompt(style_profile: dict, hard_rules: list[str]) -> str:
    rules_block = "\n".join(f"- {rule}" for rule in hard_rules) if hard_rules else "(правил пока нет)"
    return (
        "Ты пишешь тексты от лица мастера по ремонту холодильников в Симферополе, "
        "строго в его личном стиле, описанном ниже. Никогда не выходи за рамки жёстких правил.\n\n"
        f"ТОН: {style_profile['tone_summary']}\n"
        f"ЛЕКСИКА: {style_profile['lexicon_notes']}\n"
        f"СТРУКТУРА: {style_profile['structure_notes']}\n\n"
        f"Жёсткие правила:\n{rules_block}"
    )


def generate_content(
    client: GroqClient,
    style_profile: dict,
    hard_rules: list[str],
    scenario: str,
    user_input: str,
) -> str:
    if scenario not in SCENARIO_INSTRUCTIONS:
        raise ValueError(f"Неизвестный сценарий: {scenario}")
    system_prompt = build_system_prompt(style_profile, hard_rules)
    instruction = SCENARIO_INSTRUCTIONS[scenario]
    user_message = (
        f"{instruction}\n\nВходные данные от мастера:\n{user_input}" if user_input else instruction
    )
    return client.complete(system=system_prompt, user_message=user_message)
