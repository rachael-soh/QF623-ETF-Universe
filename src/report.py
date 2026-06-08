"""Generate the universe screening Markdown report."""

from pathlib import Path

import pandas as pd


def _df_to_md(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a Markdown table without requiring tabulate."""
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([header, sep] + rows)


def generate_universe_report(
    final_df: pd.DataFrame,
    excluded_df: pd.DataFrame,
    config: dict,
    output_path: str,
) -> None:
    """Write a Markdown screening report to output_path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_df = pd.concat([final_df, excluded_df], ignore_index=True)

    def _count_reason(reason_fragment: str) -> int:
        return int(
            excluded_df["remove_reason"].str.contains(reason_fragment, na=False).sum()
        )

    liq_cutoff = (
        final_df["liquidity_cutoff_used"].iloc[0]
        if "liquidity_cutoff_used" in final_df.columns and len(final_df) > 0
        else "N/A"
    )

    lines = []
    lines.append("# ETF Universe Screening Report\n")
    lines.append(
        f"**Date range:** {config.get('start_date')} – {config.get('end_date')}\n"
    )

    lines.append("## Funnel Summary\n")
    lines.append(f"| Step | Count |")
    lines.append(f"|------|-------|")
    lines.append(f"| Raw ETFs pulled from WRDS | {len(all_df):,} |")

    after_us_etf = (
        len(all_df) - _count_reason("Not US-listed") - _count_reason("Not ETF")
    )
    lines.append(f"| After US-listed + ETF type filter | {after_us_etf:,} |")
    lines.append(f"| Removed: Not US-listed | {_count_reason('Not US-listed'):,} |")
    lines.append(f"| Removed: Not ETF | {_count_reason('Not ETF'):,} |")
    lines.append(f"| Removed: Leveraged ETF | {_count_reason('Leveraged ETF'):,} |")
    lines.append(f"| Removed: Inverse ETF | {_count_reason('Inverse ETF'):,} |")
    lines.append(
        f"| Removed: Insufficient price history | {_count_reason('Insufficient price history'):,} |"
    )
    lines.append(
        f"| Removed: Too much missing data | {_count_reason('Too much missing data'):,} |"
    )
    lines.append(
        f"| Removed: Below liquidity cutoff | {_count_reason('Below liquidity cutoff'):,} |"
    )
    lines.append(
        f"| Removed: Stale pricing pattern | {_count_reason('Stale pricing pattern'):,} |"
    )
    lines.append(f"| **Final clean master universe** | **{len(final_df):,}** |")
    lines.append("")

    lines.append("## Screening Parameters\n")
    lines.append(f"- Minimum history: {config.get('min_history_years')} years")
    lines.append(
        f"- Max missing data: {config.get('max_missing_data_pct', 0.05) * 100:.1f}%"
    )
    lines.append(
        f"- Liquidity cutoff (median dollar volume): {liq_cutoff:,.0f}"
        if isinstance(liq_cutoff, (int, float))
        else f"- Liquidity cutoff: {liq_cutoff}"
    )
    stale_cfg = config.get("stale_price", {})
    lines.append(
        f"- Max zero-return ratio: {stale_cfg.get('max_zero_return_ratio', 0.30):.0%}"
    )
    lines.append(
        f"- Max consecutive zero-return days: {stale_cfg.get('max_consecutive_zero_return_days', 10)}"
    )
    lines.append("")

    if "median_dollar_volume" in final_df.columns:
        lines.append("## Top 20 ETFs by Median Dollar Volume\n")
        top20 = final_df.nlargest(20, "median_dollar_volume")[
            ["ticker"]
            + (["fund_name"] if "fund_name" in final_df.columns else [])
            + ["median_dollar_volume"]
        ]
        lines.append(_df_to_md(top20))
        lines.append("")

    if "asset_class" in final_df.columns:
        lines.append("## Asset Class Breakdown\n")
        breakdown = final_df["asset_class"].value_counts().reset_index()
        breakdown.columns = ["asset_class", "count"]
        lines.append(_df_to_md(breakdown))
        lines.append("")

    if "product_structure" in final_df.columns:
        lines.append("## Product Structure Breakdown\n")
        ps_breakdown = final_df["product_structure"].value_counts().reset_index()
        ps_breakdown.columns = ["product_structure", "count"]
        lines.append(_df_to_md(ps_breakdown))
        lines.append("")

    if "category" in final_df.columns:
        lines.append("## Category Breakdown\n")
        cat_breakdown = final_df["category"].value_counts().head(30).reset_index()
        cat_breakdown.columns = ["category", "count"]
        lines.append(_df_to_md(cat_breakdown))
        lines.append("")

    lines.append("## Important Note\n")
    lines.append(
        "> This is a **broad clean master universe**, not the final strategy-specific ETF list.\n"
        "> The strategy team should apply additional filters (momentum, mean-reversion, asset class\n"
        "> preference, correlation, target universe size) on top of this output.\n"
        "> Do **not** treat this list as the final 20–40 ETF portfolio.\n"
    )

    content = "\n".join(lines)
    output_path.write_text(content)
    print(f"  Report saved to {output_path}")
