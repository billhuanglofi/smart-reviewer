"""Tests for AIHandler."""

from __future__ import annotations

from unittest import mock

import pytest

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig


def _make_config(**overrides) -> ReviewConfig:
    defaults = {
        "github_token": "tok",
        "openai_api_key": "sk-test",
        "model": "gpt-4o",
        "max_tokens": 100,
        "temperature": 0.1,
    }
    defaults.update(overrides)
    return ReviewConfig(**defaults)


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_returns_text(self):
        config = _make_config()
        handler = AIHandler(config)

        mock_choice = mock.MagicMock()
        mock_choice.message.content = "Hello from AI"
        mock_response = mock.MagicMock()
        mock_response.choices = [mock_choice]

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(return_value=mock_response)
            result = await handler.chat_completion("sys", "usr")

        assert result == "Hello from AI"

    @pytest.mark.asyncio
    async def test_uses_override_model(self):
        config = _make_config()
        handler = AIHandler(config)

        mock_choice = mock.MagicMock()
        mock_choice.message.content = "ok"
        mock_response = mock.MagicMock()
        mock_response.choices = [mock_choice]

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(return_value=mock_response)
            await handler.chat_completion("s", "u", model="gpt-3.5-turbo")
            call_kwargs = mock_litellm.acompletion.call_args
            assert call_kwargs.kwargs["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_propagates_exception(self):
        config = _make_config()
        handler = AIHandler(config)

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(
                side_effect=RuntimeError("API error")
            )
            with pytest.raises(RuntimeError, match="API error"):
                await handler.chat_completion("s", "u")

    @pytest.mark.asyncio
    async def test_uses_override_temperature(self):
        config = _make_config()
        handler = AIHandler(config)

        mock_choice = mock.MagicMock()
        mock_choice.message.content = "ok"
        mock_response = mock.MagicMock()
        mock_response.choices = [mock_choice]

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(return_value=mock_response)
            await handler.chat_completion("s", "u", temperature=0.9)
            call_kwargs = mock_litellm.acompletion.call_args
            assert call_kwargs.kwargs["temperature"] == 0.9

    @pytest.mark.asyncio
    async def test_api_base_passed_when_configured(self):
        config = _make_config(llm_api_base="http://localhost:11434")
        handler = AIHandler(config)

        mock_choice = mock.MagicMock()
        mock_choice.message.content = "local response"
        mock_response = mock.MagicMock()
        mock_response.choices = [mock_choice]

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(return_value=mock_response)
            result = await handler.chat_completion("s", "u")
            call_kwargs = mock_litellm.acompletion.call_args
            assert call_kwargs.kwargs["api_base"] == "http://localhost:11434"
        assert result == "local response"

    @pytest.mark.asyncio
    async def test_api_base_not_passed_when_empty(self):
        config = _make_config()
        handler = AIHandler(config)

        mock_choice = mock.MagicMock()
        mock_choice.message.content = "ok"
        mock_response = mock.MagicMock()
        mock_response.choices = [mock_choice]

        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            mock_litellm.acompletion = mock.AsyncMock(return_value=mock_response)
            await handler.chat_completion("s", "u")
            call_kwargs = mock_litellm.acompletion.call_args
            assert "api_base" not in call_kwargs.kwargs

    def test_ssl_verify_disabled(self):
        config = _make_config(ssl_verify=False)
        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            AIHandler(config)
            assert mock_litellm.ssl_verify is False

    def test_ssl_verify_default(self):
        config = _make_config()
        with mock.patch("smart_reviewer.ai_handler.litellm") as mock_litellm:
            AIHandler(config)
            # ssl_verify should not be set to False
            assert mock_litellm.ssl_verify is not False
