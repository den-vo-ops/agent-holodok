# holodok_agent/rules.py
import re

_REMEMBER_PATTERN = re.compile(r"^\s*запомни[,:]?\s*(.+)$", re.IGNORECASE | re.DOTALL)


def extract_rule_from_message(text: str) -> str | None:
    match = _REMEMBER_PATTERN.match(text)
    if not match:
        return None
    rule = match.group(1).strip()
    return rule or None
