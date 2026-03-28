#!/usr/bin/env python3
"""
Hair Glue Project — M2.3 Regulatory Data Integration

Sources regulatory and classification data from multiple free, public APIs:
  1. EPA CompTox Dashboard API — DTXSID resolution (confirms TSCA listing)
  2. PubChem PUG View API — aggregated regulatory data:
     - REACH registration & restriction status
     - California Prop 65 listing (via CSCP authoritative lists)
     - IARC carcinogen classification
     - CSCP reportable ingredient status
     - FDA requirements
  3. CompTox DTXSID as a bonus identifier for cross-referencing

Strategy:
  Step 1: Resolve all CASRNs to DTXSIDs via CompTox Dashboard API
  Step 2: For each chemical with a PubChem CID, fetch regulatory + carcinogen data
  Step 3: Parse and structure regulatory flags into a flat table
  Step 4: Save to warehouse/ref_chemicals_regulatory.parquet

Outputs:
- warehouse/ref_chemicals_regulatory.parquet
- reports/M2.3_regulatory_data_report.md
- logs/M2.3_regulatory_data.log
"""

import pandas as pd
import requests
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import date

# Configure logging
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "M2.3_regulatory_data.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE_DIR = Path("warehouse")
REPORTS_DIR = Path("reports")

COMPTOX_SEARCH_URL = "https://comptox.epa.gov/dashboard-api/ccdapp1/search/chemical/equal"
PUBCHEM_PUG_VIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
PUBCHEM_PUG_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

REQUEST_DELAY = 0.4  # seconds between API calls


# ---------------------------------------------------------------------------
# Step 1: CompTox DTXSID Resolution
# ---------------------------------------------------------------------------

def resolve_dtxsid(casrn: str) -> Optional[str]:
    """Resolve a CASRN to a DTXSID via the CompTox Dashboard API."""
    try:
        url = f"{COMPTOX_SEARCH_URL}/{casrn}"
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0].get("dtxsid")
    except Exception as e:
        logger.warning("CompTox lookup failed for %s: %s", casrn, e)
    return None


def resolve_all_dtxsids(casrns: list[str]) -> dict[str, Optional[str]]:
    """Resolve a list of CASRNs to DTXSIDs."""
    mapping: dict[str, Optional[str]] = {}
    for cas in casrns:
        dtxsid = resolve_dtxsid(cas)
        mapping[cas] = dtxsid
        status = dtxsid if dtxsid else "NOT FOUND"
        logger.info("CompTox: %s -> %s", cas, status)
        time.sleep(REQUEST_DELAY)
    return mapping


# ---------------------------------------------------------------------------
# Step 2: PubChem CID Resolution
# ---------------------------------------------------------------------------

def resolve_cid(casrn: str) -> Optional[int]:
    """Resolve a CASRN to a PubChem CID."""
    try:
        url = f"{PUBCHEM_PUG_URL}/compound/name/{casrn}/cids/JSON"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
            if cids:
                return cids[0]
    except Exception as e:
        logger.warning("PubChem CID lookup failed for %s: %s", casrn, e)
    return None


# ---------------------------------------------------------------------------
# Step 3: PubChem Regulatory Data Extraction
# ---------------------------------------------------------------------------

def _get_pug_view_section(cid: int, heading: str) -> Optional[dict]:
    """Fetch a specific PUG View section for a CID."""
    url = f"{PUBCHEM_PUG_VIEW_URL}/{cid}/JSON?heading={heading}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning("PUG View failed for CID %d heading %s: %s", cid, heading, e)
    return None


def _iter_info_texts(section: dict):
    """Yield (name, text) pairs from a PUG View section at any depth."""
    for info in section.get("Information", []):
        name = info.get("Name", "")
        for sv in info.get("Value", {}).get("StringWithMarkup", []):
            yield name, sv.get("String", "")
    for sub in section.get("Section", []):
        yield from _iter_info_texts(sub)


def extract_regulatory_data(cid: int) -> Dict[str, Any]:
    """Extract structured regulatory data for a PubChem CID."""
    result: Dict[str, Any] = {
        "pubchem_cid": cid,
        "reach_registered": False,
        "reach_restricted": False,
        "prop65_listed": False,
        "prop65_types": None,
        "iarc_classification": None,
        "cscp_reportable": False,
        "cscp_hazard_traits": None,
        "cscp_authoritative_lists": None,
        "fda_requirements": None,
        "nz_epa_status": None,
        "regulatory_sources": [],
    }

    # --- Regulatory Information section ---
    reg_data = _get_pug_view_section(cid, "Regulatory+Information")
    time.sleep(REQUEST_DELAY)

    if reg_data:
        record = reg_data.get("Record", {})
        for sec in record.get("Section", []):
            for sub in sec.get("Section", []):
                for name, text in _iter_info_texts(sub):
                    name_lower = name.lower()
                    text_lower = text.lower()

                    # REACH
                    if "reach registered" in name_lower:
                        result["reach_registered"] = True
                        result["regulatory_sources"].append("REACH")
                    if "reach restricted" in name_lower:
                        result["reach_restricted"] = True

                    # CSCP / Prop 65
                    if "cscp" in name_lower:
                        result["cscp_reportable"] = True
                        if "hazard traits" in text_lower:
                            traits = text.replace("Hazard Traits - ", "").strip()
                            result["cscp_hazard_traits"] = traits
                        if "authoritative list" in text_lower:
                            lists_str = text.replace("Authoritative List - ", "").strip()
                            result["cscp_authoritative_lists"] = lists_str
                            if "prop 65" in text_lower or "proposition 65" in text_lower:
                                result["prop65_listed"] = True
                                result["regulatory_sources"].append("Prop65")

                    # Standalone Prop 65 mentions
                    if "prop 65" in text_lower or "proposition 65" in text_lower:
                        result["prop65_listed"] = True

                    # FDA
                    if "fda" in name_lower:
                        if result["fda_requirements"]:
                            result["fda_requirements"] += "; " + text[:200]
                        else:
                            result["fda_requirements"] = text[:200]

                    # NZ EPA
                    if "new zealand" in name_lower:
                        result["nz_epa_status"] = text[:200]

    # --- Carcinogen Classification section ---
    carc_data = _get_pug_view_section(cid, "Carcinogen+Classification")
    time.sleep(REQUEST_DELAY)

    if carc_data:
        record = carc_data.get("Record", {})
        for sec in record.get("Section", []):
            for sub in sec.get("Section", []):
                for sub2 in sub.get("Section", []):
                    for info in sub2.get("Information", []):
                        for sv in info.get("Value", {}).get("StringWithMarkup", []):
                            txt = sv.get("String", "")
                            if "group" in txt.lower() and (
                                "carcinogenic" in txt.lower()
                                or "possibly" in txt.lower()
                                or "probably" in txt.lower()
                            ):
                                result["iarc_classification"] = txt.strip()
                                result["regulatory_sources"].append("IARC")
                                break

    # Deduplicate sources
    result["regulatory_sources"] = list(dict.fromkeys(result["regulatory_sources"]))

    return result


# ---------------------------------------------------------------------------
# Step 4: Main Pipeline
# ---------------------------------------------------------------------------

def build_regulatory_table() -> pd.DataFrame:
    """Build the regulatory data table for all identified chemicals."""
    # Load ref_chemicals from M0.3
    ref_path = WAREHOUSE_DIR / "ref_chemicals.parquet"
    if not ref_path.exists():
        raise FileNotFoundError(f"Missing {ref_path}. Run M0.3 first.")

    ref_df = pd.read_parquet(ref_path)
    casrns = ref_df["casrn"].dropna().unique().tolist()
    logger.info("Loaded %d chemicals (%d with CASRN)", len(ref_df), len(casrns))

    # Also load hazard data for CIDs
    hazard_path = WAREHOUSE_DIR / "ref_chemicals_hazard.parquet"
    cid_map: dict[str, Optional[int]] = {}
    if hazard_path.exists():
        hazard_df = pd.read_parquet(hazard_path)
        # ref_chemicals has cid column
        for _, row in ref_df.iterrows():
            cas = row.get("casrn")
            cid = row.get("cid")
            if pd.notna(cas) and pd.notna(cid):
                cid_map[cas] = int(cid)

    # Step 1: Resolve DTXSIDs
    logger.info("--- Step 1: Resolving DTXSIDs via CompTox Dashboard API ---")
    dtxsid_map = resolve_all_dtxsids(casrns)
    dtxsid_count = sum(1 for v in dtxsid_map.values() if v)
    logger.info("DTXSID resolved: %d/%d", dtxsid_count, len(casrns))

    # Step 2: Resolve any missing CIDs
    logger.info("--- Step 2: Resolving PubChem CIDs ---")
    for cas in casrns:
        if cas not in cid_map or cid_map[cas] is None:
            cid = resolve_cid(cas)
            cid_map[cas] = cid
            logger.info("PubChem CID: %s -> %s", cas, cid)
            time.sleep(REQUEST_DELAY)

    cid_count = sum(1 for v in cid_map.values() if v)
    logger.info("PubChem CIDs resolved: %d/%d", cid_count, len(casrns))

    # Step 3: Fetch regulatory data from PubChem
    logger.info("--- Step 3: Fetching regulatory data from PubChem PUG View ---")
    rows = []
    for cas in casrns:
        cid = cid_map.get(cas)
        dtxsid = dtxsid_map.get(cas)

        # Get canonical name from ref_chemicals
        name_row = ref_df[ref_df["casrn"] == cas]
        canonical_name = (
            name_row["canonical_name"].iloc[0]
            if len(name_row) > 0 and pd.notna(name_row["canonical_name"].iloc[0])
            else None
        )

        row: Dict[str, Any] = {
            "casrn": cas,
            "canonical_name": canonical_name,
            "dtxsid": dtxsid,
            "pubchem_cid": cid,
            "tsca_listed": dtxsid is not None,  # DTXSID existence implies TSCA listing
        }

        if cid:
            reg_data = extract_regulatory_data(cid)
            row.update({
                "reach_registered": reg_data["reach_registered"],
                "reach_restricted": reg_data["reach_restricted"],
                "prop65_listed": reg_data["prop65_listed"],
                "prop65_types": reg_data.get("prop65_types"),
                "iarc_classification": reg_data["iarc_classification"],
                "cscp_reportable": reg_data["cscp_reportable"],
                "cscp_hazard_traits": reg_data["cscp_hazard_traits"],
                "cscp_authoritative_lists": reg_data["cscp_authoritative_lists"],
                "fda_requirements": reg_data["fda_requirements"],
                "nz_epa_status": reg_data["nz_epa_status"],
                "regulatory_sources": "|".join(reg_data["regulatory_sources"]),
            })
            logger.info(
                "Regulatory: %s (CID %d) — REACH=%s Prop65=%s IARC=%s CSCP=%s",
                cas, cid,
                reg_data["reach_registered"],
                reg_data["prop65_listed"],
                reg_data["iarc_classification"] or "None",
                reg_data["cscp_reportable"],
            )
        else:
            row.update({
                "reach_registered": None,
                "reach_restricted": None,
                "prop65_listed": None,
                "prop65_types": None,
                "iarc_classification": None,
                "cscp_reportable": None,
                "cscp_hazard_traits": None,
                "cscp_authoritative_lists": None,
                "fda_requirements": None,
                "nz_epa_status": None,
                "regulatory_sources": None,
            })
            logger.warning("No PubChem CID for %s — regulatory data unavailable", cas)

        row["data_source"] = "comptox+pubchem_pugview"
        row["fetched_date"] = str(date.today())
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report(df: pd.DataFrame) -> str:
    """Generate a markdown report for the regulatory data."""
    total = len(df)
    tsca_count = df["tsca_listed"].sum()
    reach_count = df["reach_registered"].fillna(False).sum()
    reach_restricted_count = df["reach_restricted"].fillna(False).sum()
    prop65_count = df["prop65_listed"].fillna(False).sum()
    iarc_count = df["iarc_classification"].notna().sum()
    cscp_count = df["cscp_reportable"].fillna(False).sum()
    dtxsid_count = df["dtxsid"].notna().sum()

    report = f"""# M2.3 Regulatory Data Integration Report

**Generated:** {date.today()}
**Data Sources:** EPA CompTox Dashboard API, PubChem PUG View API
**Chemicals Processed:** {total}

---

## Executive Summary

1. **{tsca_count}/{total}** chemicals confirmed on EPA TSCA inventory (US commercial use)
2. **{prop65_count}/{total}** chemicals listed under California Proposition 65
3. **{reach_count}/{total}** chemicals have EU REACH registration; **{reach_restricted_count}** are REACH-restricted
4. **{iarc_count}/{total}** chemicals have IARC carcinogen classifications
5. **{cscp_count}/{total}** chemicals are CSCP reportable ingredients

## Data Coverage

| Regulatory Source | Chemicals | Coverage |
|-------------------|-----------|----------|
| EPA TSCA (via DTXSID) | {tsca_count}/{total} | {tsca_count/total*100:.1f}% |
| CompTox DTXSID resolved | {dtxsid_count}/{total} | {dtxsid_count/total*100:.1f}% |
| REACH Registered | {reach_count}/{total} | {reach_count/total*100:.1f}% |
| REACH Restricted | {reach_restricted_count}/{total} | {reach_restricted_count/total*100:.1f}% |
| California Prop 65 | {prop65_count}/{total} | {prop65_count/total*100:.1f}% |
| IARC Classification | {iarc_count}/{total} | {iarc_count/total*100:.1f}% |
| CSCP Reportable | {cscp_count}/{total} | {cscp_count/total*100:.1f}% |

## IARC Carcinogen Classifications

"""
    iarc_df = df[df["iarc_classification"].notna()][["casrn", "canonical_name", "iarc_classification"]]
    if len(iarc_df) > 0:
        report += "| CASRN | Chemical | IARC Classification |\n"
        report += "|-------|----------|--------------------|\n"
        for _, row in iarc_df.iterrows():
            name = str(row["canonical_name"])[:40] if pd.notna(row["canonical_name"]) else "Unknown"
            report += f"| {row['casrn']} | {name} | {row['iarc_classification']} |\n"
    else:
        report += "*No IARC classifications found.*\n"

    report += """
## Proposition 65 Chemicals

"""
    prop65_df = df[df["prop65_listed"].fillna(False)][["casrn", "canonical_name", "cscp_hazard_traits"]]
    if len(prop65_df) > 0:
        report += "| CASRN | Chemical | Hazard Traits |\n"
        report += "|-------|----------|---------------|\n"
        for _, row in prop65_df.iterrows():
            name = str(row["canonical_name"])[:40] if pd.notna(row["canonical_name"]) else "Unknown"
            traits = str(row["cscp_hazard_traits"])[:60] if pd.notna(row["cscp_hazard_traits"]) else "—"
            report += f"| {row['casrn']} | {name[:40]} | {traits[:60]} |\n"
    else:
        report += "*No Prop 65 chemicals found.*\n"

    report += """
## REACH Restricted Chemicals

"""
    reach_r = df[df["reach_restricted"].fillna(False)][["casrn", "canonical_name"]]
    if len(reach_r) > 0:
        report += "| CASRN | Chemical |\n"
        report += "|-------|----------|\n"
        for _, row in reach_r.iterrows():
            name = str(row["canonical_name"])[:50] if pd.notna(row["canonical_name"]) else "Unknown"
            report += f"| {row['casrn']} | {name} |\n"
    else:
        report += "*No REACH-restricted chemicals found.*\n"

    report += """
## Full Regulatory Matrix

| CASRN | DTXSID | TSCA | REACH | Prop 65 | IARC | CSCP |
|-------|--------|------|-------|---------|------|------|
"""
    for _, row in df.iterrows():
        tsca = "✅" if row["tsca_listed"] else "❌"
        reach = "✅" if row.get("reach_registered") else "❌"
        p65 = "✅" if row.get("prop65_listed") else "❌"
        iarc_raw = row.get("iarc_classification")
        if pd.notna(iarc_raw):
            iarc = str(iarc_raw).split(":")[0] if ":" in str(iarc_raw) else str(iarc_raw)[:15]
        else:
            iarc = "—"
        cscp = "✅" if row.get("cscp_reportable") else "❌"
        dtxsid = row.get("dtxsid") if pd.notna(row.get("dtxsid")) else "—"
        report += f"| {row['casrn']} | {dtxsid} | {tsca} | {reach} | {p65} | {iarc} | {cscp} |\n"

    report += f"""
## Methodology

1. **TSCA Status:** Resolved via EPA CompTox Dashboard API (`/search/chemical/equal/{{casrn}}`).
   DTXSID assignment confirms presence in the TSCA inventory.
2. **REACH, Prop 65, CSCP, FDA:** Extracted from PubChem PUG View API
   (`/rest/pug_view/data/compound/{{cid}}/JSON?heading=Regulatory+Information`).
3. **IARC Classification:** Extracted from PubChem PUG View
   (`heading=Carcinogen+Classification`).
4. **Rate limiting:** {REQUEST_DELAY}s delay between API calls to respect server limits.

## Data Sources

- EPA CompTox Dashboard: https://comptox.epa.gov/dashboard/
- PubChem PUG View: https://pubchem.ncbi.nlm.nih.gov/docs/pug-view
- No API keys required for either source.
"""
    return report


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    """Run the full regulatory data integration pipeline."""
    logger.info("=" * 60)
    logger.info("M2.3 Regulatory Data Integration — Starting")
    logger.info("=" * 60)

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build the regulatory table
    df = build_regulatory_table()

    # Save parquet
    output_path = WAREHOUSE_DIR / "ref_chemicals_regulatory.parquet"
    df.to_parquet(output_path, index=False)
    logger.info("Saved %d rows to %s", len(df), output_path)

    # Generate report
    report = generate_report(df)
    report_path = REPORTS_DIR / "M2.3_regulatory_data_report.md"
    report_path.write_text(report)
    logger.info("Report saved to %s", report_path)

    # Summary
    logger.info("=" * 60)
    logger.info("M2.3 Complete — %d chemicals processed", len(df))
    logger.info("  TSCA listed: %d", df["tsca_listed"].sum())
    logger.info("  REACH registered: %d", df["reach_registered"].fillna(False).sum())
    logger.info("  Prop 65 listed: %d", df["prop65_listed"].fillna(False).sum())
    logger.info("  IARC classified: %d", df["iarc_classification"].notna().sum())
    logger.info("  CSCP reportable: %d", df["cscp_reportable"].fillna(False).sum())
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
