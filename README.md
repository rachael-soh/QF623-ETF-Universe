# QF 623 Portfolio Management — Group Project
## ETF-Based Long/Short Strategy Research

**Singapore Management University · Master of Science in Quantitative Finance**
**Course: QF 623 Portfolio Management**

---

## Project Overview

This project researches and backtests **systematic long/short strategies** built on Exchange-Traded Funds (ETFs), focusing on two primary strategy universes:

| Strategy | Universe | Signal |
|----------|----------|--------|
| **Bond Duration Rotation** | US Nominal Treasury ETFs | Yield-curve slope, momentum |
| **Sector Equity Rotation** | GICS Sector ETFs (11 sectors) | Relative momentum, factor signals |
| **Equity Momentum L/S** | Russell 1000 proxies | 12-1 trailing return momentum |

All strategies are backtested from **January 2011 to present** using CRSP daily return data accessed via WRDS.

---

## Repository Structure

```
.
├── README.md                                  ← You are here
├── README.txt                                 ← Plain-text version of this file
├── requirements.txt                           ← Python dependencies
├── .gitignore
│
├── PM_GroupProject_Trial1_DataCleaning_7thJun26.ipynb   ← Main cleaning pipeline
├── momentum_long_short_vincent.py             ← Equity momentum L/S backtest
│
└── etf_long_short_project/
    ├── data/
    │   ├── README.md                          ← Data sources & replication guide
    │   ├── external/                          ← Universe definition files
    │   ├── raw/                               ← CRSP raw pulls (git-ignored)
    │   └── processed/                         ← Cleaned outputs (git-ignored)
    └── notebooks/
        └── 01_data_download.ipynb             ← WRDS data download script
```

---

## Pipeline

The project runs in two stages:

### Stage 1 — Data Cleaning (`PM_GroupProject_Trial1_DataCleaning_7thJun26.ipynb`)

```
ETF master universe (1,630 ETFs)
        │
        ▼
Quality guards (leveraged, ETN, survivorship-bias handling)
        │
        ▼
Permno resolution — 3-stage CUSIP → ticker cascade via WRDS
        │
        ▼
CRSP daily returns pull (2011–present, net of expense ratios)
        │
        ▼
Deduplication — benchmark-based (Stage A) + correlation-based (Stage B)
        │
        ▼
ETF type classification (Treasury / Corporate / Sector / Factor / etc.)
        │
        ▼
Output: clean universe metadata + wide return panels (dates × tickers)
```

### Stage 2 — Strategy Backtests *(in progress)*

- `momentum_long_short_vincent.py` — equity momentum long/short on Russell 1000

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd <repo-folder>
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or with conda:

```bash
conda create -n qf623 python=3.11
conda activate qf623
pip install -r requirements.txt
```

### 3. WRDS access (required)

Raw data is pulled from **WRDS (Wharton Research Data Services)** via the `wrds` Python package. You need an institutional WRDS account (available through SMU).

Set up your WRDS credentials:

```bash
python -c "import wrds; wrds.Connection().create_pgpass_file()"
```

This creates a `.pgpass` file so subsequent connections don't require a password prompt.

### 4. Run the cleaning pipeline

Open and run `PM_GroupProject_Trial1_DataCleaning_7thJun26.ipynb` top to bottom.

> **Note:** Two cells are marked **ONE-TIME WRDS PULL** — they download raw data and save it locally. Skip these on subsequent runs once the parquet files exist.

---

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| **CRSP** (via WRDS) | Daily returns, prices, volume (`crsp.dsf`) | WRDS account required |
| **CRSP** (via WRDS) | Security name history, permno, share codes (`crsp.dsenames`) | WRDS account required |
| **ETFG** | ETF master universe — metadata, expense ratios, AUM, benchmarks | Provided by course (not redistributed) |

Raw and processed data files are **not committed** to this repository (see `.gitignore`). See [`etf_long_short_project/data/README.md`](etf_long_short_project/data/README.md) for full replication instructions.

---

## Key Design Decisions

### Deduplication criterion: dollar volume over AUM

When multiple ETFs track the same benchmark (e.g. SPY / IVV / VOO all track the S&P 500), we keep the **most liquid** representative, defined by `recent_median_dollar_volume`. This is preferred over AUM because:
- AUM measures the stock of invested assets
- Dollar volume measures the daily flow — how much you can actually trade

SPY trades ~$33B/day vs IVV's ~$4B/day; SPY is the correct representative for execution purposes even though IVV has marginally higher AUM.

### Survivorship bias

Delisted ETFs are **not** filtered out from the backtest universe. An ETF coded `is_active == 0` was a valid investment during its listed life. Removing it would cause the backtest to only see ETFs that "survived", artificially inflating historical performance.

### Expense ratio adjustment

All returns are adjusted for the daily expense ratio drag:
```
ret_net = ret − (net_expenses / 252)
```
This ensures fair comparison across cheap (e.g. 0.03%) and expensive (e.g. 0.50%) ETFs.

---

## Group Members

| Name | Contribution |
|------|-------------|
| Sayandip Ghosh | Data pipeline, universe construction, cleaning framework |
| Vincent | Equity momentum long/short strategy (`momentum_long_short_vincent.py`) |
| *(add members)* | *(add contributions)* |

---

## Academic Use

This project is produced for academic purposes at SMU as part of QF 623 Portfolio Management. Data from WRDS/CRSP and ETFG is used under institutional licence and is not redistributed in this repository.
