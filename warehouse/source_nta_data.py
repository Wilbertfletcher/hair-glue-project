#!/usr/bin/env python3
"""
Hair Glue Project — M3.5 Non-Targeted Analysis (NTA) Cross-Reference

Integrates the UL Research Institutes / Chemical Insights curated dataset of
chemicals reported in consumer products by non-targeted analysis
(Boatman, Ferland & Whitehead, 2026; release 2026-05-15).

Why: CSCP data only tells us what manufacturers *declared*. NTA studies
tell us what was *measured*. Cross-referencing the two answers
"has anyone ever detected our hair-glue chemicals in a real product?" and
gives us a measured-chemical suspect list for the GC-MS work in the
Dangerous Beauty proposal (Aim 1).

Produces:
  warehouse/ref_nta_consumer_products.parquet   — full curated NTA table (typed)
  warehouse/ref_chemicals_nta.parquet           — one row per hair-glue chemical
  warehouse/nta_personal_care_suspect_list.parquet — chemicals measured in
                                                  personal-care / adhesive products
  reports/M3.5_nta_crossref_report.md

Run:
    python warehouse/source_nta_data.py
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.extract.nta_curation import (
    DATASET_VERSION,
    DEFAULT_PATH,
    FLAG_COLUMNS,
    load_nta_results,
)

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "M3.5_nta_data.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE = Path("warehouse")
REPORTS = Path("reports")
REPORTS.mkdir(parents=True, exist_ok=True)

DATA_SOURCE = f"ul_chemical_insights_nta_{DATASET_VERSION}"
CITATION = (
    "Boatman, A. K.; Ferland, T. M.; Whitehead, H. D. Curated Chemicals "
    "Reported in Consumer Products Using Non-Targeted Analyses (NTA) "
    "[Data set]. UL Research Institutes, Chemical Insights, 2026. "
    "Release 2026-05-15."
)

# Why a hair-glue chemical may be absent from NTA results. Non-detection in
# the literature is NOT evidence of absence from products: LC/GC-HRMS
# cannot see inorganic solids and misses very small or very polar molecules.
NTA_BLIND_SPOTS = {
    "13463-67-7": "Inorganic solid (TiO2) — not amenable to LC/GC-HRMS; needs elemental analysis (ICP-MS/XRF)",
    "1333-86-4": "Elemental carbon particulate — not amenable to LC/GC-HRMS",
    "12001-26-2": "Inorganic silicate mineral — not amenable to LC/GC-HRMS",
    "14807-96-6": "Inorganic silicate mineral — not amenable to LC/GC-HRMS",
    "14808-60-7": "Inorganic crystalline silica — not amenable to LC/GC-HRMS",
    "50-00-0": "Very small, volatile aldehyde (m/z 30) — requires derivatisation (e.g., DNPH-HPLC), missed by standard NTA",
    "111-42-2": "Small, highly polar amine — poorly retained in standard LC/GC methods",
    "68603-42-9": "UVCB mixture (coco fatty-acid amides) — no single structure to match",
    "79-81-2": "Large, labile ester — degrades in GC; rarely reported",
}

TOP_N_EXAMPLES = 5

# The 26 fragrance allergens requiring label declaration in the EU
# (Directive 2003/15/EC; Regulation (EC) No 1223/2009, Annex III) but not in
# the U.S. The proposal's targeted GC-MS pass prioritises these.
EU_FRAGRANCE_ALLERGENS_26 = {
    "122-40-7": "Amyl cinnamal", "101-85-9": "Amylcinnamyl alcohol",
    "105-13-5": "Anise alcohol", "100-51-6": "Benzyl alcohol",
    "120-51-4": "Benzyl benzoate", "103-41-3": "Benzyl cinnamate",
    "118-58-1": "Benzyl salicylate", "104-55-2": "Cinnamal",
    "104-54-1": "Cinnamyl alcohol", "5392-40-5": "Citral",
    "106-22-9": "Citronellol", "91-64-5": "Coumarin", "97-53-0": "Eugenol",
    "4602-84-0": "Farnesol", "106-24-1": "Geraniol",
    "101-86-0": "Hexyl cinnamal", "107-75-5": "Hydroxycitronellal",
    "31906-04-4": "Hydroxyisohexyl 3-cyclohexene carboxaldehyde",
    "97-54-1": "Isoeugenol", "80-54-6": "Butylphenyl methylpropional",
    "5989-27-5": "d-Limonene", "78-70-6": "Linalool",
    "111-12-6": "Methyl 2-octynoate", "127-51-5": "alpha-Isomethyl ionone",
    "90028-68-5": "Evernia prunastri (oakmoss) extract",
    "90028-67-4": "Evernia furfuracea (treemoss) extract",
}


def _join_unique(values, limit=TOP_N_EXAMPLES) -> str:
    seen = []
    for v in values:
        for part in str(v).split(";"):
            part = part.strip()
            if part and part.lower() != "nan" and part not in seen:
                seen.append(part)
    return " | ".join(seen[:limit])


def load_project_chemicals() -> pd.DataFrame:
    """Hair-glue chemicals with DTXSID (and CID where available)."""
    reg = pd.read_parquet(WAREHOUSE / "ref_chemicals_regulatory.parquet")
    cols = ["casrn", "canonical_name", "dtxsid", "pubchem_cid"]
    chems = reg[cols].copy()
    comptox_path = WAREHOUSE / "ref_chemicals_comptox.parquet"
    if comptox_path.exists():
        ctx = pd.read_parquet(comptox_path)[["casrn", "preferred_name"]]
        chems = chems.merge(ctx, on="casrn", how="left")
    else:
        chems["preferred_name"] = None
    chems["display_name"] = chems["preferred_name"].fillna(chems["canonical_name"])
    return chems


def build_chemical_crossref(nta: pd.DataFrame, chems: pd.DataFrame) -> pd.DataFrame:
    """One row per hair-glue chemical summarising NTA detections.

    Match on DTXSID first; fall back to PubChem CID for rows NTA mapped
    to a CID instead of a DTXSID.
    """
    cid_str = chems["pubchem_cid"].dropna().astype("int64").astype(str)
    cid_to_dtx = dict(zip(cid_str, chems.loc[cid_str.index, "dtxsid"]))
    nta = nta.copy()
    nta["match_dtxsid"] = nta["mapped_id"].where(
        nta["mapped_id_type"] == "DTXSID"
    )
    cid_rows = nta["mapped_id_type"] == "PubChemCID"
    nta.loc[cid_rows, "match_dtxsid"] = (
        nta.loc[cid_rows, "mapped_id"].astype(str).map(cid_to_dtx)
    )
    hits = nta[nta["match_dtxsid"].isin(chems["dtxsid"])]

    records = []
    for _, chem in chems.iterrows():
        h = hits[hits["match_dtxsid"] == chem["dtxsid"]]
        detected = len(h) > 0
        rec = {
            "dtxsid": chem["dtxsid"],
            "casrn": chem["casrn"],
            "chemical_name": chem["display_name"],
            "nta_detected": detected,
            "nta_study_count": int(h["reference_id"].nunique()),
            "nta_feature_count": int(len(h)),
            "nta_chromatography": _join_unique(sorted(h["pub_chromatography"].dropna().unique())),
            "nta_detected_in_personal_care": bool(h["is_personal_care"].any()),
            "nta_product_examples": _join_unique(h["reported_product"]),
            "nta_study_dois": _join_unique(h["pub_doi"].dropna(), limit=20),
            "nta_classyfire_superclass": _join_unique(h["classyfire_superclass"].dropna(), limit=1),
            "nta_blind_spot_note": None if detected else NTA_BLIND_SPOTS.get(
                chem["casrn"], "Not reported in the 81 curated NTA studies"
            ),
        }
        for flag in FLAG_COLUMNS:
            rec[f"nta_{flag}"] = bool(h[flag].any()) if detected else None
        rec["data_source"] = DATA_SOURCE
        rec["fetched_date"] = date.today().isoformat()
        records.append(rec)
    return pd.DataFrame(records)


def build_suspect_list(nta: pd.DataFrame, project_dtxsids: set) -> pd.DataFrame:
    """Unique mapped chemicals measured in personal-care or adhesive products.

    Intended as a suspect-screening list for GC-MS (proposal Aim 1) and as
    an evidence-gap list for Aim 2 (chemicals with no ToxCast/ToxValDB data).
    """
    sub = nta[(nta["is_personal_care"] | nta["is_adhesive_product"]) & nta["mapped_id"].notna()]
    agg = (
        sub.groupby("mapped_id")
        .agg(
            mapped_id_type=("mapped_id_type", "first"),
            chemical_name=("reported_name", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
            casrn=("reported_casrn", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
            classyfire_superclass=("classyfire_superclass", "first"),
            study_count=("reference_id", "nunique"),
            feature_count=("feature_id", "size"),
            detected_by_gc=("pub_chromatography", lambda s: s.str.contains("GC").any()),
            detected_by_lc=("pub_chromatography", lambda s: s.str.contains("LC").any()),
            in_adhesive_product=("is_adhesive_product", "any"),
            product_examples=("reported_product", _join_unique),
            study_dois=("pub_doi", lambda s: _join_unique(s.dropna(), limit=20)),
            **{flag: (flag, "any") for flag in FLAG_COLUMNS},
        )
        .reset_index()
    )
    agg["chemical_name"] = agg["chemical_name"].fillna(agg["casrn"]).fillna(agg["mapped_id"])
    agg["eu_fragrance_allergen"] = agg["casrn"].isin(EU_FRAGRANCE_ALLERGENS_26)
    agg["is_phthalate"] = agg["chemical_name"].str.contains("phthalate", case=False, na=False)
    agg["tox_evidence_gap"] = ~(agg["toxcast_yn"] | agg["toxvaldb_yn"])
    agg["in_hair_glue_warehouse"] = agg["mapped_id"].isin(project_dtxsids)
    agg["data_source"] = DATA_SOURCE
    return agg.sort_values(
        ["study_count", "feature_count"], ascending=False
    ).reset_index(drop=True)


def write_report(nta, crossref, suspects) -> Path:
    detected = crossref[crossref["nta_detected"]]
    missing = crossref[~crossref["nta_detected"]]
    pc = nta[nta["is_personal_care"]]
    n_gap = int(suspects["tox_evidence_gap"].sum())
    n_gc = int(suspects["detected_by_gc"].sum())
    allergens = suspects[suspects["eu_fragrance_allergen"]]
    phthalates = suspects[suspects["is_phthalate"]]

    lines = [
        "# M3.5 — Non-Targeted Analysis (NTA) Cross-Reference Report",
        "",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**Script:** `warehouse/source_nta_data.py`  ",
        f"**Source file:** `{DEFAULT_PATH.as_posix()}`  ",
        f"**Citation:** {CITATION}",
        "",
        "## Why this matters",
        "",
        "Everything upstream of this step (CSCP, PubChem, CompTox, ToxCast) describes",
        "chemicals that manufacturers **declared**. The NTA dataset describes chemicals that",
        "laboratories **measured** in real consumer products with high-resolution mass",
        "spectrometry. Linking the two lets the project separate *declared* from *detected*",
        "chemistry — the central idea of Aim 1 in the Dangerous Beauty proposal.",
        "",
        "## Dataset at a glance",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Reported chemical features | {len(nta):,} |",
        f"| Peer-reviewed NTA studies | {nta['reference_id'].nunique()} |",
        f"| Unique mapped chemicals (DTXSID or PubChem CID) | {nta['mapped_id'].nunique():,} |",
        f"| Unmapped features | {int(nta['mapped_id'].isna().sum()):,} |",
        f"| Features from personal-care products | {len(pc):,} ({pc['reference_id'].nunique()} studies) |",
        f"| Features from adhesive products | {int(nta['is_adhesive_product'].sum())} |",
        "",
        "## Hair-glue chemicals found in NTA studies",
        "",
        f"**{len(detected)} of {len(crossref)}** hair-glue chemicals with a DTXSID have been",
        "measured in at least one consumer product by NTA.",
        "",
        "| Chemical | CAS # | Studies | Personal care? | ToxCast | NHANES | Example products |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in detected.sort_values("nta_study_count", ascending=False).iterrows():
        lines.append(
            f"| {r['chemical_name']} | {r['casrn']} | {r['nta_study_count']} | "
            f"{'Yes' if r['nta_detected_in_personal_care'] else 'No'} | "
            f"{'Y' if r['nta_toxcast_yn'] else '—'} | {'Y' if r['nta_nhanes_yn'] else '—'} | "
            f"{r['nta_product_examples'][:90]} |"
        )
    lines += [
        "",
        "## Hair-glue chemicals NOT found — and why",
        "",
        "Non-detection is **not** evidence of absence. Most of these chemicals fall in known",
        "blind spots of LC/GC high-resolution mass spectrometry.",
        "",
        "| Chemical | CAS # | Likely reason |",
        "|---|---|---|",
    ]
    for _, r in missing.iterrows():
        lines.append(f"| {r['chemical_name']} | {r['casrn']} | {r['nta_blind_spot_note']} |")
    lines += [
        "",
        "## Personal-care & adhesive suspect list",
        "",
        f"`warehouse/nta_personal_care_suspect_list.parquet` holds **{len(suspects):,}** unique",
        "chemicals measured in personal-care or adhesive products.",
        "",
        f"- **{n_gc:,}** were detected by a GC method — directly relevant to the proposal's GC-MS work.",
        f"- **{n_gap:,}** ({n_gap / max(len(suspects), 1):.0%}) have **no** ToxCast or ToxValDB record — an",
        "  explicit toxicity evidence gap for Aim 2.",
        f"- **{len(allergens)}** of the 26 EU-declarable fragrance allergens and **{len(phthalates)}**",
        "  phthalates appear — both are priority analytes for the proposal's targeted GC-MS pass.",
        "",
        "### EU-declarable fragrance allergens measured in personal-care products",
        "",
        "| Allergen | CAS # | Studies | ToxCast |",
        "|---|---|---|---|",
        *[
            f"| {EU_FRAGRANCE_ALLERGENS_26[r['casrn']]} | {r['casrn']} | {r['study_count']} | "
            f"{'Y' if r['toxcast_yn'] else '—'} |"
            for _, r in allergens.iterrows()
        ],
        "",
        "### Most frequently reported (top 15)",
        "",
        "| Chemical | Studies | GC | ToxCast | ToxValDB | Superclass |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in suspects.head(15).iterrows():
        lines.append(
            f"| {r['chemical_name']} | {r['study_count']} | {'Y' if r['detected_by_gc'] else '—'} | "
            f"{'Y' if r['toxcast_yn'] else '—'} | {'Y' if r['toxvaldb_yn'] else '—'} | "
            f"{r['classyfire_superclass'] or '—'} |"
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- No study in the curated set analysed hair glue, lace adhesive, or lash adhesive",
        "  specifically. The adhesive rows are general consumer/household adhesives.",
        "- Product tagging uses conservative keyword rules (`pipeline/extract/nta_curation.py`);",
        "  CPDat category codes are retained for later mapping.",
        "- The NTA literature is weighted toward GC (≈77% of features), so polar and",
        "  non-volatile chemicals are under-represented.",
        "- Reported identities carry the confidence of the original study; many are",
        "  library-match (tentative) identifications.",
        "",
    ]
    out = REPORTS / "M3.5_nta_crossref_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    logger.info("Loading NTA workbook: %s", DEFAULT_PATH)
    nta = load_nta_results()
    logger.info("NTA rows: %d  studies: %d", len(nta), nta["reference_id"].nunique())

    nta_out = nta.assign(data_source=DATA_SOURCE)
    nta_out.to_parquet(WAREHOUSE / "ref_nta_consumer_products.parquet", index=False)

    chems = load_project_chemicals()
    crossref = build_chemical_crossref(nta, chems)
    crossref.to_parquet(WAREHOUSE / "ref_chemicals_nta.parquet", index=False)
    logger.info(
        "Hair-glue chemicals detected in NTA: %d / %d",
        int(crossref["nta_detected"].sum()), len(crossref),
    )

    suspects = build_suspect_list(nta, set(chems["dtxsid"].dropna()))
    suspects.to_parquet(WAREHOUSE / "nta_personal_care_suspect_list.parquet", index=False)
    logger.info("Personal-care/adhesive suspect list: %d chemicals", len(suspects))

    report = write_report(nta, crossref, suspects)
    logger.info("Report written: %s", report)


if __name__ == "__main__":
    main()
