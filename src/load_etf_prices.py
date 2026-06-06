"""
Load daily price and volume data from CRSP dsf for candidate ETFs.

CRSP dsf is permno-based.  We resolve tickers → permnos via crsp.dsenames,
then pull from dsf and re-attach the ticker column for downstream use.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def load_etf_prices(db, tickers: list[str], config: dict) -> pd.DataFrame:
    """
    Pull daily price/volume for *tickers* from CRSP dsf.

    Steps:
      1. Resolve tickers → permnos via crsp.dsenames (date-ranged).
      2. Pull dsf for those permnos.
      3. Join ticker back onto price rows.
      4. Compute adjusted price, returns, dollar_volume.
    """
    wrds_cfg = config.get("wrds", {})
    library = wrds_cfg.get("preferred_price_library", "crsp")
    table = wrds_cfg.get("preferred_price_table", "dsf")

    if not library or not table:
        raise ValueError(
            "Price library/table not configured.\n"
            "Run `python -m src.inspect_wrds` then set "
            "`wrds.preferred_price_library` and `wrds.preferred_price_table` "
            "in config/universe_config.yaml."
        )

    start_date = config.get("start_date", "2015-01-01")
    end_date = config.get("end_date", "2025-12-31")

    raw_path = Path("data/raw/wrds_etf_prices_raw.csv")
    if raw_path.exists():
        print(f"  Raw prices cache found at {raw_path} — skipping WRDS query.")
        raw_df = pd.read_csv(raw_path, parse_dates=["date"])
        permno_map = _resolve_permnos(db, tickers, start_date, end_date)
        return _clean_prices(raw_df, permno_map)

    # ── Step 1: ticker → permno via crsp.dsenames ────────────────────────────
    permno_map = _resolve_permnos(db, tickers, start_date, end_date)
    if permno_map.empty:
        print(
            "  [WARN] No permnos resolved for given tickers. Price data will be empty."
        )
        return _empty_price_df()

    permnos = permno_map["permno"].unique().tolist()
    print(f"  Resolved {len(permnos):,} unique permnos from {len(tickers):,} tickers.")

    # ── Step 2: pull dsf in chunks ───────────────────────────────────────────
    chunks = []
    chunk_size = 500
    for i in range(0, len(permnos), chunk_size):
        batch = permnos[i : i + chunk_size]
        perm_list = ", ".join(str(p) for p in batch)
        print(
            f"  Fetching prices for permnos {i+1}–{min(i+chunk_size, len(permnos))} "
            f"of {len(permnos)} ..."
        )
        sql = f"""
            SELECT permno, date, prc, ret, vol, cfacpr, shrout
            FROM {library}.{table}
            WHERE permno IN ({perm_list})
              AND date BETWEEN '{start_date}' AND '{end_date}'
        """
        chunk_df = db.raw_sql(sql, date_cols=["date"])
        chunks.append(chunk_df)

    raw_df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    print(f"  Raw price pull: {len(raw_df):,} rows.")

    if config.get("output", {}).get("save_raw", True):
        raw_path = Path("data/raw/wrds_etf_prices_raw.csv")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_df.to_csv(raw_path, index=False)
        print(f"  Raw prices saved to {raw_path}")

    df = _clean_prices(raw_df, permno_map)
    return df


def _resolve_permnos(
    db, tickers: list[str], start_date: str, end_date: str
) -> pd.DataFrame:
    """
    Return a DataFrame with columns [ticker, permno] by querying crsp.dsenames.
    Uses the dsenames date range to find the permno(s) active during our window.
    """
    chunk_size = 500
    frames = []
    for i in range(0, len(tickers), chunk_size):
        batch = tickers[i : i + chunk_size]
        ticker_list = ", ".join(f"'{t}'" for t in batch)
        sql = f"""
            SELECT DISTINCT ticker, permno
            FROM crsp.dsenames
            WHERE ticker IN ({ticker_list})
              AND namedt <= '{end_date}'
              AND (nameendt >= '{start_date}' OR nameendt IS NULL)
              AND shrcd = 73
        """
        try:
            frames.append(db.raw_sql(sql))
        except Exception as e:
            print(f"  [WARN] dsenames query failed for batch {i}: {e}")

    if not frames:
        return pd.DataFrame(columns=["ticker", "permno"])

    result = pd.concat(frames, ignore_index=True).drop_duplicates()

    # Resolve duplicate ticker → multiple permno mappings by keeping the permno
    # with the most recent nameendt (i.e. the currently/most-recently active one).
    dupes = result[result.duplicated("ticker", keep=False)]
    if not dupes.empty:
        dup_tickers = dupes["ticker"].unique().tolist()
        # Re-query with nameendt to pick the latest mapping
        resolved_frames = []
        for i in range(0, len(dup_tickers), 500):
            batch = dup_tickers[i : i + 500]
            ticker_list = ", ".join(f"'{t}'" for t in batch)
            sql = f"""
                SELECT ticker, permno, nameendt
                FROM crsp.dsenames
                WHERE ticker IN ({ticker_list})
                  AND namedt <= '{end_date}'
                  AND (nameendt >= '{start_date}' OR nameendt IS NULL)
                  AND shrcd = 73
            """
            try:
                resolved_frames.append(db.raw_sql(sql))
            except Exception as e:
                print(f"  [WARN] duplicate-resolution query failed: {e}")

        if resolved_frames:
            dup_df = pd.concat(resolved_frames, ignore_index=True)
            # Sort: NULL nameendt (still active) first, then most recent date
            dup_df["nameendt"] = pd.to_datetime(dup_df["nameendt"], errors="coerce")
            dup_df = dup_df.sort_values(
                "nameendt", ascending=False, na_position="first"
            )
            dup_resolved = dup_df.drop_duplicates("ticker", keep="first")[
                ["ticker", "permno"]
            ]
            # Replace the duplicated rows in result
            result = result[~result["ticker"].isin(dup_tickers)]
            result = pd.concat([result, dup_resolved], ignore_index=True)
            print(f"  Resolved {len(dup_tickers):,} duplicate ticker→permno mappings.")

    return result


def _clean_prices(raw_df: pd.DataFrame, permno_map: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return _empty_price_df()

    df = raw_df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Join ticker onto price data
    df = df.merge(
        permno_map[["permno", "ticker"]].drop_duplicates("permno"),
        on="permno",
        how="left",
    )

    # CRSP prc is negative when it is a bid/ask midpoint — take absolute value
    df["prc"] = pd.to_numeric(df["prc"], errors="coerce").abs()

    # Adjusted price = prc / cfacpr  (cfacpr is the cumulative price adjustment factor)
    df["cfacpr"] = pd.to_numeric(df["cfacpr"], errors="coerce").replace(0, np.nan)
    df["adjusted_price"] = df["prc"] / df["cfacpr"]

    # Rename to canonical names
    df = df.rename(columns={"prc": "price", "ret": "return", "vol": "volume"})

    # Ensure return is numeric
    df["return"] = pd.to_numeric(df["return"], errors="coerce")

    # Compute return from adjusted price where CRSP ret is missing
    df = df.sort_values(["ticker", "date"])
    missing_ret = df["return"].isna()
    if missing_ret.any():
        computed = df.groupby("ticker")["adjusted_price"].pct_change()
        df.loc[missing_ret, "return"] = computed[missing_ret]

    # Dollar volume
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["dollar_volume"] = df["adjusted_price"].abs() * df["volume"]

    # Deduplicate
    df = df.drop_duplicates(subset=["ticker", "date"], keep="last")
    df = df.dropna(subset=["date", "ticker"])
    df = df.reset_index(drop=True)

    print(
        f"  Price data cleaned: {len(df):,} rows, {df['ticker'].nunique():,} tickers."
    )
    return df[
        [
            "date",
            "ticker",
            "price",
            "adjusted_price",
            "return",
            "volume",
            "dollar_volume",
        ]
    ]


def _empty_price_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "ticker",
            "price",
            "adjusted_price",
            "return",
            "volume",
            "dollar_volume",
        ]
    )
