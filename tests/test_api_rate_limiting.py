import os
import pytest
from unittest.mock import Mock, patch, call

from src.data.models import Price
from src.tools.api import _make_api_request, get_prices
from src.utils.api_key import (
    FINANCIAL_DATASETS_PROVIDER,
    TUSHARE_PRO_PROVIDER,
    get_financial_datasets_api_key,
    get_market_data_api_key,
    get_market_data_provider,
)


class TestRateLimiting:
    """Test suite for API rate limiting functionality."""

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_handles_single_rate_limit(self, mock_get, mock_sleep):
        """Test that API retries once after a 429 and succeeds."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429

        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.text = "Success"

        mock_get.side_effect = [mock_429_response, mock_200_response]

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"

        result = _make_api_request(url, headers)

        assert result.status_code == 200
        assert result.text == "Success"
        assert mock_get.call_count == 2
        mock_get.assert_has_calls([
            call(url, headers=headers),
            call(url, headers=headers),
        ])
        mock_sleep.assert_called_once_with(60)

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_handles_multiple_rate_limits(self, mock_get, mock_sleep):
        """Test that API retries multiple times after 429s."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429

        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.text = "Success"

        mock_get.side_effect = [
            mock_429_response,
            mock_429_response,
            mock_429_response,
            mock_200_response,
        ]

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"

        result = _make_api_request(url, headers)

        assert result.status_code == 200
        assert result.text == "Success"
        assert mock_get.call_count == 4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_has_calls([call(60), call(90), call(120)])

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.post')
    def test_handles_post_rate_limiting(self, mock_post, mock_sleep):
        """Test that POST requests handle rate limiting."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429

        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.text = "Success"

        mock_post.side_effect = [mock_429_response, mock_200_response]

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"
        json_data = {"test": "data"}

        result = _make_api_request(url, headers, method="POST", json_data=json_data)

        assert result.status_code == 200
        assert result.text == "Success"
        assert mock_post.call_count == 2
        mock_post.assert_has_calls([
            call(url, headers=headers, json=json_data),
            call(url, headers=headers, json=json_data),
        ])
        mock_sleep.assert_called_once_with(60)

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_ignores_other_errors(self, mock_get, mock_sleep):
        """Test that non-429 errors are returned without retrying."""
        mock_500_response = Mock()
        mock_500_response.status_code = 500
        mock_500_response.text = "Internal Server Error"

        mock_get.return_value = mock_500_response

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"

        result = _make_api_request(url, headers)

        assert result.status_code == 500
        assert result.text == "Internal Server Error"
        assert mock_get.call_count == 1
        mock_sleep.assert_not_called()

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_normal_success_requests(self, mock_get, mock_sleep):
        """Test that successful requests return immediately without retry."""
        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.text = "Success"

        mock_get.return_value = mock_200_response

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"

        result = _make_api_request(url, headers)

        assert result.status_code == 200
        assert result.text == "Success"
        assert mock_get.call_count == 1
        mock_sleep.assert_not_called()

    @patch('src.tools.api._cache')
    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_full_integration(self, mock_get, mock_sleep, mock_cache):
        """Test that get_prices function properly handles rate limiting."""
        mock_cache.get_prices.return_value = None

        mock_429_response = Mock()
        mock_429_response.status_code = 429

        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.json.return_value = {
            "ticker": "AAPL",
            "prices": [
                {
                    "time": "2024-01-01T00:00:00Z",
                    "open": 100.0,
                    "close": 101.0,
                    "high": 102.0,
                    "low": 99.0,
                    "volume": 1000,
                }
            ],
        }

        mock_get.side_effect = [mock_429_response, mock_200_response]

        with patch.dict(os.environ, {"FINANCIAL_DATASETS_API_KEY": "test-key"}):
            result = get_prices("AAPL", "2024-01-01", "2024-01-02")

        assert len(result) == 1
        assert result[0].open == 100.0
        assert result[0].close == 101.0
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(60)
        mock_cache.get_prices.assert_called_once()
        mock_cache.set_prices.assert_called_once()

    @patch('src.tools.api.time.sleep')
    @patch('src.tools.api.requests.get')
    def test_max_retries_exceeded(self, mock_get, mock_sleep):
        """Test that function stops retrying after max_retries and returns final 429."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.text = "Too Many Requests"

        mock_get.return_value = mock_429_response

        headers = {"X-API-KEY": "test-key"}
        url = "https://api.financialdatasets.ai/test"

        result = _make_api_request(url, headers, max_retries=2)

        assert result.status_code == 429
        assert result.text == "Too Many Requests"
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(60), call(90)])


class TestProviderRouting:
    @patch('src.tools.api._cache')
    @patch('src.tools.api._get_tushare_prices')
    def test_get_prices_uses_tushare_provider_and_provider_cache_key(self, mock_get_tushare_prices, mock_cache):
        mock_cache.get_prices.return_value = None
        mock_get_tushare_prices.return_value = [
            Price(
                open=100.0,
                close=101.0,
                high=102.0,
                low=99.0,
                volume=1000,
                time='2024-01-01T00:00:00Z',
            )
        ]

        result = get_prices(
            '000001.SZ',
            '2024-01-01',
            '2024-01-02',
            api_key='tushare-token',
            provider=TUSHARE_PRO_PROVIDER,
        )

        assert len(result) == 1
        assert result[0].close == 101.0
        mock_cache.get_prices.assert_called_once_with('TUSHARE_PRO:000001.SZ_2024-01-01_2024-01-02')
        mock_get_tushare_prices.assert_called_once_with(
            '000001.SZ',
            '2024-01-01',
            '2024-01-02',
            api_key='tushare-token',
        )
        mock_cache.set_prices.assert_called_once_with(
            'TUSHARE_PRO:000001.SZ_2024-01-01_2024-01-02',
            [
                {
                    'open': 100.0,
                    'close': 101.0,
                    'high': 102.0,
                    'low': 99.0,
                    'volume': 1000,
                    'time': '2024-01-01T00:00:00Z',
                }
            ],
        )

    @patch('src.tools.api._cache')
    @patch('src.tools.api.requests.get')
    def test_get_prices_uses_financial_datasets_provider_and_provider_cache_key(self, mock_get, mock_cache):
        mock_cache.get_prices.return_value = None

        mock_200_response = Mock()
        mock_200_response.status_code = 200
        mock_200_response.json.return_value = {
            'ticker': 'AAPL',
            'prices': [
                {
                    'time': '2024-01-01T00:00:00Z',
                    'open': 100.0,
                    'close': 101.0,
                    'high': 102.0,
                    'low': 99.0,
                    'volume': 1000,
                }
            ],
        }
        mock_get.return_value = mock_200_response

        with patch.dict(os.environ, {'FINANCIAL_DATASETS_API_KEY': 'fd-key'}, clear=False):
            result = get_prices(
                'AAPL',
                '2024-01-01',
                '2024-01-02',
                provider=FINANCIAL_DATASETS_PROVIDER,
            )

        assert len(result) == 1
        assert result[0].close == 101.0
        mock_cache.get_prices.assert_called_once_with('FINANCIAL_DATASETS:AAPL_2024-01-01_2024-01-02')
        mock_get.assert_called_once_with(
            'https://api.financialdatasets.ai/prices/?ticker=AAPL&interval=day&interval_multiplier=1&start_date=2024-01-01&end_date=2024-01-02',
            headers={'X-API-KEY': 'fd-key'},
        )
        mock_cache.set_prices.assert_called_once_with(
            'FINANCIAL_DATASETS:AAPL_2024-01-01_2024-01-02',
            [
                {
                    'open': 100.0,
                    'close': 101.0,
                    'high': 102.0,
                    'low': 99.0,
                    'volume': 1000,
                    'time': '2024-01-01T00:00:00Z',
                }
            ],
        )


class TestMarketDataProviderHelpers:
    def test_get_market_data_provider_prefers_request_value(self):
        request = {'market_data_provider': 'tushare'}

        with patch.dict(os.environ, {'MARKET_DATA_PROVIDER': 'FINANCIAL_DATASETS'}, clear=False):
            assert get_market_data_provider(request) == TUSHARE_PRO_PROVIDER

    def test_get_market_data_provider_falls_back_to_env(self):
        with patch.dict(os.environ, {'MARKET_DATA_PROVIDER': 'tushare-pro'}, clear=False):
            assert get_market_data_provider() == TUSHARE_PRO_PROVIDER

    def test_get_market_data_api_key_uses_provider_specific_request_key(self):
        request = {
            'market_data_provider': TUSHARE_PRO_PROVIDER,
            'api_keys': {
                'TUSHARE_PRO_API_KEY': 'tushare-request-key',
                'FINANCIAL_DATASETS_API_KEY': 'fd-request-key',
            },
        }

        assert get_market_data_api_key(request, provider=TUSHARE_PRO_PROVIDER) == 'tushare-request-key'
        assert get_financial_datasets_api_key(request) == 'fd-request-key'

    def test_get_market_data_api_key_falls_back_to_provider_specific_env_key(self):
        with patch.dict(
            os.environ,
            {
                'MARKET_DATA_PROVIDER': TUSHARE_PRO_PROVIDER,
                'TUSHARE_PRO_API_KEY': 'tushare-env-key',
                'FINANCIAL_DATASETS_API_KEY': 'fd-env-key',
            },
            clear=False,
        ):
            assert get_market_data_api_key(provider=TUSHARE_PRO_PROVIDER) == 'tushare-env-key'
            assert get_financial_datasets_api_key() == 'fd-env-key'


if __name__ == '__main__':
    pytest.main([__file__])
