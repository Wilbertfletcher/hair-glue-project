#!/usr/bin/env python3
"""
Hair Glue Project — M3.5c GC-MS suspect list, version 1

Turns the 2,050-chemical NTA personal-care suspect list (M3.5) into the list
the Aim 1 GC-MS work at UL Solutions screens against. Why pre-register: a
suspect list fixed before any sample runs answers the "fishing expedition"
objection to non-targeted work, and gives a principled route to level-B
identifications.

Tiers:
  1  targeted panel — every EU-declarable fragrance allergen (all 26, whether
     or not NTA has seen them), phthalates, the declared hair-glue chemicals
     NTA has detected by GC in any product, and GC-detected chemicals measured
     in an adhesive product
  2  suspect screen — GC-detected in personal-care products by >= 2 studies
  3  suspect screen — GC-detected by a single study

Retention index and NIST library availability are left blank: both need the
NIST library, which this pipeline does not have. They are filled at UL
Solutions or from a licensed NIST copy before the list is locked.

The list is written as a DRAFT. Locking it means recording who approved it
and when in the manifest, after which it must not change; a revision is a
new version (v2), never an edit to v1.

Produces:
  warehouse/gcms_suspect_list_v1.csv
  warehouse/gcms_suspect_list_v1.manifest.json

Run:
    python warehouse/build_gcms_suspect_list.py
"""

import hashlib
import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline.extract.nta_curation import DATASET_VERSION
from warehouse.source_nta_data import EU_FRAGRANCE_ALLERGENS_26

WAREHOUSE = Path("warehouse")
SUSPECTS_PATH = WAREHOUSE / "nta_personal_care_suspect_list.parquet"
CROSSREF_PATH = WAREHOUSE / "ref_chemicals_nta.parquet"
OUT_CSV = WAREHOUSE / "gcms_suspect_list_v1.csv"
OUT_MANIFEST = WAREHOUSE / "gcms_suspect_list_v1.manifest.json"

COLUMNS = [
    "tier", "reason", "chemical_name", "casrn", "dtxsid", "nta_study_count",
    "detected_by_gc", "detected_by_lc", "eu_fragrance_allergen", "is_phthalate",
    "declared_in_hair_glue", "in_adhesive_product", "tox_evidence_gap",
    "retention_index", "nist_library",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_gcms_suspect_list(suspects: pd.DataFrame, crossref: pd.DataFrame) -> pd.DataFrame:
    """Tier the NTA suspect list for GC-MS. One row per chemical."""
    s = suspects.copy()
    declared_gc = crossref[
        crossref["nta_detected"]
        & crossref["nta_chromatography"].str.contains("GC", na=False)
    ]
    s["declared_in_hair_glue"] = s["mapped_id"].isin(set(declared_gc["dtxsid"]))

    reasons = []
    for _, r in s.iterrows():
        why = []
        if r["eu_fragrance_allergen"]:
            why.append("EU fragrance allergen")
        if r["is_phthalate"]:
            why.append("phthalate")
        if r["declared_in_hair_glue"]:
            why.append("declared in hair glue (CSCP)")
        # LC-only adhesive detections (the PFAS acids, mostly) can't be screened
        # on this instrument, so they don't earn a place on the GC panel.
        if r["in_adhesive_product"] and r["detected_by_gc"]:
            why.append("measured in an adhesive product")
        reasons.append("; ".join(why))
    s["reason"] = reasons

    tier1 = s["reason"] != ""
    gc = s["detected_by_gc"]
    s["tier"] = 0
    s.loc[tier1, "tier"] = 1
    s.loc[~tier1 & gc & (s["study_count"] >= 2), "tier"] = 2
    s.loc[~tier1 & gc & (s["study_count"] == 1), "tier"] = 3
    s.loc[s["tier"] == 2, "reason"] = "GC-detected in personal care, >= 2 studies"
    s.loc[s["tier"] == 3, "reason"] = "GC-detected in personal care, 1 study"
    # LC-only chemicals outside tier 1 are out of scope for a GC-MS screen.
    s = s[s["tier"] > 0]

    s = s.rename(columns={"mapped_id": "dtxsid", "study_count": "nta_study_count"})
    s["retention_index"] = pd.NA
    s["nist_library"] = pd.NA
    out = s[COLUMNS]

    # Declared hair-glue chemicals NTA has detected by GC in non-personal-care
    # products (styrene, NMP) are not in the personal-care suspect list at all.
    xref = declared_gc.set_index("dtxsid")
    out = out.copy()
    known = out["dtxsid"].isin(xref.index)
    out.loc[known, "casrn"] = out.loc[known, "casrn"].fillna(
        out.loc[known, "dtxsid"].map(xref["casrn"]))
    extra = [
        {
            "tier": 1, "reason": "declared in hair glue (CSCP); GC-detected outside personal care",
            "chemical_name": r["chemical_name"], "casrn": r["casrn"], "dtxsid": dtxsid,
            "nta_study_count": int(r["nta_study_count"]), "detected_by_gc": True,
            "detected_by_lc": "LC" in str(r["nta_chromatography"]),
            "eu_fragrance_allergen": False, "is_phthalate": False,
            "declared_in_hair_glue": True, "in_adhesive_product": False,
            "tox_evidence_gap": not (bool(r["nta_toxcast_yn"]) or bool(r["nta_toxvaldb_yn"])),
            "retention_index": pd.NA, "nist_library": pd.NA,
        }
        for dtxsid, r in xref.iterrows() if dtxsid not in set(out["dtxsid"])
    ]
    if extra:
        out = pd.concat([out, pd.DataFrame(extra, columns=COLUMNS)], ignore_index=True)

    # Allergens NTA has never reported still belong on the targeted panel: the
    # question is whether an identical product is labelled more fully in the EU.
    seen = set(out["casrn"].dropna())
    missing = [
        {
            "tier": 1, "reason": "EU fragrance allergen (not yet reported by NTA)",
            "chemical_name": name, "casrn": cas, "dtxsid": pd.NA, "nta_study_count": 0,
            "detected_by_gc": False, "detected_by_lc": False,
            "eu_fragrance_allergen": True, "is_phthalate": False,
            "declared_in_hair_glue": False, "in_adhesive_product": False,
            "tox_evidence_gap": pd.NA, "retention_index": pd.NA, "nist_library": pd.NA,
        }
        for cas, name in EU_FRAGRANCE_ALLERGENS_26.items() if cas not in seen
    ]
    if missing:
        out = pd.concat([out, pd.DataFrame(missing, columns=COLUMNS)], ignore_index=True)

    return out.sort_values(
        ["tier", "nta_study_count", "chemical_name"], ascending=[True, False, True]
    ).reset_index(drop=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(lst: pd.DataFrame) -> dict:
    manifest = {
        "list": OUT_CSV.name,
        "version": 1,
        "status": "draft",
        "built_on": date.today().isoformat(),
        "locked_on": None,
        "approved_by": None,
        "source_dataset": f"UL Chemical Insights curated NTA, release {DATASET_VERSION}",
        "inputs": {
            str(SUSPECTS_PATH): _sha256(SUSPECTS_PATH),
            str(CROSSREF_PATH): _sha256(CROSSREF_PATH),
        },
        "output_sha256": _sha256(OUT_CSV),
        "counts": {f"tier_{t}": int((lst["tier"] == t).sum()) for t in (1, 2, 3)},
        "open_before_lock": [
            "Fill retention_index and nist_library (NIST library at UL Solutions)",
            "Add the 54 further allergens made individually declarable by "
            "Regulation (EU) 2023/1545 (80 in total) to tier 1",
            "Confirm the tier 1 panel against the GC-MS method's LOQ target (<= 0.001%)",
            "Record approver and date here, then treat v1 as frozen",
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    suspects = pd.read_parquet(SUSPECTS_PATH)
    crossref = pd.read_parquet(CROSSREF_PATH)
    lst = build_gcms_suspect_list(suspects, crossref)
    lst.to_csv(OUT_CSV, index=False)
    manifest = write_manifest(lst)
    logger.info("GC-MS suspect list v1 (draft): %s", manifest["counts"])


if __name__ == "__main__":
    main()
