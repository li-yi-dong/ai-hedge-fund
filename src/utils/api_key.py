import os
from typing import Any

DEFAULT_MARKET_DATA_PROVIDER = "FINANCIAL_DATASETS"
FINANCIAL_DATASETS_PROVIDER = "FINANCIAL_DATASETS"
TUSHARE_PRO_PROVIDER = "TUSHARE_PRO"
FINANCIAL_DATASETS_API_KEY_NAME = "FINANCIAL_DATASETS_API_KEY"
TUSHARE_PRO_API_KEY_NAME = "TUSHARE_PRO_API_KEY"
MARKET_DATA_PROVIDER_ENV_NAME = "MARKET_DATA_PROVIDER"


PROVIDER_ALIASES = {
    "FINANCIALDATASETS": FINANCIAL_DATASETS_PROVIDER,
    "FINANCIAL_DATASETS": FINANCIAL_DATASETS_PROVIDER,
    "FINANCIAL-DATASETS": FINANCIAL_DATASETS_PROVIDER,
    "TUSHARE": TUSHARE_PRO_PROVIDER,
    "TUSHAREPRO": TUSHARE_PRO_PROVIDER,
    "TUSHARE_PRO": TUSHARE_PRO_PROVIDER,
    "TUSHARE-PRO": TUSHARE_PRO_PROVIDER,
}


def normalize_market_data_provider(provider: str | None) -> str:
    if not provider:
        return DEFAULT_MARKET_DATA_PROVIDER

    normalized = provider.strip().upper().replace(" ", "_")
    return PROVIDER_ALIASES.get(normalized, DEFAULT_MARKET_DATA_PROVIDER)


def _normalize_market_data_provider(provider: str | None) -> str:
    return normalize_market_data_provider(provider)


def _get_value(container: Any, key: str, default: Any = None) -> Any:
    if container is None:
        return default

    if isinstance(container, dict):
        return container.get(key, default)

    return getattr(container, key, default)


def _get_request(source: Any) -> Any:
    if source is None:
        return None

    metadata = _get_value(source, "metadata")
    request = _get_value(metadata, "request")
    if request is not None:
        return request

    return source


def get_api_key(source: Any, api_key_name: str) -> str | None:
    request = _get_request(source)
    api_keys = _get_value(request, "api_keys")
    if api_keys:
        api_key = api_keys.get(api_key_name)
        if api_key:
            return api_key

    return os.getenv(api_key_name)


def get_api_key_from_state(state: dict, api_key_name: str) -> str | None:
    """Get an API key from the state object or environment."""
    return get_api_key(state, api_key_name)


def get_market_data_provider(source: Any = None) -> str:
    request = _get_request(source)
    provider = _get_value(request, "market_data_provider") or os.getenv(MARKET_DATA_PROVIDER_ENV_NAME)
    return _normalize_market_data_provider(provider)


def get_market_data_provider_from_state(state: dict) -> str:
    return get_market_data_provider(state)


def get_market_data_api_key_name(provider: str | None = None) -> str:
    resolved_provider = _normalize_market_data_provider(provider or os.getenv(MARKET_DATA_PROVIDER_ENV_NAME))
    if resolved_provider == TUSHARE_PRO_PROVIDER:
        return TUSHARE_PRO_API_KEY_NAME
    return FINANCIAL_DATASETS_API_KEY_NAME


def get_market_data_api_key(source: Any = None, provider: str | None = None) -> str | None:
    resolved_provider = _normalize_market_data_provider(provider or get_market_data_provider(source))
    return get_api_key(source, get_market_data_api_key_name(resolved_provider))


def get_financial_datasets_api_key(source: Any = None) -> str | None:
    return get_market_data_api_key(source, provider=FINANCIAL_DATASETS_PROVIDER)


def get_market_data_api_key_from_state(state: dict, provider: str | None = None) -> str | None:
    return get_market_data_api_key(state, provider=provider)


def get_financial_datasets_api_key_from_state(state: dict) -> str | None:
    return get_financial_datasets_api_key(state)
