import pandas as pd
import numpy as np


def compute_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.sort_values(["ticker", "date"]).copy()

    df["simple_return"] = df.groupby("ticker")["adjusted_price"].pct_change()

    # log-price computation
    log_price = np.log(df["adjusted_price"].where(df["adjusted_price"] > 0))
    df["log_return"] = log_price.groupby(df["ticker"]).diff()

    df = df.dropna(subset=["simple_return", "log_return"], how="all")
    df = df.reset_index(drop=True)
    returns_df = df[["date", "ticker", "adjusted_price", "simple_return", "log_return"]]

    print(
        f"    [INFO] Returns computed: {len(df):,} rows, {df['ticker'].nunique():,} tickers."
    )

    return returns_df


def pivot_returns(returns_df: pd.DataFrame, returns_col: str) -> pd.DataFrame:
    pivot_df = returns_df.pivot(
        index="date", columns="ticker", values=returns_col
    ).sort_index()

    return pivot_df
