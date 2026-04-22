import pytest
from pydantic import BaseModel

import src.llm.models as llm_models
from src.llm.models import ModelProvider, get_model


class _StructuredReply(BaseModel):
    answer: str


class TestAnthropicModelConfig:
    def test_get_model_uses_anthropic_api_url_and_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        monkeypatch.setenv("ANTHROPIC_API_URL", "https://anthropic-proxy.example")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        model = get_model("claude-sonnet-4-6", ModelProvider.ANTHROPIC)

        assert hasattr(model, "invoke")
        assert hasattr(model, "with_structured_output")

    def test_get_model_falls_back_to_anthropic_base_url_when_api_url_missing(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        monkeypatch.delenv("ANTHROPIC_API_URL", raising=False)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://anthropic-base.example")

        model = get_model("claude-sonnet-4-6", ModelProvider.ANTHROPIC)

        assert hasattr(model, "invoke")
        assert hasattr(model, "with_structured_output")

    def test_get_model_raises_when_anthropic_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        with pytest.raises(ValueError, match="Anthropic API key not found"):
            get_model("claude-sonnet-4-6", ModelProvider.ANTHROPIC)

    def test_anthropic_model_rejects_null_content_with_clear_error(self):
        model = llm_models.GuardedChatAnthropic(model="claude-sonnet-4-6", api_key="test-anthropic-key", base_url="https://anthropic-proxy.example")

        with pytest.raises(ValueError, match="Anthropic endpoint returned null content from https://anthropic-proxy.example"):
            model._format_output(type("Response", (), {"content": None})())

    def test_anthropic_model_still_supports_structured_output(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        monkeypatch.setenv("ANTHROPIC_API_URL", "https://anthropic-proxy.example")

        model = get_model("claude-sonnet-4-6", ModelProvider.ANTHROPIC)
        structured = model.with_structured_output(_StructuredReply)

        assert hasattr(structured, "invoke")
