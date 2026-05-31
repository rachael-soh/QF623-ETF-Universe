"""Calculate ETF-level screening metrics from daily price data."""

import numpy as np
import pandas as pd


def calculate_screening_metrics(price_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Compute per-ticker screening metrics from daily price data.

    Returns a DataFrame with one row per ETF.
    """
    start_date = pd.Timestamp(config.get("start_date", "2015-01-01"))
    end_date   = pd.Timestamp(config.get("end_date",   "2025-12-31"))

    stale_cfg   = config.get("stale_price", {})
    max_zero_ratio  = stale_cfg.get("max_zero_return_ratio",          0.30)
    max_consec_zero = stale_cfg.get("max_consecutive_zero_return_days", 10)

    zvol_cfg        = config.get("zero_volume", {})
    max_zvol_ratio  = zvol_cfg.get("max_zero_volume_ratio", 0.10)

    exret_cfg       = config.get("extreme_return", {})
    exret_threshold = exret_cfg.get("single_day_threshold", 0.50)

    liq_cfg             = config.get("liquidity", {})
    recent_lookback_days = liq_cfg.get("recent_lookback_days", 365)
    recent_cutoff       = end_date - pd.Timedelta(days=recent_lookback_days)

    records = []
    for ticker, grp in price_df.groupby("ticker"):
        grp = grp.sort_values("date").drop_duplicates(subset=["date"])
        ret_col = grp["ret"] if "ret" in grp.columns else grp["return"]

        first_date = grp["date"].min()
        last_date  = grp["date"].max()
        history_years = (last_date - first_date).days / 365.25

        days_since_last_price = (end_date - last_date).days

        # ── Missing data % (over active window only) ─────────────────────────
        window_start = max(first_date, start_date)
        window_end   = min(last_date,  end_date)
        expected_obs = len(pd.bdate_range(start=window_start, end=window_end))
        actual_obs   = len(grp)
        missing_pct  = max(0.0, (expected_obs - actual_obs) / expected_obs) if expected_obs > 0 else 1.0

        # ── Returns ──────────────────────────────────────────────────────────
        returns = pd.to_numeric(ret_col, errors="coerce").dropna()
        ann_vol = float(returns.std() * np.sqrt(252)) if len(returns) > 1 else np.nan

        # ── Stale-price metrics ───────────────────────────────────────────────
        zero_ret_mask  = returns == 0
        zero_ret_ratio = float(zero_ret_mask.mean()) if len(returns) > 0 else 0.0
        max_consec     = _max_consecutive_true(zero_ret_mask)
        stale_flag     = (zero_ret_ratio > max_zero_ratio) or (max_consec > max_consec_zero)

        # ── Dollar volume ─────────────────────────────────────────────────────
        dv = pd.to_numeric(grp.get("dollar_volume", pd.Series(dtype=float)), errors="coerce")
        median_dv = float(dv.median()) if dv.notna().any() else np.nan
        avg_dv    = float(dv.mean())   if dv.notna().any() else np.nan

        # Recent dollar volume (last N calendar days)
        recent_grp = grp[grp["date"] >= recent_cutoff]
        rdv = pd.to_numeric(recent_grp.get("dollar_volume", pd.Series(dtype=float)), errors="coerce")
        recent_median_dv = float(rdv.median()) if rdv.notna().any() else np.nan
        recent_avg_dv    = float(rdv.mean())   if rdv.notna().any() else np.nan

        # ── Zero-volume ratio ─────────────────────────────────────────────────
        vol_series = pd.to_numeric(grp.get("volume", pd.Series(dtype=float)), errors="coerce")
        zero_vol_mask  = (vol_series == 0) | vol_series.isna()
        zero_vol_ratio = float(zero_vol_mask.mean()) if len(vol_series) > 0 else 0.0

        # ── Extreme returns ───────────────────────────────────────────────────
        extreme_mask        = returns.abs() > exret_threshold
        extreme_return_count = int(extreme_mask.sum())
        extreme_return_ratio = float(extreme_mask.mean()) if len(returns) > 0 else 0.0
        extreme_return_flag  = extreme_return_count > 0

        records.append({
            "ticker":                         ticker,
            "first_price_date":               first_date,
            "last_price_date":                last_date,
            "days_since_last_price":          days_since_last_price,
            "history_years":                  round(history_years, 4),
            "num_observations":               actual_obs,
            "expected_observations":          expected_obs,
            "missing_data_pct":               round(missing_pct, 6),
            "median_dollar_volume":           median_dv,
            "average_dollar_volume":          avg_dv,
            "recent_median_dollar_volume":    recent_median_dv,
            "recent_average_dollar_volume":   recent_avg_dv,
            "annualized_volatility":          round(ann_vol, 6) if pd.notna(ann_vol) else np.nan,
            "zero_return_ratio":              round(zero_ret_ratio, 6),
            "max_consecutive_zero_return_days": max_consec,
            "stale_price_flag":               stale_flag,
            "zero_volume_ratio":              round(zero_vol_ratio, 6),
            "extreme_return_count":           extreme_return_count,
            "extreme_return_ratio":           round(extreme_return_ratio, 6),
            "extreme_return_flag":            extreme_return_flag,
        })

    metrics_df = pd.DataFrame(records)
    print(f"  Screening metrics computed for {len(metrics_df):,} tickers.")
    return metrics_df


def _max_consecutive_true(mask: pd.Series) -> int:
    """Return the maximum number of consecutive True values in a boolean Series."""
    if mask.empty:
        return 0
    max_run = current_run = 0
    for val in mask:
        if val:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run
