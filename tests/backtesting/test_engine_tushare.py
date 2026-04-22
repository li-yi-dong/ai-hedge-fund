from src.backtesting.engine import BacktestEngine
from tests.backtesting.integration.mocks import MockConfigurableAgent


def test_backtest_engine_skips_financial_datasets_prefetches_for_tushare(monkeypatch):
    engine = BacktestEngine(
        agent=MockConfigurableAgent([{}], ["000001.SZ"]),
        tickers=["000001.SZ"],
        start_date="2024-01-02",
        end_date="2024-01-05",
        initial_capital=100000.0,
        model_name="test-model",
        model_provider="Anthropic",
        selected_analysts=["technical_analyst"],
        initial_margin_requirement=0.0,
        market_data_provider="TUSHARE_PRO",
        market_data_api_key="test-token",
    )

    price_calls = []

    monkeypatch.setattr("src.backtesting.engine.get_prices", lambda *args, **kwargs: price_calls.append((args, kwargs)))
    monkeypatch.setattr("src.backtesting.engine.get_financial_metrics", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not fetch financial metrics for Tushare")))
    monkeypatch.setattr("src.backtesting.engine.get_insider_trades", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not fetch insider trades for Tushare")))
    monkeypatch.setattr("src.backtesting.engine.get_company_news", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not fetch company news for Tushare")))

    engine._prefetch_data()

    assert len(price_calls) == 1
    assert price_calls[0][0][0] == "000001.SZ"



def test_backtest_engine_raises_when_all_days_use_portfolio_manager_fallback(monkeypatch):
    tickers = ["000001.SZ"]
    engine = BacktestEngine(
        agent=MockConfigurableAgent([{}], tickers),
        tickers=tickers,
        start_date="2024-01-02",
        end_date="2024-01-05",
        initial_capital=100000.0,
        model_name="test-model",
        model_provider="Anthropic",
        selected_analysts=["technical_analyst"],
        initial_margin_requirement=0.0,
        market_data_provider="TUSHARE_PRO",
        market_data_api_key="test-token",
    )

    monkeypatch.setattr("src.backtesting.engine.get_prices", lambda *a, **k: None)

    class _FakePriceData:
        empty = False

        def __init__(self, close: float):
            self._close = close
            self.iloc = self

        def __getitem__(self, index):
            return {"close": self._close}

    monkeypatch.setattr(
        "src.backtesting.engine.get_price_data",
        lambda *a, **k: _FakePriceData(9.21),
    )

    def _fake_run_agent(*args, **kwargs):
        return {
            "decisions": {
                "000001.SZ": {
                    "action": "hold",
                    "quantity": 0,
                    "confidence": 0,
                    "reasoning": "LLM error: object of type 'NoneType' has no len()",
                }
            },
            "analyst_signals": {},
        }

    monkeypatch.setattr(engine._agent_controller, "run_agent", _fake_run_agent)
    monkeypatch.setattr(engine._results, "build_day_rows", lambda **kwargs: [])
    monkeypatch.setattr(engine._results, "print_rows", lambda rows: None)
    monkeypatch.setattr(engine._benchmark, "get_return_pct", lambda *a, **k: None)

    try:
        engine.run_backtest()
        assert False, "Expected RuntimeError for all-fallback portfolio manager output"
    except RuntimeError as exc:
        assert "object of type 'NoneType' has no len()" in str(exc)



def test_backtest_engine_preserves_decision_reasoning_in_controller(portfolio):
    def agent(**kwargs):
        return {
            "decisions": {
                "000001.SZ": {
                    "action": "hold",
                    "quantity": "0",
                    "confidence": 12,
                    "reasoning": "LLM error: object of type 'NoneType' has no len()",
                }
            },
            "analyst_signals": {},
        }

    engine = BacktestEngine(
        agent=agent,
        tickers=["000001.SZ"],
        start_date="2024-01-02",
        end_date="2024-01-05",
        initial_capital=100000.0,
        model_name="test-model",
        model_provider="Anthropic",
        selected_analysts=["technical_analyst"],
        initial_margin_requirement=0.0,
        market_data_provider="TUSHARE_PRO",
        market_data_api_key="test-token",
    )

    output = engine._agent_controller.run_agent(
        engine._agent,
        tickers=["000001.SZ"],
        start_date="2024-01-02",
        end_date="2024-01-03",
        portfolio=portfolio,
        model_name="test-model",
        model_provider="Anthropic",
        selected_analysts=["technical_analyst"],
    )

    assert output["decisions"]["000001.SZ"]["reasoning"] == "LLM error: object of type 'NoneType' has no len()"
    assert output["decisions"]["000001.SZ"]["confidence"] == 12.0
