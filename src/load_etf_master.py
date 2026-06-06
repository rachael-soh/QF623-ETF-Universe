"""Load the broad ETF master list from WRDS ETF Global (etfg.industry)."""

from pathlib import Path

import pandas as pd


# etfg.industry column → canonical name
ETFG_INDUSTRY_RENAME = {
    "composite_ticker": "ticker",
    "description": "fund_name",
    "listing_exchange": "exchange",
    "asset_class": "asset_class",
    "category": "category",
    "inception_date": "inception_date",
    "issuer": "issuer",  # kept as extra info
    "is_levered": "is_leveraged",  # 0/1 numeric in this table
    "is_etn": "is_etn",  # we will drop ETNs
    "is_active": "is_active",
    "aum": "aum",
    "avg_daily_trading_volume": "avg_daily_trading_volume",
    "region": "region",  # used to help infer US-listed
}

CANONICAL = [
    "ticker",
    "fund_name",
    "exchange",
    "country",
    "security_type",
    "asset_class",
    "category",
    "inception_date",
    "cusip",
    "permno",
    "raw_source",
    "is_leveraged",
    "is_inverse",
    # extra useful columns
    "issuer",
    "is_etn",
    "is_active",
    "aum",
    "avg_daily_trading_volume",
    "region",
    "product_structure",
]


def load_etf_master(db, config: dict) -> pd.DataFrame:
    """
    Load the ETF master list from etfg.industry.

    etfg.industry is a time-series table (one row per ticker per date).
    We take the latest available snapshot per ticker.
    """
    wrds_cfg = config.get("wrds", {})
    library = wrds_cfg.get("preferred_etf_library")
    table = wrds_cfg.get("preferred_etf_master_table")

    if not library or not table:
        raise ValueError(
            "ETF master library/table not configured.\n"
            "Run `python -m src.inspect_wrds` then set "
            "`wrds.preferred_etf_library` and `wrds.preferred_etf_master_table` "
            "in config/universe_config.yaml."
        )

    raw_path = Path("data/raw/wrds_etf_master_raw.csv")

    if raw_path.exists():
        print(f"  Raw master cache found at {raw_path} — skipping WRDS query.")
        raw_df = pd.read_csv(raw_path)
        return _clean_master(raw_df, library_hint=library)

    print(f"Loading ETF master from {library}.{table} ...")

    # Pull the latest snapshot per ticker using a window function
    sql = f"""
        SELECT *
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY composite_ticker
                       ORDER BY as_of_date DESC NULLS LAST
                   ) AS rn
            FROM {library}.{table}
        ) t
        WHERE rn = 1
    """
    raw_df = db.raw_sql(sql)
    print(f"  Raw pull: {len(raw_df):,} rows (latest snapshot per ticker).")

    if config.get("output", {}).get("save_raw", True):
        raw_path = Path("data/raw/wrds_etf_master_raw.csv")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_df.to_csv(raw_path, index=False)
        print(f"  Raw master saved to {raw_path}")

    df = _clean_master(raw_df, library_hint=library)
    return df


def _clean_master(raw_df: pd.DataFrame, library_hint: str = "") -> pd.DataFrame:
    df = raw_df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Drop the row-number helper column if present
    df = df.drop(columns=["rn"], errors="ignore")

    # Rename known columns
    rename = {k: v for k, v in ETFG_INDUSTRY_RENAME.items() if k in df.columns}
    df = df.rename(columns=rename)

    # ── Derived / filled columns ──────────────────────────────────────────────
    # security_type: ETNs are not ETFs — flag them but keep in raw; filters will drop
    df["security_type"] = df.get("is_etn", pd.Series(0, index=df.index)).apply(
        lambda x: "ETN" if pd.notna(x) and int(x) == 1 else "ETF"
    )

    # product_structure: finer-grained classification for reporting.
    # Derived from is_etn flag and fund name keywords. Does not drive removal.
    def _product_structure(row) -> str:
        if pd.notna(row.get("is_etn")) and int(row.get("is_etn", 0)) == 1:
            return "ETN"
        name = str(row.get("fund_name", "")).upper()
        if any(
            kw in name
            for kw in [
                "COMMODITY TRUST",
                "GOLD TRUST",
                "SILVER TRUST",
                "OIL FUND",
                "NATURAL GAS FUND",
            ]
        ):
            return "Commodity Trust"
        if any(
            kw in name
            for kw in [
                "CURRENCY",
                "EURO TRUST",
                "YEN TRUST",
                "STERLING TRUST",
                "CURRENCY SHARES",
            ]
        ):
            return "Currency Trust"
        if any(kw in name for kw in ["FUTURES", "ROLL SELECT", "CONTANGO"]):
            return "Futures-Based ETF"
        if any(kw in name for kw in ["ACTIVE", "ACTIVELY MANAGED", "MANAGED ETF"]):
            return "Actively Managed ETF"
        return "ETF"

    df["product_structure"] = df.apply(_product_structure, axis=1)

    # country: ETF Global uses listing_exchange for US detection; set to US
    # for exchanges that are clearly US-based.
    us_exchange_fragments = ["nyse", "nasdaq", "cboe", "bats", "nyse arca"]

    def _infer_country(row):
        exch = str(row.get("exchange", "")).lower()
        if any(frag in exch for frag in us_exchange_fragments):
            return "US"
        # fall back to region
        region = str(row.get("region", "")).lower()
        if "u.s." in region or "united states" in region or region == "us":
            return "US"
        return row.get("region", pd.NA)

    df["country"] = df.apply(_infer_country, axis=1)

    # is_inverse: not in ETF Global — will be detected by keyword in filters.py
    df["is_inverse"] = pd.NA

    # cusip / permno: not in ETF Global industry table
    df["cusip"] = pd.NA
    df["permno"] = pd.NA
    df["raw_source"] = library_hint

    # ── is_leveraged: convert 0/1 numeric to bool ────────────────────────────
    if "is_leveraged" in df.columns:
        df["is_leveraged"] = (
            pd.to_numeric(df["is_leveraged"], errors="coerce").fillna(0).astype(bool)
        )

    # ── String cleanup ────────────────────────────────────────────────────────
    for col in ["ticker", "fund_name", "exchange", "country"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA)

    df = df.dropna(subset=["ticker"])
    df = df[df["ticker"] != ""]

    if "inception_date" in df.columns:
        df["inception_date"] = pd.to_datetime(df["inception_date"], errors="coerce")

    # Keep canonical + any extra columns present
    keep = [c for c in CANONICAL if c in df.columns]
    extras = [c for c in df.columns if c not in CANONICAL]
    df = df[keep + extras].reset_index(drop=True)

    print(f"  ETF master cleaned: {len(df):,} rows.")
    return df
