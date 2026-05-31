"""
Inspect available WRDS libraries and tables.

Run with:
    python -m src.inspect_wrds

Output: output/wrds_inventory.md
"""

import os
import sys
from pathlib import Path

# Libraries that are likely to contain ETF or price data
ETF_CANDIDATE_LIBRARIES = [
    "etfg",
    "etfglobal",
    "etf_global",
    "crsp",
    "crspq",
    "comp",
    "compd",
    "msf",
    "tfn",
    "mergent",
    "mfl",
]


def list_available_libraries(db) -> list[str]:
    """Return a sorted list of all library names the user can access on WRDS."""
    try:
        libraries = db.list_libraries()
        return sorted(libraries)
    except Exception as e:
        print(f"[WARN] Could not list libraries: {e}")
        return []


def list_tables_for_library(db, library_name: str) -> list[str]:
    """Return a sorted list of tables within a WRDS library."""
    try:
        tables = db.list_tables(library=library_name)
        return sorted(tables)
    except Exception as e:
        print(f"[WARN] Could not list tables for library '{library_name}': {e}")
        return []


def save_wrds_inventory(db, output_path: str) -> None:
    """
    Print and save a Markdown inventory of WRDS libraries and tables
    that are relevant to ETF universe construction.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# WRDS Data Inventory\n")

    # ── All accessible libraries ──────────────────────────────────────────────
    print("Fetching available libraries...")
    all_libraries = list_available_libraries(db)

    lines.append("## All Accessible Libraries\n")
    if all_libraries:
        for lib in all_libraries:
            lines.append(f"- {lib}")
    else:
        lines.append("_No libraries returned or access error._")
    lines.append("")

    # ── ETF / price candidate libraries ──────────────────────────────────────
    # Include any library whose name contains a candidate keyword, plus the
    # explicit candidate list above.
    candidate_keywords = ["etf", "crsp", "comp", "security", "price", "fund"]
    matched_libraries = set(ETF_CANDIDATE_LIBRARIES) & set(all_libraries)
    for lib in all_libraries:
        if any(kw in lib.lower() for kw in candidate_keywords):
            matched_libraries.add(lib)

    lines.append("## Tables in ETF / Price Candidate Libraries\n")
    if matched_libraries:
        for lib in sorted(matched_libraries):
            print(f"  Listing tables in '{lib}'...")
            tables = list_tables_for_library(db, lib)
            lines.append(f"### {lib}\n")
            if tables:
                for t in tables:
                    lines.append(f"- {t}")
            else:
                lines.append("_No tables found or access denied._")
            lines.append("")
    else:
        lines.append("_No candidate libraries found in your WRDS subscription._")
        lines.append("")

    # ── Guidance notes ────────────────────────────────────────────────────────
    lines.append("## Next Steps\n")
    lines.append(
        "After reviewing the tables above, update `config/universe_config.yaml`:\n"
    )
    lines.append("```yaml")
    lines.append("wrds:")
    lines.append("  preferred_etf_library: <library_name>      # e.g. etfg")
    lines.append(
        "  preferred_etf_master_table: <table_name>  # e.g. etfg_global_master"
    )
    lines.append("  preferred_price_library: <library_name>    # e.g. crsp")
    lines.append("  preferred_price_table: <table_name>        # e.g. dsf")
    lines.append("```")
    lines.append("")
    lines.append(
        "> **Tip:** If ETF Global (`etfg`) is available, use it for the master file.\n"
        "> Otherwise use CRSP security master tables filtered to ETFs.\n"
    )

    content = "\n".join(lines)
    output_path.write_text(content)
    print(f"\nInventory saved to: {output_path}")
    print("\n" + content)


def main():
    from src.wrds_connection import get_wrds_connection

    output_path = Path("output/wrds_inventory.md")
    print("Connecting to WRDS...")
    db = get_wrds_connection()
    save_wrds_inventory(db, str(output_path))
    db.close()


if __name__ == "__main__":
    main()
