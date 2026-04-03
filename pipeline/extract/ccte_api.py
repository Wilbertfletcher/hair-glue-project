"""
EPA CCTE API Client — powered by ctx-python (ctxpy)

Covers:
  - Chemical detail (structure, formula, mass) — CompTox
  - Bioactivity / toxicology study counts — ToxValDB
  - Functional use / product-data — ChemExpo exposure
  - Hazard data — ToxValDB

Auth: CTX_API_KEY in .env
  Free key: https://www.epa.gov/comptox-tools/
            computational-toxicology-and-exposure-apis-about

All functions cache results to data/raw/ccte_cache/.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import ctxpy as ctx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CTX_API_KEY = os.getenv("CTX_API_KEY", "")

CACHE_DIR = Path("data/raw/ccte_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Cache helpers ─────────────────────────────────────────────────────────

def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _load_cache(key: str) -> Optional[Any]:
    p = _cache_path(key)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def _save_cache(key: str, data: Any) -> None:
    with open(_cache_path(key), "w") as f:
        json.dump(data, f)


def _cache_key(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _make_chem() -> ctx.Chemical:
    if CTX_API_KEY:
        return ctx.Chemical(x_api_key=CTX_API_KEY)
    return ctx.Chemical()


def _make_expo() -> ctx.Exposure:
    if CTX_API_KEY:
        return ctx.Exposure(x_api_key=CTX_API_KEY)
    return ctx.Exposure()


def _make_hazard() -> ctx.Hazard:
    if CTX_API_KEY:
        return ctx.Hazard(x_api_key=CTX_API_KEY)
    return ctx.Hazard()


# ── M3.1a: Chemical Detail (CompTox) ──────────────────────────────────────

def get_chemical_detail(dtxsid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch CompTox chemical detail for a single DTXSID via ctxpy.

    Returns a flat dict with keys:
      dtxsid, preferred_name, iupac_name, smiles, inchi_key,
      inchi_string, molecular_formula, molecular_mass
    or None if not found.
    """
    key = _cache_key("detail", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached or None

    try:
        chem = _make_chem()
        df = chem.details(by="dtxsid", query=dtxsid)
        if df is None or (hasattr(df, "__len__") and len(df) == 0):
            _save_cache(key, {})
            return None

        row = df.iloc[0] if hasattr(df, "iloc") else df
        result = {
            "dtxsid": dtxsid,
            "preferred_name": _get(row, "preferredName"),
            "iupac_name": _get(row, "iupacName"),
            "smiles": _get(row, "smiles"),
            "inchi_key": _get(row, "inchiKey"),
            "inchi_string": _get(row, "inchiString"),
            "molecular_formula": _get(row, "molecularFormula"),
            "molecular_mass": _get(row, "monoisotopicMass"),
        }
        _save_cache(key, result)
        logger.info(
            "CompTox detail: %s — %s",
            dtxsid,
            result.get("preferred_name", "?"),
        )
        return result
    except Exception as exc:
        logger.error("CompTox detail failed for %s: %s", dtxsid, exc)
        _save_cache(key, {})
        return None


def get_chemical_details_batch(
    dtxsid_list: List[str],
) -> List[Dict[str, Any]]:
    """Fetch chemical detail for a list of DTXSIDs, falling back to individual."""
    key = _cache_key("detail_batch", *sorted(dtxsid_list))
    cached = _load_cache(key)
    if cached is not None:
        return cached

    try:
        chem = _make_chem()
        df = chem.details(by="batch", query=dtxsid_list)
        if df is None or len(df) == 0:
            return []

        results = []
        for _, row in df.iterrows():
            sid = _get(row, "dtxsid") or _get(row, "id") or ""
            results.append({
                "dtxsid": sid,
                "preferred_name": _get(row, "preferredName"),
                "iupac_name": _get(row, "iupacName"),
                "smiles": _get(row, "smiles"),
                "inchi_key": _get(row, "inchiKey"),
                "inchi_string": _get(row, "inchiString"),
                "molecular_formula": _get(row, "molecularFormula"),
                "molecular_mass": _get(row, "monoisotopicMass"),
            })
        _save_cache(key, results)
        logger.info(
            "CompTox batch: %d/%d returned",
            len(results),
            len(dtxsid_list),
        )
        return results
    except Exception as exc:
        logger.warning(
            "Batch detail failed (%s), falling back to individual", exc
        )
        return [
            r for dtxsid in dtxsid_list
            if (r := get_chemical_detail(dtxsid))
        ]


# ── M3.1b: ToxValDB Bioactivity ───────────────────────────────────────────

def get_bioactivity(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch toxicological study data from ToxValDB for a single DTXSID.

    Counts how many study records exist and how many carry a hazard value,
    as a proxy for bioactivity / concern level.

    Returns a dict with:
      dtxsid, assays_tested, assays_active, activity_score,
      top_hit_categories (pipe-delimited string)
    """
    key = _cache_key("bioactivity", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "assays_tested": 0,
        "assays_active": 0,
        "activity_score": None,
        "top_hit_categories": None,
    }

    try:
        haz = _make_hazard()
        df = haz.search_toxvaldb(by="all", dtxsid=dtxsid)

        if df is not None and len(df) > 0:
            tested = len(df)

            active_cols = [
                "cancerCall",
                "cancerClassification",
                "toxvalNumeric",
                "criticalEffect",
            ]

            def _has_value(row):
                return any(
                    row[c] is not None
                    and str(row[c]).strip() not in ("", "<NA>", "nan")
                    for c in active_cols
                    if c in row.index
                )

            active_mask = df.apply(_has_value, axis=1)
            active = int(active_mask.sum())

            categories: List[str] = []
            for col in (
                "source", "studyType", "toxvalType", "studyDuration"
            ):
                if col in df.columns:
                    cats = (
                        df[col].dropna().astype(str).unique().tolist()
                    )
                    categories.extend(
                        c for c in cats
                        if c and c not in categories
                    )

            result["assays_tested"] = tested
            result["assays_active"] = active
            result["activity_score"] = (
                round(active / tested, 4) if tested > 0 else 0.0
            )
            result["top_hit_categories"] = (
                "|".join(categories[:10]) if categories else None
            )
            logger.info(
                "ToxValDB: %s — %d records, %d with hazard values",
                dtxsid, tested, active,
            )
        else:
            logger.warning("ToxValDB: %s — no data", dtxsid)
    except Exception as exc:
        logger.error("ToxValDB failed for %s: %s", dtxsid, exc)

    _save_cache(key, result)
    return result


def get_bioactivity_batch(
    dtxsid_list: List[str],
) -> List[Dict[str, Any]]:
    """Fetch ToxValDB bioactivity for a list of DTXSIDs."""
    return [get_bioactivity(dtxsid) for dtxsid in dtxsid_list]


# ── M3.1c: ChemExpo Exposure Data ─────────────────────────────────────────

def get_functional_use(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ChemExpo functional use data for a single DTXSID via ctxpy.

    Returns a dict with:
      dtxsid, functional_uses (pipe-delimited), use_count
    """
    key = _cache_key("funcuse", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "functional_uses": None,
        "use_count": 0,
    }

    try:
        expo = _make_expo()
        df = expo.search_cpdat(vocab_name="fc", dtxsid=dtxsid)
        if df is not None and len(df) > 0:
            uses: List[str] = []
            for col in (
                "functionalUse",
                "use",
                "reportedFunctionalUse",
                "harmonizedFunctionalUse",
            ):
                if col in df.columns:
                    uses = df[col].dropna().astype(str).unique().tolist()
                    break
            result["functional_uses"] = "|".join(uses) if uses else None
            result["use_count"] = len(df)
            logger.info(
                "ChemExpo functional use: %s — %d records",
                dtxsid, len(df),
            )
        else:
            logger.warning(
                "ChemExpo functional use: %s — no data", dtxsid
            )
    except Exception as exc:
        logger.error(
            "ChemExpo functional use failed for %s: %s", dtxsid, exc
        )

    _save_cache(key, result)
    return result


def get_product_data(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ChemExpo product-use category (PUC) data for a single DTXSID.

    Returns a dict with:
      dtxsid, product_categories (pipe-delimited), national_product_count
    """
    key = _cache_key("proddata", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "product_categories": None,
        "national_product_count": 0,
    }

    try:
        expo = _make_expo()
        df = expo.search_cpdat(vocab_name="puc", dtxsid=dtxsid)
        if df is not None and len(df) > 0:
            cats: List[str] = []
            for col in (
                "productCategory",
                "puc",
                "generalCategory",
                "productUseCategory",
            ):
                if col in df.columns:
                    cats = df[col].dropna().astype(str).unique().tolist()
                    break
            result["product_categories"] = (
                "|".join(cats) if cats else None
            )
            result["national_product_count"] = len(df)
            logger.info(
                "ChemExpo product data: %s — %d records",
                dtxsid, len(df),
            )
        else:
            logger.warning(
                "ChemExpo product data: %s — no data", dtxsid
            )
    except Exception as exc:
        logger.error(
            "ChemExpo product data failed for %s: %s", dtxsid, exc
        )

    _save_cache(key, result)
    return result


def get_chemexpo_batch(
    dtxsid_list: List[str],
) -> List[Dict[str, Any]]:
    """
    Fetch combined ChemExpo data (functional use + product data)
    for a list of DTXSIDs.
    """
    results = []
    for dtxsid in dtxsid_list:
        func = get_functional_use(dtxsid)
        prod = get_product_data(dtxsid)
        merged = {
            **func,
            **{k: v for k, v in prod.items() if k != "dtxsid"},
        }
        results.append(merged)
    return results


# ── M3.1d: EPA IRIS — Federal reference doses & cancer data ──────────────

def get_iris(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch EPA IRIS (Integrated Risk Information System) data for one DTXSID.

    IRIS is the federal standard for chemical risk — used by EPA, FDA, and
    OSHA to set safety limits. Only ~600 chemicals have IRIS assessments,
    so most will return empty.

    Returns a dict with:
      dtxsid, has_iris, rfd_chronic, rfc_chronic, tumor_sites,
      critical_effects, last_revised, iris_url
    """
    key = _cache_key("iris", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "has_iris": False,
        "rfd_chronic": None,
        "rfc_chronic": None,
        "tumor_sites": None,
        "critical_effects": None,
        "last_revised": None,
        "iris_url": None,
    }

    try:
        haz = _make_hazard()
        df = haz.search_iris(dtxsid=dtxsid)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            result["has_iris"] = True
            result["rfd_chronic"] = _na_str(_get(row, "rfdChronic"))
            result["rfc_chronic"] = _na_str(_get(row, "rfcChronic"))
            result["tumor_sites"] = _na_str(_get(row, "tumorSite"))
            result["critical_effects"] = _na_str(
                _get(row, "criticalEffectsSystems")
            )
            result["last_revised"] = _na_str(
                _get(row, "lastSignificantRevision")
            )
            result["iris_url"] = _na_str(_get(row, "irisUrl"))
            logger.info("IRIS: %s — data found", dtxsid)
        else:
            logger.info("IRIS: %s — no assessment", dtxsid)
    except Exception as exc:
        logger.error("IRIS failed for %s: %s", dtxsid, exc)

    _save_cache(key, result)
    return result


def get_iris_batch(dtxsid_list: List[str]) -> List[Dict[str, Any]]:
    """Fetch IRIS data for a list of DTXSIDs."""
    return [get_iris(dtxsid) for dtxsid in dtxsid_list]


# ── Bonus: Hazard / ToxValDB cancer search ────────────────────────────────

def get_hazard_summary(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ToxValDB cancer-call data for a single DTXSID via ctxpy.

    Returns a dict with:
      dtxsid, cancer_classification, tox_summary, record_count
    """
    key = _cache_key("hazard", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "cancer_classification": None,
        "tox_summary": None,
        "record_count": 0,
    }

    try:
        haz = _make_hazard()
        df = haz.search_toxvaldb(by="cancer", dtxsid=dtxsid)
        if df is not None and len(df) > 0:
            result["record_count"] = len(df)
            for col in (
                "cancerClassification",
                "cancer_classification",
                "cancerCall",
            ):
                if col in df.columns:
                    vals = df[col].dropna().astype(str).unique().tolist()
                    result["cancer_classification"] = (
                        "|".join(vals) if vals else None
                    )
                    break
            logger.info("Hazard: %s — %d records", dtxsid, len(df))
        else:
            logger.warning("Hazard: %s — no data", dtxsid)
    except Exception as exc:
        logger.error("Hazard search failed for %s: %s", dtxsid, exc)

    _save_cache(key, result)
    return result


# ── Internal helpers ──────────────────────────────────────────────────────

def _get(row, key: str):
    """Safe getter for both dict-like and Series rows."""
    try:
        return row[key] if key in row else None
    except Exception:
        return None


def _na_str(value) -> str | None:
    """Convert pandas NA / NAType to None so json.dump doesn't choke."""
    if value is None:
        return None
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value) if str(value) not in ("nan", "None", "<NA>") else None
