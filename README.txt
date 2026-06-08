================================================================================
QF 623 Portfolio Management -- Group Project
ETF-Based Long/Short Strategy Research
Singapore Management University, MSc Quantitative Finance
================================================================================

OVERVIEW
--------
This project researches and backtests systematic long/short strategies built
on Exchange-Traded Funds (ETFs). Three primary strategies are explored:

  1. Bond Duration Rotation     -- US nominal Treasury ETFs
  2. Sector Equity Rotation     -- GICS sector ETFs (11 sectors)
  3. Equity Momentum Long/Short -- Russell 1000 proxies (12-1 momentum)

Backtest window: January 2011 to present.
Data source: CRSP daily returns via WRDS.


FILES IN THIS REPOSITORY
-------------------------
README.md
  Full project documentation with setup instructions (renders on GitHub).

README.txt
  This file. Plain-text version for environments that don't render Markdown.

requirements.txt
  Python package dependencies. Install with: pip install -r requirements.txt

.gitignore
  Lists files excluded from version control (large data files, credentials).

PM_GroupProject_Trial1_DataCleaning_7thJun26.ipynb
  Main data cleaning and pipeline notebook. Runs from raw WRDS data through
  to clean return panels ready for strategy backtesting.

momentum_long_short_vincent.py
  Equity momentum long/short backtest on Russell 1000. Reads an Excel input
  file with monthly returns and outputs CSV position/performance files.

etf_long_short_project/data/README.md
  Full documentation of all data files -- what they contain, how to
  regenerate them from WRDS, and important data quality notes.

etf_long_short_project/notebooks/01_data_download.ipynb
  Original WRDS data download script (earlier universe pull).


SETUP INSTRUCTIONS
------------------
1. Python environment
   Requires Python 3.11. Install dependencies:
     pip install -r requirements.txt

2. WRDS credentials (required for data pulls)
   You need an SMU institutional WRDS account. After installing the wrds
   package, set up credentials once:
     python -c "import wrds; wrds.Connection().create_pgpass_file()"

3. ETF universe file
   Obtain clean_etf_master_universe.csv from course materials and place it
   in the project root directory (same level as this README.txt).

4. Run the pipeline
   Open PM_GroupProject_Trial1_DataCleaning_7thJun26.ipynb in Jupyter.
   Run all cells top to bottom. Two cells are marked "ONE-TIME WRDS PULL"
   -- they download raw data from WRDS and save it locally. Skip them on
   subsequent runs once the parquet files exist on your machine.


DATA NOTES
----------
- Raw and processed data files (.parquet, .csv) are NOT committed to this
  repository. See etf_long_short_project/data/README.md for replication.

- WRDS/CRSP data and ETFG universe data are used under institutional licence
  and cannot be redistributed.

- All returns are net of expense ratios: ret_net = ret - (net_expenses / 252)

- Delisted ETFs are included in the backtest panel to avoid survivorship bias.


GROUP MEMBERS
-------------
  Sayandip Ghosh   -- Data pipeline, universe construction, cleaning framework
  Vincent          -- Equity momentum long/short strategy
  (add members)    -- (add contributions)


ACADEMIC USE
------------
Produced for QF 623 Portfolio Management at SMU.
Data used under institutional licence -- not for redistribution.

================================================================================
