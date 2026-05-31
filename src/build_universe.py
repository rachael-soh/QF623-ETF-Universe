"""
Main pipeline: build the clean ETF master universe.

Run with:
    python -m src.build_universe --config config/universe_config.yaml
"""

import argparse
from pathlib import Path

import pandas as pd
import yaml

from src.wrds_connection import get_wrds_connection
from src.load_etf_master import load_etf_master
from src.load_etf_prices import load_etf_prices
from src.filters import apply_master_filters, apply_quality_filters
from src.screening_metrics import calculate_screening_metrics
from src.report import generate_universe_report


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def _save(df: pd.DataFrame, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    print(f"  Saved: {p}  ({len(df):,} rows)")


def run_pipeline(config_path: str) -> None:
    config = load_config(config_path)
    save_raw = config.get("output", {}).get("save_raw", True)
    save_interim = config.get("output", {}).get("save_interim", True)

    print("\n=== Step 1: Connect to WRDS ===")
    db = get_wrds_connection()

    print("\n=== Step 2: Load ETF master list ===")
    master_df = load_etf_master(db, config)

    print("\n=== Step 3: Apply master filters (US-listed, ETF, leveraged, inverse) ===")
    candidate_df = apply_master_filters(master_df, config)
    if save_interim:
        _save(candidate_df, "data/interim/candidate_etf_universe.csv")

    print("\n=== Step 4: Load daily prices ===")
    tickers = candidate_df["ticker"].dropna().unique().tolist()
    price_df = load_etf_prices(db, tickers, config)

    db.close()

    print("\n=== Step 5: Calculate screening metrics ===")
    metrics_df = calculate_screening_metrics(price_df, config)
    if save_interim:
        _save(metrics_df, "data/interim/etf_screening_metrics.csv")

    print("\n=== Step 6: Apply quality / liquidity / stale-price filters ===")
    filtered_df = apply_quality_filters(candidate_df, metrics_df, config)

    final_df = filtered_df[filtered_df["keep_flag"]].copy().reset_index(drop=True)
    excluded_df = filtered_df[~filtered_df["keep_flag"]].copy().reset_index(drop=True)

    _save(final_df, "data/processed/clean_etf_master_universe.csv")
    if save_interim:
        _save(excluded_df, "data/interim/excluded_etfs_with_reasons.csv")

    print("\n=== Step 7: Generate report ===")
    generate_universe_report(final_df, excluded_df, config, "output/universe_screening_report.md")

    print(f"\nDone. Clean master universe: {len(final_df):,} ETFs.")


def main():
    parser = argparse.ArgumentParser(description="Build clean ETF master universe.")
    parser.add_argument("--config", default="config/universe_config.yaml")
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
