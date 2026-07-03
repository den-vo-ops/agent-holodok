import logging

import anthropic
from anthropic import Anthropic

from holodok_agent.llm.errors import to_llm_error

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIError as exc:
            logger.exception("Claude API call failed")
            raise to_llm_error(exc) from exc
        return "".join(block.text for block in response.content if block.type == "text")
