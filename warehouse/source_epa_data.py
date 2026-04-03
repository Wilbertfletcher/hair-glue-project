#!/usr/bin/env python3
"""
Hair Glue Project — M3.1 EPA Data Integration

Pulls live data from the EPA CCTE API for all chemicals in our warehouse
that have a DTXSID (EPA chemical identifier).

Produces three new parquet files:
  warehouse/ref_chemicals_comptox.parquet   — structure + properties (M3.1a)
  warehouse/ref_chemicals_toxcast.parquet   — ToxCast bioactivity scores (M3.1b)
  warehouse/ref_chemicals_chemexpo.parquet  — ChemExpo exposure data (M3.1c)

Also produces:
  reports/M3.1_epa_data_report.md

Run:
    python warehouse/source_epa_data.py
"""

import logging
import pandas as pd
from datetime import date
from pathlib import Path

from pipeline.extract.ccte_api import (
    get_chemical_details_batch,
    get_bioactivity_batch,
    get_chemexpo_batch,
    get_iris_batch,
)

# ── Logging ───────────────────────────────────────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "M3.1_epa_data.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE = Path("warehouse")
REPORTS = Path("reports")
REPORTS.mkdir(parents=True, exist_ok=True)


# ── Load chemicals with DTXSID ────────────────────────────────────────────────

def load_dtxsid_list() -> pd.DataFrame:
    """
    Load all chemicals that have a DTXSID from the regulatory parquet.
    Returns a DataFrame with columns: casrn, dtxsid, canonical_name.
    """
    reg_path = WAREHOUSE / "ref_chemicals_regulatory.parquet"
    ref_path = WAREHOUSE / "ref_chemicals.parquet"

    if not reg_path.exists():
        raise FileNotFoundError(
            f"Missing {reg_path}. Run warehouse/source_regulatory_data.py first."
        )

    reg = pd.read_parquet(reg_path)
    has_dtxsid = reg[reg["dtxsid"].notna() & (reg["dtxsid"].str.strip() != "")].copy()

    # Join canonical name from ref_chemicals if available
    if ref_path.exists():
        ref = pd.read_parquet(ref_path)[["casrn", "canonical_name"]]
        has_dtxsid = has_dtxsid.merge(ref, on="casrn", how="left")
    else:
        has_dtxsid["canonical_name"] = has_dtxsid.get("canonical_name", None)

    logger.info(
        "Found %d chemicals with DTXSID (out of %d total)",
        len(has_dtxsid),
        len(reg),
    )
    cols = ["casrn", "dtxsid"]
    if "canonical_name" in has_dtxsid.columns:
        cols.append("canonical_name")
    else:
        has_dtxsid["canonical_name"] = None
        cols.append("canonical_name")
    return has_dtxsid[cols].drop_duplicates("casrn")


# ── M3.1a: CompTox Chemical Detail ───────────────────────────────────────────

def run_comptox_detail(dtxsid_list: list, casrn_map: dict) -> pd.DataFrame:
    """Fetch CompTox structure/property data and save parquet."""
    logger.info("=== M3.1a: CompTox Chemical Detail ===")
    records = get_chemical_details_batch(dtxsid_list)

    if not records:
        logger.warning("No CompTox detail records returned.")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Add casrn join key
    df["casrn"] = df["dtxsid"].map(casrn_map)
    df["data_source"] = "ccte_comptox_api"
    df["fetched_date"] = str(date.today())

    out = WAREHOUSE / "ref_chemicals_comptox.parquet"
    df.to_parquet(out, index=False)
    logger.info("Saved %d rows -> %s", len(df), out)
    return df


# ── M3.1b: ToxCast Bioactivity ───────────────────────────────────────────────

def run_toxcast(dtxsid_list: list, casrn_map: dict) -> pd.DataFrame:
    """Fetch ToxCast bioactivity scores and save parquet."""
    logger.info("=== M3.1b: ToxCast Bioactivity ===")
    records = get_bioactivity_batch(dtxsid_list)

    df = pd.DataFrame(records)
    df["casrn"] = df["dtxsid"].map(casrn_map)
    df["data_source"] = "ccte_toxcast_api"
    df["fetched_date"] = str(date.today())

    out = WAREHOUSE / "ref_chemicals_toxcast.parquet"
    df.to_parquet(out, index=False)
    logger.info("Saved %d rows -> %s", len(df), out)
    return df


# ── M3.1c: ChemExpo Exposure Data ────────────────────────────────────────────

def run_chemexpo(dtxsid_list: list, casrn_map: dict) -> pd.DataFrame:
    """Fetch ChemExpo functional-use + product data and save parquet."""
    logger.info("=== M3.1c: ChemExpo Exposure Data ===")
    records = get_chemexpo_batch(dtxsid_list)

    df = pd.DataFrame(records)
    df["casrn"] = df["dtxsid"].map(casrn_map)
    df["data_source"] = "ccte_chemexpo_api"
    df["fetched_date"] = str(date.today())

    out = WAREHOUSE / "ref_chemicals_chemexpo.parquet"
    df.to_parquet(out, index=False)
    logger.info("Saved %d rows -> %s", len(df), out)
    return df


# ── M3.1d: EPA IRIS ──────────────────────────────────────────────────────────

def run_iris(dtxsid_list: list, casrn_map: dict) -> pd.DataFrame:
    """Fetch EPA IRIS reference dose / cancer data and save parquet."""
    logger.info("=== M3.1d: EPA IRIS ===")
    records = get_iris_batch(dtxsid_list)

    df = pd.DataFrame(records)
    df["casrn"] = df["dtxsid"].map(casrn_map)
    df["data_source"] = "ccte_iris_api"
    df["fetched_date"] = str(date.today())

    out = WAREHOUSE / "ref_chemicals_iris.parquet"
    df.to_parquet(out, index=False)
    iris_count = int(df["has_iris"].sum())
    logger.info(
        "IRIS: %d/%d chemicals have assessments -> %s",
        iris_count, len(dtxsid_list), out,
    )
    return df


# ── Report Generation ─────────────────────────────────────────────────────────

def generate_report(
    chem_df: pd.DataFrame,
    tox_df: pd.DataFrame,
    expo_df: pd.DataFrame,
    iris_df: pd.DataFrame,
    source_df: pd.DataFrame,
) -> str:
    total = len(source_df)
    comptox_count = len(chem_df[chem_df["preferred_name"].notna()]) if len(chem_df) > 0 else 0
    tox_tested = (tox_df["assays_tested"] > 0).sum() if len(tox_df) > 0 else 0
    tox_active = (tox_df["assays_active"] > 0).sum() if len(tox_df) > 0 else 0
    expo_found = (expo_df["national_product_count"] > 0).sum() if len(expo_df) > 0 else 0

    report = f"""# M3.1 EPA Data Integration Report

**Generated:** {date.today()}
**Data Source:** EPA CCTE API (api-ccte.epa.gov)
**Chemicals with DTXSID processed:** {total}

---

## Executive Summary

| Tool | Chemicals Enriched | Notes |
|------|--------------------|-------|
| CompTox Chemical Detail (M3.1a) | {comptox_count}/{total} | Structure, formula, molecular mass |
| ToxCast Bioactivity (M3.1b) | {tox_tested}/{total} | Number of assays tested |
| ChemExpo Product Exposure (M3.1c) | {expo_found}/{total} | Found in national product databases |

---

## M3.1a — CompTox Chemical Detail

"""
    if len(chem_df) > 0:
        report += "| CASRN | Official Name | Formula | Molecular Mass | SMILES |\n"
        report += "|-------|--------------|---------|---------------|--------|\n"
        for _, row in chem_df.iterrows():
            name = str(row.get("preferred_name") or "—")[:35]
            formula = str(row.get("molecular_formula") or "—")
            mass = f"{row.get('molecular_mass'):.2f}" if row.get("molecular_mass") else "—"
            smiles = str(row.get("smiles") or "—")[:30]
            report += f"| {row.get('casrn', '—')} | {name} | {formula} | {mass} | {smiles} |\n"
    else:
        report += "*No CompTox detail data retrieved.*\n"

    report += f"""
---

## M3.1b — ToxCast Bioactivity Scores

**{tox_tested}/{total}** chemicals had ToxCast assay data.
**{tox_active}/{total}** chemicals triggered at least one active bioassay hit.

A **ToxCast Activity Score** of 1.0 means the chemical was active in ALL assays tested.
A score of 0.0 means it was active in none.

"""
    if len(tox_df) > 0 and tox_tested > 0:
        active_chems = tox_df[tox_df["assays_active"] > 0].sort_values(
            "activity_score", ascending=False
        )
        report += "### Chemicals with ToxCast Activity (sorted by score)\n\n"
        report += "| CASRN | DTXSID | Assays Tested | Active Hits | Activity Score | Top Hit Categories |\n"
        report += "|-------|--------|--------------|------------|----------------|--------------------|\n"
        for _, row in active_chems.iterrows():
            cats = str(row.get("top_hit_categories") or "—")[:50]
            report += (
                f"| {row.get('casrn', '—')} | {row.get('dtxsid', '—')} "
                f"| {row.get('assays_tested', 0)} | {row.get('assays_active', 0)} "
                f"| {row.get('activity_score', 0):.3f} | {cats} |\n"
            )
    else:
        report += "*No ToxCast activity data returned. Chemicals may not yet be in ToxCast database.*\n"

    report += f"""
---

## M3.1c — ChemExpo Consumer Exposure Data

**{expo_found}/{total}** chemicals found in the ChemExpo national product database.
This tells us how common each chemical is across all consumer products in the U.S.

"""
    if len(expo_df) > 0 and expo_found > 0:
        found = expo_df[expo_df["national_product_count"] > 0].sort_values(
            "national_product_count", ascending=False
        )
        report += "| CASRN | Products in ChemExpo | Functional Uses | Product Categories |\n"
        report += "|-------|---------------------|-----------------|--------------------|\n"
        for _, row in found.iterrows():
            uses = str(row.get("functional_uses") or "—")[:40]
            cats = str(row.get("product_categories") or "—")[:40]
            report += (
                f"| {row.get('casrn', '—')} "
                f"| {row.get('national_product_count', 0)} "
                f"| {uses} | {cats} |\n"
            )
    else:
        report += "*No ChemExpo product data returned.*\n"

    # M3.1d — IRIS section
    iris_count = int(iris_df["has_iris"].sum()) if len(iris_df) > 0 else 0
    report += f"""
---

## M3.1d — EPA IRIS Federal Risk Assessments

**{iris_count}/{total}** chemicals have an EPA IRIS assessment.

IRIS is the federal standard used by EPA, FDA, and OSHA to set safety limits.
It provides reference doses (how much is safe per day) and cancer classifications.

"""
    if iris_count > 0:
        iris_chems = iris_df[iris_df["has_iris"]].copy()
        report += (
            "| CASRN | Chemical | Safe Daily Dose (RfD) "
            "| Safe Air Conc. (RfC) | Tumor Sites | IRIS Link |\n"
        )
        report += (
            "|-------|---------|----------------------"
            "|----------------------|-------------|----------|\n"
        )
        for _, row in iris_chems.iterrows():
            rfd = str(row.get("rfd_chronic") or "—")
            rfc = str(row.get("rfc_chronic") or "—")
            tumors = str(row.get("tumor_sites") or "—")[:30]
            url = str(row.get("iris_url") or "—")
            report += (
                f"| {row.get('casrn', '—')} "
                f"| {row.get('dtxsid', '—')} "
                f"| {rfd} | {rfc} | {tumors} | {url} |\n"
            )
    else:
        report += "*No IRIS assessments found for these chemicals.*\n"

    report += """
---

## Methodology

- **API:** EPA CCTE API via ctx-python — free with API key
- **Authentication:** CTX_API_KEY in `.env`
- **Caching:** SHA-256 keyed JSON in `data/raw/ccte_cache/`
  (delete to force full refresh)
"""
    return report


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("M3.1 EPA Data Integration — Starting")
    logger.info("=" * 60)

    source_df = load_dtxsid_list()
    dtxsid_list = source_df["dtxsid"].tolist()
    casrn_map = dict(zip(source_df["dtxsid"], source_df["casrn"]))

    logger.info("Processing %d chemicals with DTXSID", len(dtxsid_list))

    chem_df = run_comptox_detail(dtxsid_list, casrn_map)
    tox_df = run_toxcast(dtxsid_list, casrn_map)
    expo_df = run_chemexpo(dtxsid_list, casrn_map)
    iris_df = run_iris(dtxsid_list, casrn_map)

    report = generate_report(chem_df, tox_df, expo_df, iris_df, source_df)
    report_path = REPORTS / "M3.1_epa_data_report.md"
    report_path.write_text(report)
    logger.info("Report saved -> %s", report_path)

    logger.info("=" * 60)
    logger.info("M3.1 Complete")
    logger.info(
        "  CompTox enriched: %d/%d",
        len(chem_df[chem_df["preferred_name"].notna()]) if len(chem_df) > 0 else 0,
        len(dtxsid_list),
    )
    logger.info(
        "  ToxCast studies: %d/%d",
        int((tox_df["assays_tested"] > 0).sum()) if len(tox_df) > 0 else 0,
        len(dtxsid_list),
    )
    logger.info(
        "  ChemExpo found: %d/%d",
        int((expo_df["national_product_count"] > 0).sum()) if len(expo_df) > 0 else 0,
        len(dtxsid_list),
    )
    logger.info(
        "  IRIS assessments: %d/%d",
        int(iris_df["has_iris"].sum()) if len(iris_df) > 0 else 0,
        len(dtxsid_list),
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
