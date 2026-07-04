# holodok_agent/llm/style.py
from holodok_agent.llm.client import GroqClient

STYLE_ANALYSIS_SYSTEM_PROMPT = (
    "Ты — лингвист-аналитик. Тебе дают несколько текстов объявлений/постов одного автора. "
    "Опиши стиль автора тремя блоками, каждый — 2-4 предложения на русском: "
    "ТОН, ЛЕКСИКА, СТРУКТУРА. Не придумывай факты про автора, только наблюдения о тексте. "
    "Ответь строго в формате:\nТОН: ...\nЛЕКСИКА: ...\nСТРУКТУРА: ..."
)

_MARKERS = {
    "ТОН:": "tone_summary",
    "ЛЕКСИКА:": "lexicon_notes",
    "СТРУКТУРА:": "structure_notes",
}


def analyze_style(client: GroqClient, samples: list[str]) -> dict:
    if not samples:
        raise ValueError("Нужен хотя бы один образец текста для анализа стиля")
    joined = "\n\n---\n\n".join(samples)
    raw = client.complete(system=STYLE_ANALYSIS_SYSTEM_PROMPT, user_message=joined)
    return _parse_style_response(raw)


def _parse_style_response(raw: str) -> dict:
    sections = {"tone_summary": "", "lexicon_notes": "", "structure_notes": ""}
    current_key = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for marker, key in _MARKERS.items():
            if stripped.startswith(marker):
                current_key = key
                sections[key] = stripped[len(marker):].strip()
                matched = True
                break
        if not matched and current_key:
            sections[current_key] = (sections[current_key] + " " + stripped).strip()

    for key, value in sections.items():
        if not value:
            label = next(marker for marker, k in _MARKERS.items() if k == key)
            raise ValueError(f"Не удалось разобрать ответ модели: отсутствует секция {label}")
    return sections
