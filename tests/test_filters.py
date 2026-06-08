import pytest
from src.filters import detect_leveraged, detect_inverse


# ── Leveraged detection ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "ProShares UltraPro QQQ",
        "Direxion Daily S&P 500 Bull 3X",
        "ProShares Ultra S&P500",
        "2X S&P 500 ETF",
        "Leveraged Gold ETF",
        "Daily 2X VIX Short-Term ETN",
    ],
)
def test_detect_leveraged_true(name):
    assert detect_leveraged(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "SPDR S&P 500 ETF Trust",
        "iShares Core US Aggregate Bond ETF",
        "Vanguard Total Stock Market ETF",
        "Invesco QQQ Trust",
    ],
)
def test_detect_leveraged_false(name):
    assert detect_leveraged(name) is False


# ── Inverse detection ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "ProShares Short S&P500",
        "ProShares UltraShort QQQ",
        "Direxion Daily S&P 500 Bear 3X",
        "Inverse Bond ETF",
    ],
)
def test_detect_inverse_true(name):
    assert detect_inverse(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "SPDR S&P 500 ETF Trust",
        "iShares Core US Aggregate Bond ETF",
        "Vanguard Total Stock Market ETF",
        "Invesco QQQ Trust",
    ],
)
def test_detect_inverse_false(name):
    assert detect_inverse(name) is False


# ── Category fallback ─────────────────────────────────────────────────────


def test_detect_leveraged_via_category():
    assert detect_leveraged("Some ETF", category="Leveraged Equity") is True


def test_detect_inverse_via_category():
    assert detect_inverse("Some ETF", category="Inverse Bond") is True
