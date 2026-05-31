Build a Python pipeline for QF623 ETF universe construction.

Project context:
We need a reproducible ETF universe construction pipeline for a portfolio management project. The project requires ETF universe construction, exclusion of leveraged/inverse ETFs, Python implementation, and later portfolio construction/performance attribution. At this stage, DO NOT select the final strategy-specific 20–40 ETFs. Instead, build a broad clean master universe of “workable” US-listed ETFs by filtering out bad/unusable ETFs only.

End goal:
Produce a clean master ETF universe CSV that can later be filtered by the strategy team.

Final main output:
data/processed/clean_etf_master_universe.csv

Secondary outputs:
data/raw/wrds_etf_master_raw.csv
data/raw/wrds_etf_prices_raw.csv
data/interim/etf_screening_metrics.csv
data/interim/excluded_etfs_with_reasons.csv
output/universe_screening_report.md

Important principle:
Do not hardcode a final list of ETFs. The universe must be generated programmatically using screening criteria.

Core screening rules:
1. US-listed ETFs only.
2. Exclude leveraged ETFs.
3. Exclude inverse ETFs.
4. Remove ETFs with insufficient price history.
5. Remove ETFs with too much missing price data.
6. Remove extremely illiquid ETFs.
7. Remove ETFs with obvious stale pricing / bad return series.
8. Keep all ETFs that are broadly usable, even if they may not fit the final strategy.

Do NOT filter yet based on:
- Momentum strength
- Mean-reversion behavior
- Past return
- High/low volatility preference
- Correlation
- Specific asset class preference
- Final portfolio size

Use WRDS as the preferred data source.
However, do not assume exact WRDS table names. First implement code that checks available WRDS libraries/tables. If ETF Global data is available, use it for the ETF master file. If not, use available WRDS security master sources and/or CRSP daily security data. The implementation should be configurable so we can update table names after checking WRDS access.

Recommended project structure:

project/
│
├── config/
│   └── universe_config.yaml
│
├── data/
│   ├── raw/
│   │   ├── wrds_etf_master_raw.csv
│   │   └── wrds_etf_prices_raw.csv
│   │
│   ├── interim/
│   │   ├── candidate_etf_universe.csv
│   │   ├── etf_screening_metrics.csv
│   │   └── excluded_etfs_with_reasons.csv
│   │
│   └── processed/
│       └── clean_etf_master_universe.csv
│
├── output/
│   └── universe_screening_report.md
│
├── src/
│   ├── __init__.py
│   ├── wrds_connection.py
│   ├── inspect_wrds.py
│   ├── load_etf_master.py
│   ├── load_etf_prices.py
│   ├── screening_metrics.py
│   ├── filters.py
│   ├── build_universe.py
│   └── report.py
│
├── tests/
│   ├── test_filters.py
│   └── test_screening_metrics.py
│
├── requirements.txt
└── README.md

Use these dependencies:
pandas
numpy
pyyaml
wrds
python-dotenv
pytest

Create a config file:

config/universe_config.yaml

Suggested contents:

start_date: "2015-01-01"
end_date: "2025-12-31"

country: "US"
security_type: "ETF"

exclude_leveraged: true
exclude_inverse: true

min_history_years: 3
max_missing_data_pct: 0.05

liquidity:
  method: "median_dollar_volume"
  min_median_dollar_volume: null
  percentile_cutoff: 0.10

stale_price:
  max_zero_return_ratio: 0.30
  max_consecutive_zero_return_days: 10

wrds:
  preferred_etf_library: null
  preferred_etf_master_table: null
  preferred_price_library: null
  preferred_price_table: null

output:
  save_raw: true
  save_interim: true
  save_processed: true

Implementation details:

1. wrds_connection.py

Create a helper function:

get_wrds_connection()

Requirements:
- Connect using wrds.Connection()
- Do not hardcode username/password.
- Allow normal WRDS credential flow.
- Return the connection object.

2. inspect_wrds.py

Purpose:
Help us discover available WRDS data.

Functions:
- list_available_libraries(db)
- list_tables_for_library(db, library_name)
- save_wrds_inventory(db, output_path)

This script should print and save:
- Available libraries
- Tables in likely ETF-related libraries
- Tables in likely CRSP-related libraries

The goal is to avoid assuming exact WRDS table names before checking access.

CLI command:
python -m src.inspect_wrds

Output:
output/wrds_inventory.md

3. load_etf_master.py

Purpose:
Load the broad ETF master list.

Function:
load_etf_master(db, config) -> pd.DataFrame

Expected columns after cleaning:
ticker
fund_name
exchange
country
security_type
asset_class
category
inception_date
cusip
permno
raw_source

Notes:
- Use WRDS source if configured.
- If exact WRDS table names are not configured, raise a clear error explaining that the user must run inspect_wrds.py first and update the config.
- Save raw output to data/raw/wrds_etf_master_raw.csv.
- Standardize column names to lowercase snake_case.
- Strip whitespace from tickers and fund names.
- Drop rows with missing tickers.

4. load_etf_prices.py

Purpose:
Load daily price and volume data for candidate ETFs.

Function:
load_etf_prices(db, tickers, config) -> pd.DataFrame

Expected columns:
date
ticker
price
adjusted_price
return
volume
dollar_volume

Rules:
- Use adjusted price if available.
- If WRDS price data already has returns, keep them.
- If return is missing, compute pct_change by ticker using adjusted_price.
- dollar_volume = abs(adjusted_price) * volume
- Save raw output to data/raw/wrds_etf_prices_raw.csv.
- Ensure date is datetime.
- Sort by ticker and date.
- Remove duplicate ticker-date rows, keeping the latest valid observation.

5. filters.py

Purpose:
Centralize all filtering logic.

Create these functions:

detect_leveraged(fund_name, category=None) -> bool
detect_inverse(fund_name, category=None) -> bool
is_us_listed(row) -> bool
is_etf(row) -> bool
apply_master_filters(master_df, config) -> pd.DataFrame

Leveraged keyword fallback:
[
    "2X",
    "3X",
    "ULTRA",
    "ULTRAPRO",
    "LEVERAGED",
    "DAILY 2X",
    "DAILY 3X",
    "BULL 2X",
    "BULL 3X"
]

Inverse keyword fallback:
[
    "INVERSE",
    "SHORT",
    "ULTRASHORT",
    "BEAR",
    "BEAR 1X",
    "BEAR 2X",
    "BEAR 3X"
]

Important:
- Use official WRDS leveraged/inverse flags if available.
- If no official flags exist, use keyword detection as fallback.
- Store both:
  leveraged_flag
  inverse_flag
- Also store:
  leverage_inverse_detection_method
  e.g. "official_flag", "keyword_fallback", or "manual_unknown"

6. screening_metrics.py

Purpose:
Calculate ETF-level metrics from price data.

Function:
calculate_screening_metrics(price_df, config) -> pd.DataFrame

Output columns:
ticker
first_price_date
last_price_date
days_since_last_price          (added in Stage 1 additional filters)
history_years
num_observations
expected_observations
missing_data_pct
median_dollar_volume
average_dollar_volume
recent_median_dollar_volume    (added in Stage 1 additional filters)
recent_average_dollar_volume   (added in Stage 1 additional filters)
annualized_volatility
zero_return_ratio
max_consecutive_zero_return_days
stale_price_flag
zero_volume_ratio              (added in Stage 1 additional filters)
extreme_return_count           (added in Stage 1 additional filters)
extreme_return_ratio           (added in Stage 1 additional filters)
extreme_return_flag            (added in Stage 1 additional filters)

Metric definitions:

history_years:
(last_price_date - first_price_date).days / 365.25

missing_data_pct:
Compare available trading days for each ETF against a common date index.
Use the ETF’s active window only: from max(first_price_date, start_date) to
min(last_price_date, end_date). Do not punish ETFs for dates before inception
or after their last trade (delisted ETFs are not penalised for post-delisting gaps).

annualized_volatility:
daily return standard deviation * sqrt(252)

zero_return_ratio:
percentage of valid daily returns equal to zero

max_consecutive_zero_return_days:
maximum number of consecutive zero-return days for each ETF

stale_price_flag:
true if:
zero_return_ratio > config threshold
OR
max_consecutive_zero_return_days > config threshold

7. filters.py continued

Create function:

apply_quality_filters(universe_df, metrics_df, config) -> pd.DataFrame

This should merge master ETF info with screening metrics and create:

keep_flag
remove_reason

Filtering logic:
- If not US-listed: remove_reason += "Not US-listed"
- If not ETF: remove_reason += "Not ETF"
- If leveraged_flag: remove_reason += "Leveraged ETF"
- If inverse_flag: remove_reason += "Inverse ETF"
- If history_years is NaN (no price data): remove_reason += "No price data found"
  (short-circuit — skip all metric-based checks for this ETF)
- If days_since_last_price > max_days_since_last_price: remove_reason += "Inactive (...)"
- If history_years < min_history_years: remove_reason += "Insufficient price history"
- If missing_data_pct > max_missing_data_pct: remove_reason += "Too much missing data"
- If stale_price_flag: remove_reason += "Stale pricing pattern"
- If zero_volume_ratio > max_zero_volume_ratio: remove_reason += "Excessive zero-volume days"
- If recent_median_dollar_volume < liquidity_cutoff: remove_reason += "Below liquidity cutoff"
- If extreme_return_ratio > max_extreme_ratio (only when max_extreme_ratio is set):
    remove_reason += "Excessive extreme returns (data error suspected)"

Liquidity rule:
If config liquidity min_median_dollar_volume is null:
- Compute the 10th percentile of recent_median_dollar_volume across otherwise
  valid ETFs (passing all non-liquidity filters).
- Use that as a data-driven cutoff.
- Remove ETFs below that cutoff.
If config has explicit min_median_dollar_volume:
- Use that threshold.

Add:
liquidity_cutoff_used

Important:
Do not remove ETFs just because they are volatile, low-return, highly correlated, or outside a specific strategy type.

8. build_universe.py

Purpose:
Main pipeline script.

CLI command:
python -m src.build_universe --config config/universe_config.yaml

Pipeline steps:
1. Load config.
2. Connect to WRDS.
3. Load ETF master list.
4. Apply basic master filters:
   - US-listed
   - ETF only
   - no leveraged
   - no inverse
5. Save candidate ETF universe to:
   data/interim/candidate_etf_universe.csv
6. Load daily prices and volume for candidate ETFs.
7. Calculate screening metrics.
8. Apply data-quality/liquidity/stale-price filters.
9. Save kept ETFs to:
   data/processed/clean_etf_master_universe.csv
10. Save excluded ETFs to:
   data/interim/excluded_etfs_with_reasons.csv
11. Generate report:
   output/universe_screening_report.md

9. report.py

Create function:
generate_universe_report(final_df, excluded_df, config, output_path)

Report should include:
- Start date and end date
- Number of raw ETFs pulled
- Number remaining after US-listed ETF filter
- Number removed because leveraged
- Number removed because inverse
- Number removed due to insufficient history
- Number removed due to missing data
- Number removed due to liquidity
- Number removed due to stale pricing
- Final number of ETFs in clean master universe
- Liquidity cutoff used
- Missing data threshold
- History threshold
- Top 20 ETFs by median dollar volume
- Asset class/category breakdown if available
- Reminder that this is a clean master universe, not the final strategy-specific universe

10. README.md

Explain:
- Purpose of universe construction
- How to install dependencies
- How to connect to WRDS
- How to inspect WRDS tables
- How to update config with table names
- How to run the pipeline
- What files are produced
- What each output means
- Why we do not target 20–40 ETFs yet

README should include commands:

pip install -r requirements.txt

python -m src.inspect_wrds

python -m src.build_universe --config config/universe_config.yaml

11. Tests

Create basic pytest tests.

test_filters.py:
- Check leveraged keyword detection catches “UltraPro”, “2X”, “3X”, “Leveraged”
- Check inverse keyword detection catches “Inverse”, “Short”, “UltraShort”, “Bear”
- Check normal ETF names are not incorrectly flagged

test_screening_metrics.py:
- Test annualized volatility calculation
- Test missing data percentage calculation
- Test zero-return ratio
- Test max consecutive zero-return days

12. Acceptance criteria

The implementation is complete when:

- Running python -m src.inspect_wrds creates output/wrds_inventory.md.
- Running python -m src.build_universe --config config/universe_config.yaml creates:
  - data/raw/wrds_etf_master_raw.csv
  - data/raw/wrds_etf_prices_raw.csv
  - data/interim/candidate_etf_universe.csv
  - data/interim/etf_screening_metrics.csv
  - data/interim/excluded_etfs_with_reasons.csv
  - data/processed/clean_etf_master_universe.csv
  - output/universe_screening_report.md
- The final clean master universe includes only ETFs with keep_flag = True.
- The excluded ETF file clearly explains why each ETF was removed.
- Leveraged and inverse ETFs are excluded.
- The pipeline does not manually hardcode the final ETF universe.
- The final universe is broad and strategy-neutral.
- The code is modular enough that the strategy team can later create a strategy-specific universe.

14. Additional Stage 1 filters (implemented after initial pipeline)

These filters extend apply_quality_filters in filters.py and
calculate_screening_metrics in screening_metrics.py.
New config keys were added to config/universe_config.yaml.
load_etf_master.py was extended to derive product_structure.
load_etf_prices.py was extended to resolve duplicate ticker→permno mappings.

14a. Active ETF filter

Config key: active_etf.max_days_since_last_price (default: 365)

New metric: days_since_last_price = (end_date - last_price_date).days

Removal rule:
If days_since_last_price > max_days_since_last_price:
  remove_reason += "Inactive (last price Xd before end_date)"

Purpose: removes ETFs that have been delisted or halted well before the end
of the analysis window, ensuring the universe only contains tradeable ETFs.

14b. Identifier quality filter

No config key. Driven by presence/absence of price data.

Two layers:
1. Duplicate ticker→permno resolution in load_etf_prices.py:
   - When a ticker maps to multiple permnos (ticker reuse across time),
     keep the permno with the most recent nameendt (NULL = still active first).
   - This prevents historic stock data contaminating ETF price series
     (e.g. FB ticker used by Facebook before it was reused by a ProShares ETF).
2. Missing price data in filters.py:
   - ETFs that remain unresolved after deduplication get:
     remove_reason += "No price data found"
   - These ETFs short-circuit all metric-based filter checks.

The CRSP dsenames query is also restricted to shrcd = 73 (ETF share code)
to prevent non-ETF permnos from being matched on ticker alone.

14c. Recent liquidity filter

Config key: liquidity.recent_lookback_days (default: 365)

New metrics:
  recent_median_dollar_volume  — median daily dollar volume over the last
                                  recent_lookback_days calendar days
  recent_average_dollar_volume — mean over the same window

Change to liquidity cutoff logic:
- The 10th-percentile cutoff is now computed from recent_median_dollar_volume
  (not full-sample median_dollar_volume).
- If recent data is unavailable for a ticker, falls back to full-sample median.

Purpose: prevents ETFs that were liquid in the past but have dried up recently
from passing the liquidity screen.

14d. Zero-volume filter

Config key: zero_volume.max_zero_volume_ratio (default: 0.10)

New metric: zero_volume_ratio = fraction of trading days with zero or missing volume

Removal rule:
If zero_volume_ratio > max_zero_volume_ratio:
  remove_reason += "Excessive zero-volume days"

Purpose: catches ETFs with chronic liquidity gaps that the dollar-volume
median may not fully capture.

14e. Extreme return flag

Config keys:
  extreme_return.single_day_threshold (default: 0.50)
  extreme_return.max_extreme_ratio    (default: null = flag only, no auto-remove)

New metrics:
  extreme_return_count — number of days where |return| > single_day_threshold
  extreme_return_ratio — extreme_return_count / total valid return observations
  extreme_return_flag  — True if extreme_return_count > 0

Removal rule:
If max_extreme_ratio is set (not null):
  If extreme_return_ratio > max_extreme_ratio:
    remove_reason += "Excessive extreme returns (data error suspected)"
If max_extreme_ratio is null:
  Flag only. ETF remains in universe. extreme_return_flag is recorded in
  clean_etf_master_universe.csv for the strategy team to review.

Purpose: surface ETFs with suspicious return spikes that may indicate data
errors, corporate actions, or illiquid pricing artifacts. Auto-removal is
intentionally conservative — the strategy team decides final treatment.

14f. Product structure flag

No config key. Derived from ETF Global is_etn flag and fund name keywords.
Recorded in product_structure column. Does not drive automatic removal.

Values:
  ETF                  — standard exchange-traded fund
  ETN                  — exchange-traded note (debt instrument, no asset backing)
  Commodity Trust      — physical commodity trust (e.g. gold, silver)
  Currency Trust       — currency-backed trust
  Futures-Based ETF    — ETF primarily holding futures contracts
  Actively Managed ETF — non-index-tracking ETF

Rationale:
The strategy team may later wish to exclude or separate ETNs, commodity trusts,
or futures-based products. Recording the structure now avoids re-running
the pipeline later.

Product structure breakdown is included in universe_screening_report.md.

Updated config/universe_config.yaml sections:

active_etf:
  max_days_since_last_price: 365

liquidity:
  method: "median_dollar_volume"
  min_median_dollar_volume: null
  percentile_cutoff: 0.10
  recent_lookback_days: 365

zero_volume:
  max_zero_volume_ratio: 0.10

extreme_return:
  single_day_threshold: 0.50
  max_extreme_ratio: null

Updated screening_metrics.py output columns (additions to original list):
  days_since_last_price
  recent_median_dollar_volume
  recent_average_dollar_volume
  zero_volume_ratio
  extreme_return_count
  extreme_return_ratio
  extreme_return_flag

Updated filters.py apply_quality_filters additional remove_reason values:
  "Inactive (last price Xd before end_date)"
  "No price data found"
  "Excessive zero-volume days"
  "Below liquidity cutoff"  (now based on recent window)
  "Excessive extreme returns (data error suspected)"  (only if max_extreme_ratio set)

Updated load_etf_master.py additions:
  product_structure column (see 14f above)

Updated load_etf_prices.py additions:
  Duplicate ticker→permno resolution (see 14b above)
  shrcd = 73 filter on dsenames query

13. Important design choices

- Prefer clear, readable Python over over-engineered code.
- Use Pandas for data manipulation.
- Use config values instead of hardcoded thresholds.
- Save intermediate files for auditability.
- Make the pipeline reproducible.
- Keep all removed ETFs with reasons, because this helps with the project write-up.
- Do not optimize for speed yet unless the data pull is too slow.