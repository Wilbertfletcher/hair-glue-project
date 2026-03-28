#!/usr/bin/env python3
"""
Hair Glue Project — M2.3 ECHA REACH Registration Detail

Loads the ECHA Registered Substances bulk export and produces
warehouse/ref_chemicals_reach.parquet with tonnage band, registrant
count, and registration type for each of our 13 identified chemicals.

Prerequisites
-------------
Download the ECHA Registered Substances export before running:
  1. Go to:
     https://echa.europa.eu/en/information-on-chemicals/registered-substances
  2. Click "Export" → save as:
     data/raw/echa_registered_substances.xlsx

Usage
-----
    python warehouse/source_reach_detail.py
    # or via CLI:
    python -m pipeline.cli enrich-reach

Outputs
-------
  warehouse/ref_chemicals_reach.parquet
  reports/M2.3_reach_detail_report.md
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.extract.echa_reach import (
    filter_by_casrns,
    load_echa_registered_substances,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WAREHOUSE_DIR = Path("warehouse")
REPORTS_DIR = Path("reports")
LOGS_DIR = Path("logs")
ECHA_FILE = Path("data/raw/echa_registered_substances.xlsx")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_casrns() -> list[str]:
    """Load CAS numbers from ref_chemicals.parquet (M0.3 output)."""
    ref_path = WAREHOUSE_DIR / "ref_chemicals.parquet"
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Missing {ref_path}. Run M0.3 identity resolution first."
        )
    ref_df = pd.read_parquet(ref_path)
    casrns = ref_df["casrn"].dropna().unique().tolist()
    logger.info(
        "Loaded %d CAS numbers from ref_chemicals.parquet", len(casrns)
    )
    return casrns


def _generate_report(df: pd.DataFrame) -> str:
    total = len(df)
    registered = df["reach_registered"].sum()
    unregistered = total - registered
    with_tonnage = df["tonnage_band"].notna().sum()

    lines = [
        "# M2.3 ECHA REACH Registration Detail Report",
        "",
        f"**Generated:** {date.today()}",
        "**Data source:** ECHA Registered Substances bulk export",
        f"**Chemicals queried:** {total}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| REACH registered | {registered}/{total} |",
        f"| Not registered (or not matched) | {unregistered}/{total} |",
        f"| Tonnage band available | {with_tonnage}/{total} |",
        "",
        "## Registration Detail",
        "",
        "| CASRN | Substance Name | Reg. Type"
        " | Tonnage Band | Registrants |",
        "|-------|----------------|-----------|--------------|-------------|",
    ]

    for _, row in df.sort_values("casrn").iterrows():
        name = str(row.get("substance_name") or "—")[:35]
        reg_type = str(row.get("registration_type") or "—")
        tonnage = str(row.get("tonnage_band") or "—")
        count = str(row.get("registrant_count") or "—")
        lines.append(
            f"| {row['casrn']} | {name} | {reg_type}"
            f" | {tonnage} | {count} |"
        )

    lines += [
        "",
        "## Methodology",
        "",
        "REACH registration data sourced from the ECHA Registered Substances",
        "bulk export. Joined to project chemicals by CAS number.",
        "For CAS numbers with multiple registration entries, the row with the",
        "highest registrant count (typically the Full registration) is kept.",
        "",
        "No API key or account required. Re-download the ECHA export",
        "periodically to refresh the data.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("M2.3 ECHA REACH Registration Detail — Starting")
    logger.info("=" * 60)

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    casrns = _load_casrns()

    logger.info("Loading ECHA bulk export from %s ...", ECHA_FILE)
    echa_df = load_echa_registered_substances(ECHA_FILE)
    logger.info("ECHA export loaded: %d substances", len(echa_df))

    result = filter_by_casrns(echa_df, casrns)
    registered = result["reach_registered"].sum()
    logger.info(
        "Matched %d/%d chemicals in ECHA export",
        registered, len(casrns),
    )

    out_path = WAREHOUSE_DIR / "ref_chemicals_reach.parquet"
    result.to_parquet(out_path, index=False)
    logger.info("Saved to %s", out_path)

    report = _generate_report(result)
    report_path = REPORTS_DIR / "M2.3_reach_detail_report.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Report saved to %s", report_path)

    logger.info("=" * 60)
    logger.info(
        "Done — %d/%d chemicals REACH-registered",
        registered, len(casrns),
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
