"""
EPA CompTox CTX API Client

Provides batch search and chemical detail retrieval for structure enrichment.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Optional
import pandas as pd
import requests
from pipeline.utils.http import RateLimiter, retry_with_backoff

CTX_BASE_URL = "https://comptox.epa.gov/ctx-api"
CTX_API_KEY = os.getenv("CTX_API_KEY")
CACHE_DIR = Path("data/raw/ctx_cache/")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "HairGlueProject/1.0 (research@hairglue.org)"
}
if CTX_API_KEY:
    HEADERS["x-api-key"] = CTX_API_KEY

rate_limiter = RateLimiter(max_calls=3, period=1.0)  # 3 req/sec

def _cache_response(key: str, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_DIR / f"{key}.json", "w") as f:
        json.dump(data, f)

def _load_cache(key: str) -> Optional[dict]:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None

def _hash_payload(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

@retry_with_backoff
@rate_limiter
def search_by_cas_batch(cas_list: List[str]) -> pd.DataFrame:
    """Batch resolve CASRN to DTXSID using CTX API."""
    payload = {"casrnList": cas_list}
    key = f"cas_batch_{_hash_payload(payload)}"
    cached = _load_cache(key)
    if cached:
        data = cached
    else:
        url = f"{CTX_BASE_URL}/chemical/search/by-casrn"
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _cache_response(key, data)
    # Parse response
    rows = []
    for chem in data.get("results", []):
        rows.append({
            "dtxsid": chem.get("dtxsid"),
            "casrn": chem.get("casrn"),
            "preferredName": chem.get("preferredName")
        })
    return pd.DataFrame(rows)

@retry_with_backoff
@rate_limiter
def search_by_name_batch(name_list: List[str]) -> pd.DataFrame:
    """Batch resolve names to DTXSID using CTX API."""
    payload = {"nameList": name_list}
    key = f"name_batch_{_hash_payload(payload)}"
    cached = _load_cache(key)
    if cached:
        data = cached
    else:
        url = f"{CTX_BASE_URL}/chemical/search/by-name"
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _cache_response(key, data)
    rows = []
    for chem in data.get("results", []):
        rows.append({
            "dtxsid": chem.get("dtxsid"),
            "preferredName": chem.get("preferredName")
        })
    return pd.DataFrame(rows)

@retry_with_backoff
@rate_limiter
def get_chemical_details_batch(dtxsid_list: List[str], projection="chemicaldetailall") -> pd.DataFrame:
    """Batch fetch chemical details for DTXSIDs."""
    payload = {"dtxsidList": dtxsid_list, "projection": projection}
    key = f"details_batch_{_hash_payload(payload)}"
    cached = _load_cache(key)
    if cached:
        data = cached
    else:
        url = f"{CTX_BASE_URL}/chemical/batch/details"
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        _cache_response(key, data)
    rows = []
    for chem in data.get("results", []):
        rows.append({
            "dtxsid": chem.get("dtxsid"),
            "dtxcid": chem.get("dtxcid"),
            "preferredName": chem.get("preferredName"),
            "smiles": chem.get("smiles"),
            "inchikey": chem.get("inchikey"),
            "inchi": chem.get("inchi"),
            "molFormula": chem.get("molFormula"),
            "molWeight": chem.get("molWeight")
        })
    return pd.DataFrame(rows)
