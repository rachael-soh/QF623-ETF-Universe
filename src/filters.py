"""Filtering logic for the ETF universe construction pipeline."""

import pandas as pd

LEVERAGED_KEYWORDS = [
    "2X", "3X", "ULTRA", "ULTRAPRO", "LEVERAGED",
    "DAILY 2X", "DAILY 3X", "BULL 2X", "BULL 3X",
]

INVERSE_KEYWORDS = [
    "INVERSE", "SHORT", "ULTRASHORT", "BEAR",
    "BEAR 1X", "BEAR 2X", "BEAR 3X",
]


def detect_leveraged(fund_name: str, category: str = None) -> bool:
    """Return True if the fund name or category suggests a leveraged ETF."""
    text = fund_name.upper() if fund_name else ""
    if category:
        text += " " + category.upper()
    return any(kw in text for kw in LEVERAGED_KEYWORDS)


def detect_inverse(fund_name: str, category: str = None) -> bool:
    """Return True if the fund name or category suggests an inverse ETF."""
    text = fund_name.upper() if fund_name else ""
    if category:
        text += " " + category.upper()
    return any(kw in text for kw in INVERSE_KEYWORDS)


def is_us_listed(row: pd.Series) -> bool:
    """Return True if the ETF is US-listed."""
    exchange = str(row.get("exchange", "")).upper()
    country = str(row.get("country", "")).upper()
    # Exact-match set for short exchange codes
    us_exact = {"NYSE", "NASDAQ", "ARCX", "BATS", "CBOE", "AMEX", "NYSEARCA"}
    # Substring match for full exchange names from ETF Global (e.g. "NYSE Arca, Inc.")
    us_fragments = ["NYSE", "NASDAQ", "CBOE", "BATS"]
    if exchange in us_exact:
        return True
    if any(frag in exchange for frag in us_fragments):
        return True
    if country in {"US", "USA", "UNITED STATES", "UNITED_STATES"}:
        return True
    return False


def is_etf(row: pd.Series) -> bool:
    """Return True if the row represents an ETF."""
    sec_type = str(row.get("security_type", "")).upper()
    if "ETF" in sec_type:
        return True
    if sec_type in {"", "NAN", "NONE"}:
        return True
    return False


def apply_master_filters(master_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Apply initial categorical filters (US-listed, ETF, leveraged, inverse).
    Adds leveraged_flag, inverse_flag, and leverage_inverse_detection_method columns.
    """
    df = master_df.copy()

    has_lev_flag = "is_leveraged" in df.columns
    has_inv_flag = "is_inverse" in df.columns

    def _lev_flag(row):
        if has_lev_flag and pd.notna(row.get("is_leveraged")):
            return bool(row["is_leveraged"]), "official_flag"
        return detect_leveraged(str(row.get("fund_name", "")), str(row.get("category", ""))), "keyword_fallback"

    def _inv_flag(row):
        if has_inv_flag and pd.notna(row.get("is_inverse")):
            return bool(row["is_inverse"]), "official_flag"
        return detect_inverse(str(row.get("fund_name", "")), str(row.get("category", ""))), "keyword_fallback"

    lev_results = df.apply(_lev_flag, axis=1)
    inv_results = df.apply(_inv_flag, axis=1)

    df["leveraged_flag"] = [r[0] for r in lev_results]
    df["inverse_flag"] = [r[0] for r in inv_results]
    df["leverage_inverse_detection_method"] = [r[1] for r in lev_results]

    keep = pd.Series([True] * len(df), index=df.index)
    if config.get("exclude_leveraged", True):
        keep &= ~df["leveraged_flag"]
    if config.get("exclude_inverse", True):
        keep &= ~df["inverse_flag"]
    keep &= df.apply(is_us_listed, axis=1)
    keep &= df.apply(is_etf, axis=1)

    result = df[keep].copy().reset_index(drop=True)
    print(f"  Master filters: {len(master_df):,} → {len(result):,} ETFs (removed {len(master_df) - len(result):,})")
    return result


def apply_quality_filters(
    universe_df: pd.DataFrame, metrics_df: pd.DataFrame, config: dict
) -> pd.DataFrame:
    """
    Merge master ETF info with screening metrics and apply data-quality,
    liquidity, and stale-price filters.

    Returns the full merged DataFrame with keep_flag and remove_reason columns.
    """
    df = universe_df.merge(metrics_df, on="ticker", how="left")

    min_history = config.get("min_history_years", 3)
    max_missing = config.get("max_missing_data_pct", 0.05)
    liq_cfg = config.get("liquidity", {})
    stale_cfg = config.get("stale_price", {})

    explicit_liq = liq_cfg.get("min_median_dollar_volume")
    pct_cutoff = liq_cfg.get("percentile_cutoff", 0.10)

    # ── Pull all thresholds from config ──────────────────────────────────────
    active_cfg   = config.get("active_etf", {})
    zvol_cfg     = config.get("zero_volume", {})
    exret_cfg    = config.get("extreme_return", {})

    max_days_inactive  = active_cfg.get("max_days_since_last_price", 365)
    max_zvol_ratio     = zvol_cfg.get("max_zero_volume_ratio", 0.10)
    exret_threshold    = exret_cfg.get("single_day_threshold", 0.50)
    max_exret_ratio    = exret_cfg.get("max_extreme_ratio", None)

    end_date = pd.Timestamp(config.get("end_date", "2025-12-31"))

    # ── Coerce boolean flag columns (NaN → False avoids Python truthiness bug) ─
    for flag_col in ("stale_price_flag", "extreme_return_flag"):
        df[flag_col] = pd.to_numeric(
            df.get(flag_col, pd.Series(0, index=df.index)), errors="coerce"
        ).fillna(0).astype(bool)

    # ── Identifier quality: flag tickers with no price link ──────────────────
    # (history_years is NaN when no price data was found for that ticker)
    no_price_mask = df["history_years"].isna()

    # ── Liquidity cutoff (computed on ETFs that pass all other hard filters) ──
    if explicit_liq is None:
        pre_liq_mask = (
            ~no_price_mask
        ) & (
            df["history_years"].fillna(0) >= min_history
        ) & (
            df["missing_data_pct"].fillna(1) <= max_missing
        ) & (
            ~df["stale_price_flag"]
        ) & (
            df["days_since_last_price"].fillna(9999) <= max_days_inactive
        ) & (
            df["zero_volume_ratio"].fillna(1) <= max_zvol_ratio
        )
        valid_vol = df.loc[pre_liq_mask, "recent_median_dollar_volume"].dropna()
        liq_cutoff = float(valid_vol.quantile(pct_cutoff)) if len(valid_vol) > 0 else 0.0
    else:
        liq_cutoff = float(explicit_liq)

    df["liquidity_cutoff_used"] = liq_cutoff

    # ── Build remove_reason per ETF ───────────────────────────────────────────
    reasons = []
    for _, row in df.iterrows():
        r = []

        # Categorical filters (should mostly be empty here — master filters ran first)
        if not is_us_listed(row):
            r.append("Not US-listed")
        if not is_etf(row):
            r.append("Not ETF")
        if row.get("leveraged_flag", False):
            r.append("Leveraged ETF")
        if row.get("inverse_flag", False):
            r.append("Inverse ETF")

        # Identifier quality
        if pd.isna(row.get("history_years")):
            r.append("No price data found")
            reasons.append("; ".join(r))
            continue   # skip metric-based filters — no data to evaluate

        # Active ETF filter
        days_inactive = row.get("days_since_last_price", 0)
        if pd.notna(days_inactive) and days_inactive > max_days_inactive:
            r.append(f"Inactive (last price {int(days_inactive)}d before end_date)")

        # History filter
        if row["history_years"] < min_history:
            r.append("Insufficient price history")

        # Missing data filter
        if pd.notna(row.get("missing_data_pct")) and row["missing_data_pct"] > max_missing:
            r.append("Too much missing data")

        # Stale price filter
        if row.get("stale_price_flag", False):
            r.append("Stale pricing pattern")

        # Zero-volume filter
        if pd.notna(row.get("zero_volume_ratio")) and row["zero_volume_ratio"] > max_zvol_ratio:
            r.append("Excessive zero-volume days")

        # Recent liquidity filter (use recent window, fall back to full-sample)
        recent_dv = row.get("recent_median_dollar_volume")
        if pd.isna(recent_dv):
            recent_dv = row.get("median_dollar_volume")
        if pd.notna(recent_dv) and recent_dv < liq_cutoff:
            r.append("Below liquidity cutoff")

        # Extreme return — remove only if max_exret_ratio is explicitly set
        if max_exret_ratio is not None:
            exret_ratio = row.get("extreme_return_ratio", 0.0)
            if pd.notna(exret_ratio) and exret_ratio > max_exret_ratio:
                r.append("Excessive extreme returns (data error suspected)")

        reasons.append("; ".join(r))

    df["remove_reason"] = reasons
    df["keep_flag"] = df["remove_reason"] == ""

    kept = df["keep_flag"].sum()
    print(f"  Quality filters: {kept:,} kept, {(~df['keep_flag']).sum():,} removed.")
    return df
