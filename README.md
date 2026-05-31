# ETF Universe Construction Pipeline

Builds a **broad, clean master ETF universe** for QF623 Portfolio Management.
This is not the final strategy-specific portfolio — it is the pre-filtered universe
from which the strategy team can later select 20–40 ETFs.

---

## Purpose

The pipeline pulls US-listed ETFs from WRDS, removes clearly unusable ETFs
(leveraged, inverse, insufficient history, poor data quality, extreme illiquidity),
and produces a strategy-neutral master universe in CSV format.

---

## Installation

```bash
pip install -r requirements.txt
```

WRDS credentials are handled by the `wrds` Python package.
You will be prompted for your password on first run; the package caches it securely.

---

## Step 1 — Inspect Available WRDS Tables

Before running the full pipeline, check which libraries and tables you have access to:

```bash
python -m src.inspect_wrds
```

This writes `output/wrds_inventory.md` listing every accessible library and the tables
inside ETF/price-related libraries.

---

## Step 2 — Update the Config

Open `config/universe_config.yaml` and fill in the WRDS section based on what
`inspect_wrds` found:

```yaml
wrds:
  preferred_etf_library: etfg           # e.g. etfg (ETF Global) or crsp
  preferred_etf_master_table: etfg_...  # exact table name from wrds_inventory.md
  preferred_price_library: crsp
  preferred_price_table: dsf
```

If ETF Global (`etfg`) is available, use it for the master file because it has
dedicated leveraged/inverse flags. Otherwise use CRSP security master filtered to ETFs.

---

## Step 3 — Run the Pipeline

```bash
python -m src.build_universe --config config/universe_config.yaml
```

---

## Output Files

| File | Description |
|------|-------------|
| `data/raw/wrds_etf_master_raw.csv` | Unmodified master list from WRDS |
| `data/raw/wrds_etf_prices_raw.csv` | Unmodified daily prices from WRDS |
| `data/interim/candidate_etf_universe.csv` | After US/ETF/leveraged/inverse filters |
| `data/interim/etf_screening_metrics.csv` | Per-ETF computed metrics |
| `data/interim/excluded_etfs_with_reasons.csv` | All removed ETFs with reasons |
| `data/processed/clean_etf_master_universe.csv` | **Final clean master universe** |
| `output/universe_screening_report.md` | Human-readable screening summary |
| `output/wrds_inventory.md` | WRDS library/table inventory |

---

## Screening Rules Applied

1. US-listed ETFs only
2. Exclude leveraged ETFs (keyword detection + official flags if available)
3. Exclude inverse ETFs
4. Remove ETFs with fewer than 3 years of price history
5. Remove ETFs with > 5% missing trading days (after inception)
6. Remove ETFs below the 10th-percentile median dollar volume
7. Remove ETFs with stale pricing patterns (> 30% zero returns or > 10 consecutive zero-return days)

## Rules NOT Applied Here

The following filters are intentionally deferred to the strategy team:

- Momentum strength or mean-reversion behavior
- Past return preferences
- Volatility level preferences
- Correlation constraints
- Asset class / sector preferences
- Final portfolio size (20–40 ETFs)

---

## Running Tests

```bash
pytest tests/
```
