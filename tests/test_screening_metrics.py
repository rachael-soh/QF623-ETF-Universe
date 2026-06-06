import numpy as np
import pandas as pd
import pytest

from src.screening_metrics import calculate_screening_metrics, _max_consecutive_true


CONFIG = {
    "start_date": "2020-01-01",
    "end_date": "2020-12-31",
    "stale_price": {
        "max_zero_return_ratio": 0.30,
        "max_consecutive_zero_return_days": 10,
    },
}


def _make_prices(ticker, dates, returns, dollar_volumes=None):
    n = len(dates)
    dv = dollar_volumes if dollar_volumes is not None else [1_000_000] * n
    return pd.DataFrame(
        {
            "ticker": ticker,
            "date": pd.to_datetime(dates),
            "return": returns,
            "dollar_volume": dv,
        }
    )


# ── Annualised volatility ──────────────────────────────────────────────────


def test_annualized_volatility():
    dates = pd.bdate_range("2020-01-02", periods=252)
    daily_std = 0.01
    returns = [daily_std] * 252
    df = _make_prices("SPY", dates, returns)
    metrics = calculate_screening_metrics(df, CONFIG)
    expected = daily_std * np.sqrt(252)
    # daily_std * sqrt(252) but std([c]*n) == 0 for constant series — use alternating
    dates2 = pd.bdate_range("2020-01-02", periods=252)
    returns2 = [0.01, -0.01] * 126
    df2 = _make_prices("SPY2", dates2, returns2)
    metrics2 = calculate_screening_metrics(df2, CONFIG)
    ann_vol = metrics2.loc[metrics2["ticker"] == "SPY2", "annualized_volatility"].iloc[
        0
    ]
    assert ann_vol == pytest.approx(pd.Series(returns2).std() * np.sqrt(252), rel=1e-4)


# ── Missing data percentage ────────────────────────────────────────────────


def test_missing_data_pct_full_history():
    dates = pd.bdate_range("2020-01-02", "2020-12-31")
    returns = [0.001] * len(dates)
    df = _make_prices("FULL", dates, returns)
    metrics = calculate_screening_metrics(df, CONFIG)
    row = metrics[metrics["ticker"] == "FULL"].iloc[0]
    assert row["missing_data_pct"] == pytest.approx(0.0, abs=0.01)


def test_missing_data_pct_partial_history():
    # Only provide half the trading days
    all_dates = pd.bdate_range("2020-01-02", "2020-12-31")
    half_dates = all_dates[::2]  # every other day
    returns = [0.001] * len(half_dates)
    df = _make_prices("HALF", half_dates, returns)
    metrics = calculate_screening_metrics(df, CONFIG)
    row = metrics[metrics["ticker"] == "HALF"].iloc[0]
    assert row["missing_data_pct"] > 0.40  # roughly 50% missing


# ── Zero-return ratio ──────────────────────────────────────────────────────


def test_zero_return_ratio():
    dates = pd.bdate_range("2020-01-02", periods=100)
    returns = [0.0] * 40 + [0.01] * 60
    df = _make_prices("ZERO", dates, returns)
    metrics = calculate_screening_metrics(df, CONFIG)
    row = metrics[metrics["ticker"] == "ZERO"].iloc[0]
    assert row["zero_return_ratio"] == pytest.approx(0.40, rel=1e-3)


# ── Max consecutive zero-return days ─────────────────────────────────────


def test_max_consecutive_zero_return_days():
    mask = pd.Series([False, True, True, True, False, True, False])
    assert _max_consecutive_true(mask) == 3


def test_max_consecutive_all_false():
    mask = pd.Series([False] * 10)
    assert _max_consecutive_true(mask) == 0


def test_max_consecutive_all_true():
    mask = pd.Series([True] * 7)
    assert _max_consecutive_true(mask) == 7


def test_stale_price_flag_triggered():
    dates = pd.bdate_range("2020-01-02", periods=100)
    returns = [0.0] * 35 + [0.01] * 65  # 35% zeros > threshold of 30%
    df = _make_prices("STALE", dates, returns)
    metrics = calculate_screening_metrics(df, CONFIG)
    row = metrics[metrics["ticker"] == "STALE"].iloc[0]
    assert row["stale_price_flag"] is True
