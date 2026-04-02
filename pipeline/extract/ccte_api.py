"""
EPA CCTE (Center for Computational Toxicology and Exposure) API Client

Covers:
  - Chemical detail (structure, formula, mass) — CompTox
  - Bioactivity data (ToxCast assay hits)
  - Functional use / product-data (ChemExpo exposure)

Base URL: https://api-ccte.epa.gov/
Auth:     x-api-key header (free key from api-ccte.epa.gov)

All functions cache results to data/raw/ccte_cache/ so repeated runs
do not re-hit the API.
"""

import os
import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv
from pipeline.utils.http import RateLimiter, retry_with_backoff

load_dotenv()

logger = logging.getLogger(__name__)

CCTE_BASE = "https://comptox.epa.gov/ctx-api"
CTX_API_KEY = os.getenv("CTX_API_KEY", "")

HEADERS = {
    "accept": "application/json",
    "User-Agent": "HairGlueProject/1.0 (thesis-research)",
}
if CTX_API_KEY:
    HEADERS["x-api-key"] = CTX_API_KEY

CACHE_DIR = Path("data/raw/ccte_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# CCTE recommends max 5 req/sec with a key; be conservative at 3/sec
_rate_limiter = RateLimiter(max_calls=3, period=1.0)


# ── Cache helpers ─────────────────────────────────────────────────────────────

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


# ── Core HTTP ─────────────────────────────────────────────────────────────────

@_rate_limiter
@retry_with_backoff
def _get(path: str, params: Optional[dict] = None) -> Optional[Any]:
    """GET from CCTE API. Returns parsed JSON or None on error."""
    url = f"{CCTE_BASE}{path}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None  # chemical not found — not an error
        logger.warning("CCTE GET %s → HTTP %d", path, resp.status_code)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("CCTE GET %s failed: %s", path, exc)
        return None


# ── M3.1a: Chemical Detail ────────────────────────────────────────────────────

def get_chemical_detail(dtxsid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch CompTox chemical detail for a single DTXSID.

    Returns a flat dict with keys:
      dtxsid, preferred_name, iupac_name, smiles, inchi_key,
      inchi_string, molecular_formula, molecular_mass
    or None if the DTXSID is not found.
    """
    key = _cache_key("detail", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached or None  # {} stored as cache-miss sentinel

    data = _get(f"/chemical/detail/search/by-dtxsid/{dtxsid}")
    if not data:
        _save_cache(key, {})  # sentinel — don't re-query
        return None

    result = {
        "dtxsid": dtxsid,
        "preferred_name": data.get("preferredName"),
        "iupac_name": data.get("iupacName"),
        "smiles": data.get("smiles"),
        "inchi_key": data.get("inchiKey"),
        "inchi_string": data.get("inchiString"),
        "molecular_formula": data.get("molecularFormula"),
        "molecular_mass": data.get("monoisotopicMass"),
    }
    _save_cache(key, result)
    return result


def get_chemical_details_batch(dtxsid_list: List[str]) -> List[Dict[str, Any]]:
    """Fetch chemical detail for a list of DTXSIDs. Returns list of dicts."""
    results = []
    for dtxsid in dtxsid_list:
        detail = get_chemical_detail(dtxsid)
        if detail:
            results.append(detail)
            logger.info("CompTox detail: %s — %s", dtxsid, detail.get("preferred_name", "?"))
        else:
            logger.warning("CompTox detail: %s — not found", dtxsid)
    return results


# ── M3.1b: ToxCast Bioactivity ────────────────────────────────────────────────

def get_bioactivity(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ToxCast bioactivity summary for a single DTXSID.

    Returns a dict with:
      dtxsid, assays_tested, assays_active, activity_score,
      top_hit_categories (pipe-delimited string)
    """
    key = _cache_key("bioactivity", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    data = _get(f"/bioactivity/data/search/by-dtxsid/{dtxsid}")

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "assays_tested": 0,
        "assays_active": 0,
        "activity_score": None,
        "top_hit_categories": None,
    }

    if data:
        # The CCTE bioactivity endpoint returns a list of assay records
        records = data if isinstance(data, list) else data.get("data", [])
        tested = len(records)
        active_records = [r for r in records if r.get("hitCall") == 1
                          or str(r.get("hitCall", "")).lower() == "active"]
        active = len(active_records)

        # Collect endpoint category names from active hits
        categories = []
        for r in active_records:
            cat = r.get("endpointCategory") or r.get("aeid") or r.get("assayEndpointName")
            if cat and str(cat) not in categories:
                categories.append(str(cat))

        result["assays_tested"] = tested
        result["assays_active"] = active
        result["activity_score"] = round(active / tested, 4) if tested > 0 else 0.0
        result["top_hit_categories"] = "|".join(categories[:10]) if categories else None

        logger.info(
            "ToxCast: %s — %d tested, %d active (score=%.3f)",
            dtxsid, tested, active, result["activity_score"],
        )
    else:
        logger.warning("ToxCast: %s — no data returned", dtxsid)

    _save_cache(key, result)
    return result


def get_bioactivity_batch(dtxsid_list: List[str]) -> List[Dict[str, Any]]:
    """Fetch ToxCast bioactivity for a list of DTXSIDs."""
    return [get_bioactivity(dtxsid) for dtxsid in dtxsid_list]


# ── M3.1c: ChemExpo Exposure Data ─────────────────────────────────────────────

def get_functional_use(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ChemExpo functional use data for a single DTXSID.

    Returns a dict with:
      dtxsid, functional_uses (pipe-delimited), use_count
    """
    key = _cache_key("funcuse", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    data = _get(f"/exposure/functional-use/search/by-dtxsid/{dtxsid}")

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "functional_uses": None,
        "use_count": 0,
    }

    if data:
        records = data if isinstance(data, list) else data.get("data", [])
        uses = []
        for r in records:
            use = r.get("functionalUse") or r.get("use") or r.get("reportedFunctionalUse")
            if use and str(use) not in uses:
                uses.append(str(use))
        result["functional_uses"] = "|".join(uses) if uses else None
        result["use_count"] = len(records)
        logger.info("ChemExpo functional use: %s — %d records", dtxsid, len(records))
    else:
        logger.warning("ChemExpo functional use: %s — no data", dtxsid)

    _save_cache(key, result)
    return result


def get_product_data(dtxsid: str) -> Dict[str, Any]:
    """
    Fetch ChemExpo product-level data for a single DTXSID.

    Returns a dict with:
      dtxsid, product_categories (pipe-delimited),
      national_product_count
    """
    key = _cache_key("proddata", dtxsid)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    data = _get(f"/exposure/product-data/search/by-dtxsid/{dtxsid}")

    result: Dict[str, Any] = {
        "dtxsid": dtxsid,
        "product_categories": None,
        "national_product_count": 0,
    }

    if data:
        records = data if isinstance(data, list) else data.get("data", [])
        cats = []
        for r in records:
            cat = (
                r.get("productCategory")
                or r.get("puc")
                or r.get("generalCategory")
            )
            if cat and str(cat) not in cats:
                cats.append(str(cat))
        result["product_categories"] = "|".join(cats) if cats else None
        result["national_product_count"] = len(records)
        logger.info("ChemExpo product data: %s — %d products", dtxsid, len(records))
    else:
        logger.warning("ChemExpo product data: %s — no data", dtxsid)

    _save_cache(key, result)
    return result


def get_chemexpo_batch(dtxsid_list: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch combined ChemExpo data (functional use + product data) for a list of DTXSIDs.
    Returns merged dicts.
    """
    results = []
    for dtxsid in dtxsid_list:
        func = get_functional_use(dtxsid)
        prod = get_product_data(dtxsid)
        merged = {**func, **{k: v for k, v in prod.items() if k != "dtxsid"}}
        results.append(merged)
    return results
