import os

import pytest
from anthropic import Anthropic
from dotenv import load_dotenv

from src.llm.models import ModelProvider, get_model


load_dotenv('.env')


def _require_live_anthropic_env() -> tuple[str, str]:
    if os.getenv('RUN_LIVE_API_TESTS') != '1':
        pytest.skip('Set RUN_LIVE_API_TESTS=1 to run live Anthropic endpoint tests')

    api_key = "sk-NuecjfYXYZcnP4xvknHnYMyxeGNddamdlsX9B4CB3I65CwkM"
    base_url = "https://key.simpleai.com.cn"

    if not api_key or not base_url:
        pytest.skip('ANTHROPIC_API_KEY and ANTHROPIC_API_URL/ANTHROPIC_BASE_URL are required')

    return api_key, base_url


def test_anthropic_endpoint_returns_non_empty_content_via_sdk():
    api_key, base_url = _require_live_anthropic_env()

    response = Anthropic(api_key=api_key, base_url=base_url).messages.create(
        model='claude-sonnet-4-6',
        max_tokens=32,
        messages=[{'role': 'user', 'content': 'Reply with OK only.'}],
    )
    print(response)

    assert response.content is not None, (
        f'Expected non-null content from {base_url}, got stop_reason={response.stop_reason!r} '
        f'and output_tokens={getattr(response.usage, "output_tokens", None)!r}'
    )
    assert len(response.content) > 0, f'Expected at least one content block from {base_url}'

    text_blocks = [
        block.text
        for block in response.content
        if getattr(block, 'type', None) == 'text' and getattr(block, 'text', None)
    ]
    assert text_blocks, f'Expected at least one text block from {base_url}'


def test_anthropic_endpoint_returns_non_empty_content_via_repo_model():
    _, base_url = _require_live_anthropic_env()

    response = get_model('claude-sonnet-4-6', ModelProvider.ANTHROPIC).invoke('Reply with OK only.')

    assert response.content is not None, f'Expected non-null LangChain content from {base_url}'
    if isinstance(response.content, str):
        assert response.content.strip(), f'Expected non-empty LangChain content from {base_url}'
    else:
        assert len(response.content) > 0, f'Expected at least one LangChain content block from {base_url}'
