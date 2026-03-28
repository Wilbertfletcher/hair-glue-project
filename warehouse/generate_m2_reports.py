#!/usr/bin/env python3
"""
Hair Glue Project — M2 Enhanced Report Generation

Generates three cross-source reports combining identity, structure,
hazard, and regulatory data assembled across M0–M2:

  reports/M2_chemical_profiles.md   — per-chemical deep profile
  reports/M2_coverage_summary.md    — data completeness matrix
  reports/M2_enrichment_delta.md    — before/after comparison

Usage
-----
    python warehouse/generate_m2_reports.py
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

WAREHOUSE_DIR = Path("warehouse")
CURATED_DIR = Path("data/curated")
REPORTS_DIR = Path("reports")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all() -> dict[str, pd.DataFrame]:
    """Load all relevant warehouse tables into a dict."""
    tables = {}

    def _load(key: str, path: Path) -> None:
        if path.exists():
            tables[key] = pd.read_parquet(path)
            logger.info("Loaded %s (%d rows)", path.name, len(tables[key]))
        else:
            logger.warning("Missing: %s — skipping", path)
            tables[key] = pd.DataFrame()

    _load("ref_chem",     WAREHOUSE_DIR / "ref_chemicals.parquet")
    _load("hazard",       WAREHOUSE_DIR / "ref_chemicals_hazard.parquet")
    _load("regulatory",   WAREHOUSE_DIR / "ref_chemicals_regulatory.parquet")
    _load("reach",        WAREHOUSE_DIR / "ref_chemicals_reach.parquet")
    _load("dim_chem",     CURATED_DIR   / "dim_chemical.parquet")
    _load(
        "ingredients",
        WAREHOUSE_DIR / "ingredient_identity_matched.parquet",
    )
    _load("products",     WAREHOUSE_DIR / "dim_products.parquet")
    _load("prod_hazard",  WAREHOUSE_DIR / "product_hazard_summary.parquet")

    return tables


def build_master(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join all tables on casrn into one master DataFrame,
    one row per identified chemical.
    """
    base = t["ref_chem"].copy()
    if base.empty:
        return base

    # Structure data from dim_chemical
    struct_cols = [
        "casrn", "smiles", "inchi", "inchikey",
        "molecular_formula", "molecular_weight",
        "chemspider_id", "common_name", "systematic_name",
    ]
    struct = t["dim_chem"][
        [c for c in struct_cols if c in t["dim_chem"].columns]
    ].drop_duplicates("casrn")

    # Hazard
    haz_cols = [
        "casrn", "ghs_hazard_class", "ghs_signal_word",
        "h_codes", "pictograms", "carcinogenicity",
        "reproductive_hazard", "skin_irritation",
    ]
    haz = t["hazard"][
        [c for c in haz_cols if c in t["hazard"].columns]
    ].drop_duplicates("casrn") if not t["hazard"].empty else pd.DataFrame()

    # Regulatory
    reg_cols = [
        "casrn", "dtxsid", "tsca_listed",
        "reach_registered", "reach_restricted",
        "prop65_listed", "iarc_classification",
        "cscp_reportable",
    ]
    reg = t["regulatory"][
        [c for c in reg_cols if c in t["regulatory"].columns]
    ].drop_duplicates("casrn") if not t["regulatory"].empty else pd.DataFrame()

    # REACH detail
    reach_cols = [
        "casrn", "ec_number", "registration_type",
        "tonnage_band", "registrant_count",
    ]
    reach = t["reach"][
        [c for c in reach_cols if c in t["reach"].columns]
    ].drop_duplicates("casrn") if not t["reach"].empty else pd.DataFrame()

    # Merge everything
    df = base
    for other in [struct, haz, reg, reach]:
        if not other.empty and "casrn" in other.columns:
            df = df.merge(other, on="casrn", how="left", suffixes=("", "_r"))

    return df


def product_counts(t: dict) -> pd.DataFrame:
    """Products per chemical (casrn → product count, brand count)."""
    ingr = t["ingredients"]
    if ingr.empty or "casrn" not in ingr.columns:
        return pd.DataFrame(columns=["casrn", "product_count", "brand_count"])

    merged = ingr.merge(
        t["products"][["product_id", "brand"]],
        on="product_id", how="left",
    )
    counts = (
        merged.groupby("casrn")
        .agg(
            product_count=("product_id", "nunique"),
            brand_count=("brand", "nunique"),
        )
        .reset_index()
    )
    return counts


# ---------------------------------------------------------------------------
# Report 1 — Chemical Profiles
# ---------------------------------------------------------------------------

def _yn(val) -> str:
    if pd.isna(val):
        return "—"
    return "Yes" if val else "No"


def _val(val, default="—") -> str:
    if pd.isna(val) or val is None or str(val).strip() in ("", "nan", "None"):
        return default
    return str(val).strip()


def generate_chemical_profiles(
    master: pd.DataFrame,
    pc: pd.DataFrame,
) -> str:
    today = date.today()
    lines = [
        "# M2 Chemical Profiles",
        "",
        f"**Generated:** {today}  ",
        f"**Chemicals profiled:** {len(master)}",
        "",
        "Each profile combines identity (M0), hazard (M1), "
        "structure (M2.2), and regulatory data (M2.3).",
        "",
        "---",
        "",
    ]

    for _, row in master.sort_values("casrn").iterrows():
        casrn = _val(row.get("casrn"))
        name = _val(row.get("canonical_name"),
                    _val(row.get("common_name"), casrn))

        # product/brand counts
        pc_row = pc[pc["casrn"] == casrn]
        n_products = int(pc_row["product_count"].iloc[0]) \
            if len(pc_row) > 0 else 0
        n_brands = int(pc_row["brand_count"].iloc[0]) \
            if len(pc_row) > 0 else 0

        lines += [
            f"## {name}",
            "",
            "### Identity",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| CAS Number | {casrn} |",
            f"| EC Number | {_val(row.get('ec_number'))} |",
            f"| Canonical Name | {_val(row.get('canonical_name'))} |",
            f"| PubChem CID | {_val(row.get('cid'))} |",
            f"| ChemSpider ID | {_val(row.get('chemspider_id'))} |",
            f"| DTXSID | {_val(row.get('dtxsid'))} |",
            "",
            "### Structure",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| SMILES | `{_val(row.get('smiles'))}` |",
            f"| InChIKey | {_val(row.get('inchikey'))} |",
            f"| Molecular Formula | {_val(row.get('molecular_formula'))} |",
            f"| Molecular Weight | {_val(row.get('molecular_weight'))} |",
            "",
            "### Hazard",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| GHS Hazard Classes | {_val(row.get('ghs_hazard_class'))} |",
            f"| Signal Word | {_val(row.get('ghs_signal_word'))} |",
            f"| H-Codes | {_val(row.get('h_codes'))} |",
            f"| Pictograms | {_val(row.get('pictograms'))} |",
            f"| Carcinogenicity | {_val(row.get('carcinogenicity'))} |",
            "| Reproductive Hazard | "
            f"{_val(row.get('reproductive_hazard'))} |",
            f"| Skin Irritation | {_val(row.get('skin_irritation'))} |",
            "",
            "### Regulatory",
            f"| Framework | Status |",
            f"|-----------|--------|",
            f"| TSCA (US) | {_yn(row.get('tsca_listed'))} |",
            f"| REACH Registered | {_yn(row.get('reach_registered'))} |",
            f"| REACH Restricted | {_yn(row.get('reach_restricted'))} |",
            f"| REACH Tonnage Band | {_val(row.get('tonnage_band'))} |",
            f"| REACH Registrants | {_val(row.get('registrant_count'))} |",
            f"| California Prop 65 | {_yn(row.get('prop65_listed'))} |",
            "| IARC Classification | "
            f"{_val(row.get('iarc_classification'))} |",
            f"| CSCP Reportable | {_yn(row.get('cscp_reportable'))} |",
            "",
            "### Product Presence",
            f"Found in **{n_products} products** across "
            f"**{n_brands} brands**.",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report 2 — Coverage Summary
# ---------------------------------------------------------------------------

def generate_coverage_summary(master: pd.DataFrame) -> str:
    total = len(master)
    if total == 0:
        return "# M2 Coverage Summary\n\nNo data.\n"

    def _pct(n: int) -> str:
        return f"{n}/{total} ({n/total*100:.0f}%)"

    def _count(col: str, truthy: bool = True) -> int:
        if col not in master.columns:
            return 0
        if truthy:
            return int(
                master[col].infer_objects(copy=False)
                .fillna(False).astype(bool).sum()
            )
        return int(master[col].notna().sum())

    rows = [
        ("CAS Number",          _count("casrn", False)),
        ("PubChem CID",         _count("cid", False)),
        ("ChemSpider ID",       _count("chemspider_id", False)),
        ("SMILES",              _count("smiles", False)),
        ("InChIKey",            _count("inchikey", False)),
        ("Molecular Formula",   _count("molecular_formula", False)),
        ("GHS Hazard Class",    _count("ghs_hazard_class", False)),
        ("Signal Word",         _count("ghs_signal_word", False)),
        ("H-Codes",             _count("h_codes", False)),
        ("DTXSID (CompTox)",    _count("dtxsid", False)),
        ("TSCA Listed",         _count("tsca_listed")),
        ("REACH Registered",    _count("reach_registered")),
        ("REACH Tonnage Band",  _count("tonnage_band", False)),
        ("Prop 65",             _count("prop65_listed")),
        ("IARC Classification", _count("iarc_classification", False)),
        ("CSCP Reportable",     _count("cscp_reportable")),
    ]

    lines = [
        "# M2 Data Coverage Summary",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Chemicals in scope:** {total}",
        "",
        "## Completeness by Field",
        "",
        "| Data Field | Coverage | Source |",
        "|------------|----------|--------|",
    ]

    source_map = {
        "CAS Number": "CSCP raw data",
        "PubChem CID": "PubChem (M0.3)",
        "ChemSpider ID": "ChemSpider API (M2.2)",
        "SMILES": "ChemSpider API (M2.2)",
        "InChIKey": "ChemSpider API (M2.2)",
        "Molecular Formula": "ChemSpider API (M2.2)",
        "GHS Hazard Class": "PubChem PUG View (M1.1)",
        "Signal Word": "PubChem PUG View (M1.1)",
        "H-Codes": "PubChem PUG View (M1.1)",
        "DTXSID (CompTox)": "EPA CompTox (M2.3)",
        "TSCA Listed": "EPA CompTox (M2.3)",
        "REACH Registered": "PubChem PUG View (M2.3)",
        "REACH Tonnage Band": "ECHA bulk export (M2.3)",
        "Prop 65": "PubChem PUG View (M2.3)",
        "IARC Classification": "PubChem PUG View (M2.3)",
        "CSCP Reportable": "PubChem PUG View (M2.3)",
    }

    for field, count in rows:
        lines.append(
            f"| {field} | {_pct(count)} | {source_map.get(field, '—')} |"
        )

    # Gap analysis
    gaps = [(f, c) for f, c in rows if c < total]
    lines += [
        "",
        "## Gap Analysis",
        "",
    ]
    if gaps:
        lines += [
            "| Field | Missing | Action |",
            "|-------|---------|--------|",
        ]
        actions = {
            "ChemSpider ID": "1 CAS not in ChemSpider — mixture/trade name",
            "SMILES": "Follows ChemSpider coverage",
            "InChIKey": "Follows ChemSpider coverage",
            "Molecular Formula": "Follows ChemSpider coverage",
            "REACH Tonnage Band": "2 chemicals not in ECHA export — US-only",
            "Prop 65": "Not all chemicals are listed — expected",
            "IARC Classification": "Not all classified by IARC — expected",
            "CSCP Reportable": "Not all chemicals reportable — expected",
        }
        for field, count in gaps:
            missing = total - count
            action = actions.get(field, "Review source data")
            lines.append(f"| {field} | {missing} | {action} |")
    else:
        lines.append("All fields at 100% coverage.")

    lines += [""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report 3 — Enrichment Delta
# ---------------------------------------------------------------------------

def generate_enrichment_delta(
    master: pd.DataFrame,
    t: dict[str, pd.DataFrame],
) -> str:
    total = len(master)

    def _c(col: str, truthy: bool = False) -> int:
        if col not in master.columns:
            return 0
        if truthy:
            return int(
                master[col].infer_objects(copy=False)
                .fillna(False).astype(bool).sum()
            )
        return int(master[col].notna().sum())

    lines = [
        "# M2 Enrichment Delta",
        "",
        f"**Generated:** {date.today()}",
        "",
        "What M2 added vs. the M0/M1 baseline.",
        "",
        "---",
        "",
        "## M2.1 — Fallback Identity Resolution",
        "",
        "| Metric | Before (M0.3) | After (M2.1) |",
        "|--------|--------------|--------------|",
        "| Identity match rate | 61.9% (91/147 rows) "
        "| **100% (147/147 rows)** |",
        "| Unmatched ingredients | 7 unique ingredients | **0** |",
        "| Method | PubChem CAS lookup only "
        "| + PubChem name search + manual mappings |",
        "",
        "Resolved ingredients: Cocamide DEA, Carbon black, "
        "Crystalline silica,",
        "Talc, Mineral oils, Retinol esters, BHA.",
        "",
        "---",
        "",
        "## M2.2 — ChemSpider Structure Enrichment",
        "",
        "New fields added to `dim_chemical`:",
        "",
        "| Field | Coverage |",
        "|-------|----------|",
        f"| SMILES | {_c('smiles')}/{total} |",
        f"| InChIKey | {_c('inchikey')}/{total} |",
        f"| Molecular Formula | {_c('molecular_formula')}/{total} |",
        f"| Molecular Weight | {_c('molecular_weight')}/{total} |",
        f"| ChemSpider ID | {_c('chemspider_id')}/{total} |",
        "",
        "Before M2.2: no structural data existed for any chemical.",
        "",
        "---",
        "",
        "## M2.3 — Regulatory Data",
        "",
        "### New from CompTox + PubChem PUG View",
        "",
        "| Framework | Coverage |",
        "|-----------|----------|",
        f"| TSCA Listed | {_c('tsca_listed', True)}/{total} |",
        f"| REACH Registered | {_c('reach_registered', True)}/{total} |",
        f"| California Prop 65 | {_c('prop65_listed', True)}/{total} |",
        f"| IARC Classification | {_c('iarc_classification')}/{total} |",
        f"| CSCP Reportable | {_c('cscp_reportable', True)}/{total} |",
        "",
        "### New from ECHA Bulk Export",
        "",
        "| Field | Coverage |",
        "|-------|----------|",
        f"| REACH Tonnage Band | {_c('tonnage_band')}/{total} |",
        f"| Registrant Count | {_c('registrant_count')}/{total} |",
        f"| Registration Type | {_c('registration_type')}/{total} |",
        "",
        "Before M2.3: no regulatory framework data existed.",
        "",
        "---",
        "",
        "## Overall M2 Impact",
        "",
        "| Dimension | M0/M1 Baseline | M2 Final |",
        "|-----------|----------------|----------|",
        "| Identity coverage | 61.9% | **100%** |",
        "| Structural data fields | 0 | **5** (SMILES, InChIKey, "
        "formula, weight, CSid) |",
        "| Regulatory frameworks | 0 | **6** (TSCA, REACH, Prop 65, "
        "IARC, CSCP, ECHA tonnage) |",
        "| Cross-source identifiers | PubChem CID only | "
        "+ DTXSID + ChemSpider ID + EC Number |",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("M2 Report Generation — Starting")
    logger.info("=" * 60)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    t = load_all()
    master = build_master(t)
    pc = product_counts(t)

    logger.info("Master table: %d chemicals", len(master))

    # Report 1
    r1 = generate_chemical_profiles(master, pc)
    p1 = REPORTS_DIR / "M2_chemical_profiles.md"
    p1.write_text(r1, encoding="utf-8")
    logger.info("Saved %s", p1)

    # Report 2
    r2 = generate_coverage_summary(master)
    p2 = REPORTS_DIR / "M2_coverage_summary.md"
    p2.write_text(r2, encoding="utf-8")
    logger.info("Saved %s", p2)

    # Report 3
    r3 = generate_enrichment_delta(master, t)
    p3 = REPORTS_DIR / "M2_enrichment_delta.md"
    p3.write_text(r3, encoding="utf-8")
    logger.info("Saved %s", p3)

    logger.info("=" * 60)
    logger.info("Done — 3 reports written to reports/")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
