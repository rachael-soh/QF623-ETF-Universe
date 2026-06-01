# ETF Universe Screening Report

**Date range:** 2015-01-01 – 2025-12-31

## Funnel Summary

| Step | Count |
|------|-------|
| Raw ETFs pulled from WRDS | 5,460 |
| After US-listed + ETF type filter | 5,460 |
| Removed: Not US-listed | 0 |
| Removed: Not ETF | 0 |
| Removed: Leveraged ETF | 0 |
| Removed: Inverse ETF | 0 |
| Removed: Insufficient price history | 1,858 |
| Removed: Too much missing data | 100 |
| Removed: Below liquidity cutoff | 1,421 |
| Removed: Stale pricing pattern | 10 |
| **Final clean master universe** | **1,630** |

## Screening Parameters

- Minimum history: 3 years
- Max missing data: 5.0%
- Liquidity cutoff (median dollar volume): 72,414
- Max zero-return ratio: 30%
- Max consecutive zero-return days: 10

## Top 20 ETFs by Median Dollar Volume

| ticker | fund_name | median_dollar_volume |
| --- | --- | --- |
| SPY | SPDR S&P 500 ETF Trust | 24980175425.255882 |
| QQQ | Invesco QQQ | 8497749601.57 |
| IWM | iShares Russell 2000 ETF | 4222406810.68682 |
| EEM | iShares MSCI Emerging Markets ETF | 1941549719.4699998 |
| HYG | iShares iBoxx $ High Yield Corporate Bond ETF | 1690692527.98 |
| OIH | VanEck Oil Services ETF | 1587330378.1999998 |
| TLT | iShares 20+ Year Treasury Bond ETF | 1514918855.029995 |
| XLF | Financial Select Sector SPDR Fund | 1396867249.673264 |
| EFA | iShares MSCI EAFE ETF | 1337401549.425 |
| IVV | iShares Core S&P 500 ETF | 1331492099.6598048 |
| XOP | SPDR S&P Oil & Gas Exploration & Production ETF | 1305924731.372325 |
| LQD | iShares iBoxx $ Investment Grade Corporate Bond ETF | 1256759554.44 |
| XLE | Energy Select Sector SPDR Fund | 1205812503.005 |
| GLD | SPDR Gold Shares | 1100022612.7649999 |
| DIA | SPDR Dow Jones Industrial Average ETF Trust | 998362279.495 |
| VOO | Vanguard S&P 500 ETF | 933127315.73189 |
| XLV | Health Care Select Sector SPDR Fund | 896166227.935 |
| FXI | iShares China Large-Cap ETF | 885515935.66 |
| GDX | VanEck Gold Miners ETF | 853045035.62 |
| XLK | Technology Select Sector SPDR Fund | 851622341.595005 |

## Asset Class Breakdown

| asset_class | count |
| --- | --- |
| Equity | 1203 |
| Fixed Income | 278 |
| Multi Asset | 68 |
| Commodities | 35 |
| Real Estate | 34 |
| Currency | 11 |

## Product Structure Breakdown

| product_structure | count |
| --- | --- |
| ETF | 1587 |
| Actively Managed ETF | 18 |
| Currency Trust | 14 |
| Futures-Based ETF | 7 |
| Commodity Trust | 4 |

## Category Breakdown

| category | count |
| --- | --- |
| Size and Style | 402 |
| Strategy | 300 |
| Broad Equity | 283 |
| Sector | 257 |
| Corporate | 100 |
| Broad Debt | 68 |
| Asset Allocation | 56 |
| U.S. Government | 49 |
| Municipals | 42 |
| Precious Metals | 14 |
| Sovereign | 12 |
| Absolute Returns | 12 |
| Broad Commodities | 11 |
| Energy | 5 |
| Broad Market | 4 |
| Alternative Currency | 3 |
| Basket | 2 |
| Agriculture | 1 |
| Industrial Metals | 1 |
| Australian Dollar | 1 |
| Pound Sterling | 1 |
| Canadian Dollar | 1 |
| Euro | 1 |
| Swiss Franc | 1 |
| Japanese Yen | 1 |
| Spreads | 1 |

## Important Note

> This is a **broad clean master universe**, not the final strategy-specific ETF list.
> The strategy team should apply additional filters (momentum, mean-reversion, asset class
> preference, correlation, target universe size) on top of this output.
> Do **not** treat this list as the final 20–40 ETF portfolio.
