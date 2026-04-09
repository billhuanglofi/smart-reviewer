"""AI handler using LiteLLM for multi-model support."""

from __future__ import annotations

import logging
from typing import Optional

import litellm

from smart_reviewer.config import ReviewConfig

logger = logging.getLogger(__name__)


class AIHandler:
    """Send chat-completion requests through LiteLLM.

    Parameters:
        config: Application configuration (carries API keys, model defaults).
    """

    def __init__(self, config: ReviewConfig) -> None:
        self.config = config
        if config.openai_api_key:
            litellm.api_key = config.openai_api_key
        litellm.drop_params = True

        if not config.ssl_verify:
            litellm.ssl_verify = False

        if config.llm_api_base:
            litellm.api_base = config.llm_api_base

    async def chat_completion(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Request a chat completion and return the assistant text.

        Parameters:
            system: The system prompt.
            user: The user prompt.
            model: Override for the configured model.
            temperature: Override for the configured temperature.

        Returns:
            The text content of the first choice.
        """
        model = model or self.config.model
        temperature = temperature if temperature is not None else self.config.temperature

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs: dict[str, object] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_tokens,
        }

        # Per-request api_base (takes precedence over litellm.api_base when
        # the caller has configured a custom endpoint).
        if self.config.llm_api_base:
            kwargs["api_base"] = self.config.llm_api_base

        try:
            response = await litellm.acompletion(**kwargs)
            text: str = response.choices[0].message.content
            logger.debug("AI response length: %d characters", len(text))
            return text
        except Exception:
            logger.exception("AI chat completion failed")
            raise
