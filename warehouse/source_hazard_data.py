#!/usr/bin/env python3
"""
Hair Glue Project — M1.1 Hazard Data Sourcing (PubChem PUG View API)

Sources GHS hazard classification data for all chemicals identified in M0.3
using PubChem's PUG View API, which returns structured GHS classification data
including H-codes, P-codes, pictograms, and signal words.

Strategy:
  Phase 1: For chemicals with known PubChem CIDs → direct PUG View lookup
  Phase 2: For chemicals without CIDs → resolve CID by CASRN or name, then PUG View

Outputs:
- warehouse/ref_chemicals_hazard.parquet
- reports/M1.1_hazard_sourcing_report.md
- logs/M1.1_hazard_sourcing.log
"""

import re
import pandas as pd
import requests
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/M1.1_hazard_sourcing.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PUBCHEM_PUG_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_PUG_VIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
WAREHOUSE_DIR = Path("warehouse")
REPORTS_DIR = Path("reports")
LOGS_DIR = Path("logs")

# H-code → hazard class mapping
H_CODE_TO_CLASS = {
    "H300": "Acute Tox", "H301": "Acute Tox", "H302": "Acute Tox", "H303": "Acute Tox",
    "H310": "Acute Tox", "H311": "Acute Tox", "H312": "Acute Tox", "H313": "Acute Tox",
    "H330": "Acute Tox", "H331": "Acute Tox", "H332": "Acute Tox", "H333": "Acute Tox",
    "H314": "Skin Corr", "H315": "Skin Irrit", "H316": "Skin Irrit",
    "H317": "Skin Sens",
    "H318": "Eye Damage", "H319": "Eye Irrit",
    "H334": "Resp Sens", "H335": "Resp Irrit",
    "H340": "Muta", "H341": "Muta",
    "H350": "Carc", "H350i": "Carc", "H351": "Carc",
    "H360": "Repr/Dev", "H361": "Repr/Dev", "H362": "Repr/Dev",
    "H370": "STOT-SE", "H371": "STOT-SE",
    "H372": "STOT-RE", "H373": "STOT-RE",
    "H400": "Aquatic Acute", "H401": "Aquatic Acute", "H402": "Aquatic Acute",
    "H410": "Aquatic Chronic", "H411": "Aquatic Chronic", "H412": "Aquatic Chronic",
    "H413": "Aquatic Chronic",
    "H220": "Flam Gas", "H221": "Flam Gas", "H222": "Flam Aer", "H223": "Flam Aer",
    "H224": "Flam Liq", "H225": "Flam Liq", "H226": "Flam Liq", "H227": "Flam Liq",
    "H228": "Flam Sol",
    "H280": "Gas Press", "H281": "Gas Press",
}

# H-codes that indicate specific hazard categories
REPR_H_CODES = {"H340", "H341", "H360", "H361", "H362"}
CARC_H_CODES = {"H350", "H350i", "H351"}
ACUTE_ORAL_H = {"H300": "Category 1", "H301": "Category 3", "H302": "Category 4", "H303": "Category 5"}
ACUTE_DERM_H = {"H310": "Category 1", "H311": "Category 3", "H312": "Category 4", "H313": "Category 5"}
ACUTE_INH_H = {"H330": "Category 1", "H331": "Category 3", "H332": "Category 4", "H333": "Category 5"}


def _resolve_cid_by_casrn(casrn: str) -> Optional[int]:
    """Resolve PubChem CID from CASRN."""
    try:
        url = f"{PUBCHEM_PUG_URL}/compound/name/{casrn}/cids/JSON"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
            if cids:
                return cids[0]
    except Exception as e:
        logger.debug(f"CID resolve by CASRN failed for {casrn}: {e}")
    return None


def _resolve_cid_by_name(name: str) -> Optional[int]:
    """Resolve PubChem CID from chemical name, trying progressively cleaned variants."""
    variants = _generate_name_variants(name)
    for variant in variants:
        try:
            url = f"{PUBCHEM_PUG_URL}/compound/name/{requests.utils.quote(variant)}/cids/JSON"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                cids = data.get("IdentifierList", {}).get("CID", [])
                if cids:
                    logger.debug(f"  Resolved '{name}' via variant '{variant}' -> CID {cids[0]}")
                    return cids[0]
        except Exception as e:
            logger.debug(f"CID resolve by name failed for '{variant}': {e}")
    return None


def _generate_name_variants(name: str) -> List[str]:
    """Generate cleaned name variants for PubChem lookup."""
    variants = [name]
    # Strip parenthetical qualifiers: "Talc (powder)" → "Talc"
    stripped = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
    if stripped and stripped != name:
        variants.append(stripped)
    # Strip everything after comma: "Silica, crystalline ..." → "Silica"
    comma_stripped = name.split(",")[0].strip()
    if comma_stripped and comma_stripped != name:
        variants.append(comma_stripped)
    # Strip everything after slash: "Retinol/retinyl esters..." → "Retinol"
    slash_stripped = name.split("/")[0].strip()
    if slash_stripped and slash_stripped != name:
        variants.append(slash_stripped)
    # Strip trailing qualifiers after "when", "untreated"
    qualifier_stripped = re.split(r",?\s+(?:when|untreated|mildly|airborne)\b", name, flags=re.IGNORECASE)[0].strip()
    if qualifier_stripped and qualifier_stripped != name and qualifier_stripped not in variants:
        variants.append(qualifier_stripped)
    # Singularize trailing 's': "Mineral oils" → "Mineral oil"
    for v in list(variants):
        if v.endswith("s") and not v.endswith("ss"):
            variants.append(v[:-1])
    return list(dict.fromkeys(variants))  # dedupe, preserve order


def fetch_ghs_from_pugview(cid: int) -> Optional[Dict]:
    """
    Fetch GHS Classification data from PubChem PUG View API.
    Uses the first GHS classification entry (consensus/harmonized).
    """
    try:
        url = f"{PUBCHEM_PUG_VIEW_URL}/{cid}/JSON"
        resp = requests.get(url, params={"heading": "GHS Classification"}, timeout=15)
        if resp.status_code != 200:
            logger.debug(f"PUG View returned {resp.status_code} for CID {cid}")
            return None

        data = resp.json()
        sections = data.get("Record", {}).get("Section", [])
        if not sections:
            return None

        # Navigate: Safety and Hazards → Hazards Identification → GHS Classification
        ghs_section = None
        for s in sections:
            for sub in s.get("Section", []):
                for subsub in sub.get("Section", []):
                    if subsub.get("TOCHeading") == "GHS Classification":
                        ghs_section = subsub
                        break

        if not ghs_section:
            return None

        infos = ghs_section.get("Information", [])
        if not infos:
            return None

        # Parse the first GHS classification entry (consensus)
        result = {
            "signal_word": None,
            "pictograms": [],
            "h_codes": [],
            "h_statements": [],
            "p_codes_str": None,
        }

        # Track which reference we're parsing (use first ref_num as consensus)
        first_ref = infos[0].get("ReferenceNumber")

        for info in infos:
            if info.get("ReferenceNumber") != first_ref:
                break  # Only parse first classification source

            name = info.get("Name", "")
            strings = info.get("Value", {}).get("StringWithMarkup", [])

            if name == "Signal" and strings:
                result["signal_word"] = strings[0].get("String", "").strip()

            elif name == "Pictogram(s)" and strings:
                for markup in strings[0].get("Markup", []):
                    extra = markup.get("Extra", "")
                    if extra:
                        result["pictograms"].append(extra)

            elif name == "GHS Hazard Statements" and strings:
                for s in strings:
                    stmt = s.get("String", "")
                    # Extract H-code from statement like "H302: Harmful if swallowed ..."
                    match = re.match(r"(H\d+i?)", stmt)
                    if match:
                        result["h_codes"].append(match.group(1))
                    result["h_statements"].append(stmt)

            elif name == "Precautionary Statement Codes" and strings:
                result["p_codes_str"] = strings[0].get("String", "")

        if not result["h_codes"] and not result["signal_word"]:
            return None

        return result

    except Exception as e:
        logger.error(f"PUG View error for CID {cid}: {e}")
        return None


def _build_hazard_record(casrn, canonical_name, cid, ghs_data, data_source, match_confidence):
    """Convert raw GHS data into a hazard record dict."""
    h_codes = ghs_data["h_codes"]
    h_stmts = ghs_data["h_statements"]

    # Derive hazard classes from H-codes
    classes = set()
    for h in h_codes:
        if h in H_CODE_TO_CLASS:
            classes.add(H_CODE_TO_CLASS[h])

    # Derive specific hazard fields
    acute_oral = None
    acute_dermal = None
    acute_inh = None
    skin_irrit = None
    eye_irrit = None
    reproductive = False
    carcinogenicity = None

    for h in h_codes:
        if h in ACUTE_ORAL_H:
            acute_oral = ACUTE_ORAL_H[h]
        if h in ACUTE_DERM_H:
            acute_dermal = ACUTE_DERM_H[h]
        if h in ACUTE_INH_H:
            acute_inh = ACUTE_INH_H[h]
        if h in ("H315", "H316"):
            skin_irrit = "Category 2"
        if h == "H314":
            skin_irrit = "Category 1A"
        if h == "H319":
            eye_irrit = "Category 2A"
        if h == "H318":
            eye_irrit = "Category 1"
        if h in REPR_H_CODES:
            reproductive = True
        if h in CARC_H_CODES:
            if h in ("H350", "H350i"):
                carcinogenicity = "Confirmed"
            elif h == "H351":
                carcinogenicity = "Suspected"

    # Build hazard summary from first few H-statements
    summary = "; ".join(h_stmts[:5]) if h_stmts else None

    # Parse P-codes
    p_codes_raw = ghs_data.get("p_codes_str", "") or ""
    p_codes = [p.strip() for p in re.findall(r"P\d+(?:\+P\d+)*", p_codes_raw)]

    return {
        "casrn": casrn,
        "canonical_name": canonical_name,
        "ghs_hazard_class": "|".join(sorted(classes)) if classes else None,
        "ghs_signal_word": ghs_data["signal_word"],
        "h_codes": "|".join(h_codes) if h_codes else None,
        "p_codes": "|".join(p_codes) if p_codes else None,
        "pictograms": "|".join(ghs_data["pictograms"]) if ghs_data["pictograms"] else None,
        "hazard_summary": summary,
        "acute_tox_oral": acute_oral,
        "acute_tox_dermal": acute_dermal,
        "acute_tox_inhalation": acute_inh,
        "skin_irritation": skin_irrit,
        "eye_irritation": eye_irrit,
        "reproductive_hazard": reproductive,
        "carcinogenicity": carcinogenicity,
        "data_source": data_source,
        "match_confidence": match_confidence,
        "hazard_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None,
    }


def _empty_record(casrn, canonical_name, data_source, match_confidence):
    """Create a placeholder record with no hazard data."""
    return {
        "casrn": casrn,
        "canonical_name": canonical_name,
        "ghs_hazard_class": None,
        "ghs_signal_word": None,
        "h_codes": None,
        "p_codes": None,
        "pictograms": None,
        "hazard_summary": None,
        "acute_tox_oral": None,
        "acute_tox_dermal": None,
        "acute_tox_inhalation": None,
        "skin_irritation": None,
        "eye_irritation": None,
        "reproductive_hazard": False,
        "carcinogenicity": None,
        "data_source": data_source,
        "match_confidence": match_confidence,
        "hazard_url": None,
    }


def load_chemicals() -> tuple:
    """Load ref_chemicals and ingredient_identity_matched, return (matched, unmatched)."""
    ref_path = WAREHOUSE_DIR / "ref_chemicals.parquet"
    id_path = WAREHOUSE_DIR / "ingredient_identity_matched.parquet"

    ref = pd.read_parquet(ref_path)
    id_df = pd.read_parquet(id_path)
    logger.info(f"Loaded ref_chemicals ({len(ref)} rows), identity_matched ({len(id_df)} rows)")

    # Matched: chemicals with CASRNs and canonical names (from ref_chemicals with CIDs)
    matched = ref[ref["cid"].notna()].copy()
    matched["cid"] = matched["cid"].astype(int)
    logger.info(f"Phase 1 candidates (with CID): {len(matched)}")

    # Unmatched: chemicals without CIDs, plus ingredients with no canonical_name
    unmatched_ref = ref[ref["cid"].isna()].copy()
    unmatched_ingredients = (
        id_df[id_df["canonical_name"].isna()]
        .drop_duplicates(subset=["ingredient_raw"])[["ingredient_raw", "casrn"]]
        .reset_index(drop=True)
    )
    logger.info(f"Phase 2 candidates: {len(unmatched_ref)} ref w/o CID + {len(unmatched_ingredients)} unmatched ingredients")

    return matched, unmatched_ref, unmatched_ingredients


def build_hazard_reference(matched, unmatched_ref, unmatched_ingredients) -> pd.DataFrame:
    """Build hazard reference table using PubChem PUG View API."""
    records = []

    # Phase 1: Direct PUG View lookup for chemicals with known CIDs
    logger.info(f"=== Phase 1: PUG View lookup for {len(matched)} chemicals with CIDs ===")
    for idx, row in matched.iterrows():
        casrn = row["casrn"]
        name = row.get("canonical_name") or casrn
        cid = int(row["cid"])
        logger.info(f"  [{idx+1}/{len(matched)}] CID {cid} | {casrn} | {name}")

        ghs = fetch_ghs_from_pugview(cid)
        if ghs:
            records.append(_build_hazard_record(casrn, name, cid, ghs, "pubchem_pugview", 1.0))
            logger.info(f"    ✓ {ghs['signal_word']} | {len(ghs['h_codes'])} H-codes")
        else:
            records.append(_empty_record(casrn, name, "pubchem_no_ghs", 0.9))
            logger.info(f"    ✗ No GHS data")
        time.sleep(0.25)

    # Phase 2a: Chemicals in ref_chemicals without CIDs — try to resolve CID by CASRN
    logger.info(f"=== Phase 2a: Resolve CIDs for {len(unmatched_ref)} ref chemicals w/o CID ===")
    for idx, row in unmatched_ref.iterrows():
        casrn = row["casrn"]
        name = row.get("canonical_name") or casrn
        logger.info(f"  [{idx+1}/{len(unmatched_ref)}] {casrn} | {name}")

        cid = _resolve_cid_by_casrn(casrn) if pd.notna(casrn) else None
        if cid:
            ghs = fetch_ghs_from_pugview(cid)
            if ghs:
                records.append(_build_hazard_record(casrn, name, cid, ghs, "pubchem_pugview_resolved", 0.9))
                logger.info(f"    ✓ Resolved CID {cid} | {ghs['signal_word']}")
            else:
                records.append(_empty_record(casrn, name, "pubchem_no_ghs", 0.8))
                logger.info(f"    ✗ CID {cid} found but no GHS data")
        else:
            records.append(_empty_record(casrn, name, "no_cid_resolved", 0.5))
            logger.info(f"    ✗ Could not resolve CID")
        time.sleep(0.25)

    # Phase 2b: Unmatched ingredients — try name lookup
    logger.info(f"=== Phase 2b: Name-based lookup for {len(unmatched_ingredients)} unmatched ingredients ===")
    for idx, row in unmatched_ingredients.iterrows():
        ingredient = row["ingredient_raw"]
        casrn = row.get("casrn")
        logger.info(f"  [{idx+1}/{len(unmatched_ingredients)}] {ingredient}")

        # Try by CASRN first, then by name
        cid = None
        if pd.notna(casrn):
            cid = _resolve_cid_by_casrn(casrn)
        if not cid:
            # Clean ingredient name for lookup
            clean_name = re.sub(r"\s*\(.*?\)\s*$", "", ingredient).strip()
            cid = _resolve_cid_by_name(clean_name)

        if cid:
            ghs = fetch_ghs_from_pugview(cid)
            if ghs:
                records.append(_build_hazard_record(casrn, ingredient, cid, ghs, "pubchem_fallback_name", 0.7))
                logger.info(f"    ✓ CID {cid} | {ghs['signal_word']}")
            else:
                records.append(_empty_record(casrn, ingredient, "pubchem_no_ghs", 0.6))
                logger.info(f"    ✗ CID {cid} found but no GHS data")
        else:
            records.append(_empty_record(casrn, ingredient, "fallback_no_match", 0.0))
            logger.info(f"    ✗ No match")
        time.sleep(0.25)

    df = pd.DataFrame(records)
    logger.info(f"Built hazard reference: {len(df)} chemicals, {df['ghs_hazard_class'].notna().sum()} with GHS data")
    return df


def calculate_coverage_stats(hazard_df, matched_count, unmatched_count) -> Dict:
    """Calculate quality metrics."""
    with_casrn = hazard_df[hazard_df["casrn"].notna()]
    matched_with_hazard = len(with_casrn[with_casrn["ghs_hazard_class"].notna()])

    no_casrn = hazard_df[hazard_df["casrn"].isna()]
    unmatched_with_hazard = len(no_casrn[no_casrn["ghs_hazard_class"].notna()])

    return {
        "total_chemicals": len(hazard_df),
        "with_casrn": len(with_casrn),
        "with_hazard_data": int(hazard_df["ghs_hazard_class"].notna().sum()),
        "matched_with_hazard": matched_with_hazard,
        "matched_count": matched_count,
        "unmatched_with_hazard": unmatched_with_hazard,
        "unmatched_count": unmatched_count,
        "matched_coverage": (matched_with_hazard / matched_count * 100) if matched_count > 0 else 0,
        "unmatched_coverage": (unmatched_with_hazard / unmatched_count * 100) if unmatched_count > 0 else 0,
    }


def generate_report(hazard_df: pd.DataFrame, stats: Dict):
    """Generate M1.1 quality report."""
    report_path = REPORTS_DIR / "M1.1_hazard_sourcing_report.md"
    today = date.today().isoformat()

    with open(report_path, "w") as f:
        f.write("# Hair Glue Project — M1.1 Hazard Data Sourcing Report\n\n")
        f.write(f"**Generated:** {today}\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total chemicals processed:** {stats['total_chemicals']}\n")
        f.write(f"- **With CASRN:** {stats['with_casrn']}\n")
        f.write(f"- **With GHS hazard data:** {stats['with_hazard_data']}\n")
        overall_pct = stats["with_hazard_data"] / stats["total_chemicals"] * 100 if stats["total_chemicals"] else 0
        f.write(f"- **Overall hazard coverage:** {overall_pct:.1f}%\n\n")

        f.write("## Coverage by Chemical Type\n\n")
        f.write("### M0-Matched Chemicals (CAS-first, strong identity confidence)\n")
        f.write(f"- Count: {stats['matched_count']}\n")
        f.write(f"- With hazard data: {stats['matched_with_hazard']}\n")
        mc = stats["matched_coverage"]
        icon = "✅" if mc >= 80 else "⚠️"
        f.write(f"- **Coverage: {mc:.1f}%** {icon} Target: ≥80%\n\n")

        f.write("### Unmatched Chemicals (Fallback fuzzy matching, lower confidence)\n")
        f.write(f"- Count: {stats['unmatched_count']}\n")
        f.write(f"- With hazard data: {stats['unmatched_with_hazard']}\n")
        if stats["unmatched_count"] > 0:
            uc = stats["unmatched_coverage"]
            icon = "✅" if uc >= 50 else "⚠️"
            f.write(f"- **Coverage: {uc:.1f}%** {icon} Target: ≥50%\n\n")
        else:
            f.write("- **Coverage: N/A** (no unmatched chemicals)\n\n")

        f.write("## Data Source Distribution\n\n")
        for source, count in hazard_df["data_source"].value_counts().items():
            pct = count / len(hazard_df) * 100
            f.write(f"- **{source}:** {count} ({pct:.1f}%)\n")
        f.write("\n")

        f.write("## Hazard Class Distribution\n\n")
        f.write("| GHS Hazard Class | Count | % of Chemicals |\n")
        f.write("|------------------|-------|----------------|\n")
        hazard_classes = {}
        for classes in hazard_df["ghs_hazard_class"].dropna():
            for cls in str(classes).split("|"):
                cls = cls.strip()
                if cls:
                    hazard_classes[cls] = hazard_classes.get(cls, 0) + 1
        if hazard_classes:
            for cls in sorted(hazard_classes, key=hazard_classes.get, reverse=True):
                cnt = hazard_classes[cls]
                pct = cnt / len(hazard_df) * 100
                f.write(f"| {cls} | {cnt} | {pct:.1f}% |\n")
        else:
            f.write("| (No hazard data found) | — | — |\n")
        f.write("\n")

        f.write("## All Chemicals — Hazard Summary\n\n")
        f.write("| Chemical | CASRN | Signal Word | H-codes | GHS Classes | Source | Confidence |\n")
        f.write("|----------|-------|-------------|---------|-------------|--------|------------|\n")
        for _, row in hazard_df.iterrows():
            name = str(row["canonical_name"] or "N/A")[:40]
            casrn = row["casrn"] or "—"
            signal = row["ghs_signal_word"] or "—"
            hcodes = str(row["h_codes"] or "—")[:30]
            classes = str(row["ghs_hazard_class"] or "—")[:30]
            source = row["data_source"]
            conf = f"{row['match_confidence']:.1f}"
            f.write(f"| {name} | {casrn} | {signal} | {hcodes} | {classes} | {source} | {conf} |\n")
        f.write("\n")

        # Special hazards
        repro_count = int(hazard_df["reproductive_hazard"].sum())
        carc_count = int(hazard_df["carcinogenicity"].notna().sum())
        f.write("## Special Hazard Flags\n\n")
        f.write(f"- **Reproductive/developmental hazard:** {repro_count} chemicals\n")
        f.write(f"- **Carcinogenicity (suspected or confirmed):** {carc_count} chemicals\n\n")

        f.write("## Recommendations\n\n")
        if stats["matched_coverage"] >= 80:
            f.write("✅ **Excellent coverage.** Proceed to M1.2 hazard classification and risk scoring.\n\n")
        elif stats["matched_coverage"] >= 50:
            f.write("⚠️ **Moderate coverage.** Consider supplementary lookups (ECHA) for missing chemicals.\n\n")
        else:
            f.write("❌ **Low coverage.** Review API integration and consider manual data entry.\n\n")

        f.write("## Data Source Notes\n\n")
        f.write("- **pubchem_pugview**: Direct GHS lookup via PubChem PUG View API (highest confidence)\n")
        f.write("- **pubchem_pugview_resolved**: CID resolved by CASRN, then PUG View lookup\n")
        f.write("- **pubchem_fallback_name**: CID resolved by ingredient name (lower confidence)\n")
        f.write("- **pubchem_no_ghs**: CID found but no GHS classification data in PubChem\n")
        f.write("- **no_cid_resolved**: Could not resolve PubChem CID\n")
        f.write("- **fallback_no_match**: No match found by any method\n")

    logger.info(f"Report generated: {report_path}")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("M1.1 Hazard Data Sourcing — PubChem PUG View API")
    logger.info("=" * 80)

    WAREHOUSE_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    try:
        matched, unmatched_ref, unmatched_ingredients = load_chemicals()
    except FileNotFoundError as e:
        logger.error(f"FATAL: {e}")
        return

    hazard_df = build_hazard_reference(matched, unmatched_ref, unmatched_ingredients)

    output_path = WAREHOUSE_DIR / "ref_chemicals_hazard.parquet"
    hazard_df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    total_matched = len(matched) + len(unmatched_ref)
    total_unmatched = len(unmatched_ingredients)
    stats = calculate_coverage_stats(hazard_df, total_matched, total_unmatched)
    logger.info(f"Matched coverage: {stats['matched_coverage']:.1f}% (target: ≥80%)")
    logger.info(f"Unmatched coverage: {stats['unmatched_coverage']:.1f}% (target: ≥50%)")

    generate_report(hazard_df, stats)

    logger.info("=" * 80)
    logger.info("M1.1 COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
