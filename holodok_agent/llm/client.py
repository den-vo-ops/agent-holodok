import logging

import groq
from groq import Groq

from holodok_agent.llm.errors import to_llm_error

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def complete(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
            )
        except groq.APIError as exc:
            logger.exception("Groq API call failed")
            raise to_llm_error(exc) from exc
        return response.choices[0].message.content or ""
