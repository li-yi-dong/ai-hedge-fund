from pydantic import BaseModel

from src.utils.llm import call_llm


class _Reply(BaseModel):
    answer: str


class _StructuredModel:
    def with_structured_output(self, *args, **kwargs):
        return self

    def invoke(self, prompt):
        return None


def test_call_llm_uses_default_factory_when_structured_output_returns_none(monkeypatch):
    monkeypatch.setattr("src.utils.llm.get_model_info", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.utils.llm.get_model", lambda *args, **kwargs: _StructuredModel())

    result = call_llm(
        prompt="hello",
        pydantic_model=_Reply,
        max_retries=1,
        default_factory=lambda error: _Reply(answer=error),
    )

    assert result.answer == "Model returned no structured output"
