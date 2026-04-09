"""Tests for ReviewConfig."""

import os
from unittest import mock

import pytest

from smart_reviewer.config import ReviewConfig


class TestFromEnv:
    """Test ReviewConfig.from_env() factory method."""

    def test_minimal_valid_config(self):
        env = {"GITHUB_TOKEN": "ghp_test123"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = ReviewConfig.from_env()
        assert cfg.github_token == "ghp_test123"
        assert cfg.openai_api_key == ""
        assert cfg.model == "gpt-4o"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.2
        # booleans default to True when env var is absent
        assert cfg.auto_review is True
        assert cfg.auto_describe is True
        assert cfg.include_past_reviews is True

    def test_full_config(self):
        env = {
            "GITHUB_TOKEN": "ghp_abc",
            "OPENAI_API_KEY": "sk-key",
            "LLM_MODEL": "gpt-3.5-turbo",
            "MAX_TOKENS": "2048",
            "TEMPERATURE": "0.5",
            "AUTO_REVIEW": "true",
            "AUTO_DESCRIBE": "1",
            "AUTO_IMPROVE": "false",
            "EXTRA_INSTRUCTIONS": "Be nice",
            "NUM_MAX_FINDINGS": "5",
            "REQUIRE_SECURITY_REVIEW": "true",
            "REQUIRE_EFFORT_ESTIMATION": "false",
            "PUBLISH_OUTPUT": "1",
            "INCLUDE_PAST_REVIEWS": "false",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = ReviewConfig.from_env()
        assert cfg.openai_api_key == "sk-key"
        assert cfg.model == "gpt-3.5-turbo"
        assert cfg.max_tokens == 2048
        assert cfg.temperature == 0.5
        assert cfg.auto_review is True
        assert cfg.auto_describe is True
        assert cfg.auto_improve is False
        assert cfg.extra_instructions == "Be nice"
        assert cfg.num_max_findings == 5
        assert cfg.require_security_review is True
        assert cfg.require_effort_estimation is False
        assert cfg.publish_output is True
        assert cfg.include_past_reviews is False

    def test_missing_github_token_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_TOKEN"):
                ReviewConfig.from_env()

    def test_bool_variations(self):
        base = {"GITHUB_TOKEN": "tok"}
        for truthy in ("true", "True", "TRUE", "1"):
            env = {**base, "AUTO_REVIEW": truthy}
            with mock.patch.dict(os.environ, env, clear=True):
                cfg = ReviewConfig.from_env()
            assert cfg.auto_review is True, f"Expected True for {truthy!r}"

        for falsy in ("false", "0", "no", ""):
            env = {**base, "AUTO_REVIEW": falsy}
            with mock.patch.dict(os.environ, env, clear=True):
                cfg = ReviewConfig.from_env()
            assert cfg.auto_review is False, f"Expected False for {falsy!r}"
