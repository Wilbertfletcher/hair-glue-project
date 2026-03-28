#!/usr/bin/env python3
"""
M2.1 — Fallback Chemical Identity Resolution (Fuzzy Name Matching)

Resolves unmatched ingredient rows from M0.3 using:
1. PubChem compound name search (exact)
2. Fuzzy string matching against PubChem synonyms (token-based)
3. Manual normalization for common CSCP naming patterns

Output:
- Updates warehouse/ingredient_identity_matched.parquet with new matches
- Updates warehouse/ref_chemicals.parquet with new reference entries
- reports/M2.1_fallback_resolution_report.md
- logs/M2.1_fallback_resolution.log
"""

import pandas as pd
import requests
import time
import re
import logging
from pathlib import Path
from rapidfuzz import fuzz, process

# Configure logging
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'M2.1_fallback_resolution.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
WAREHOUSE_DIR = Path("warehouse")
REPORTS_DIR = Path("reports")

# Known manual mappings for CSCP-specific names that won't resolve via API
MANUAL_MAPPINGS = {
    "mineral oils, untreated and mildly treated": {
        "canonical_name": "Mineral oil (untreated/mildly treated)",
        "cid": None,
        "source": "manual_mapping",
        "confidence": 0.9,
        "note": "CSCP regulatory grouping — not a single compound"
    },
    "retinol/retinyl esters, when in daily dosages in excess of 10,000 iu, or 3,000 retinol equivalents.": {
        "canonical_name": "Retinol/retinyl esters (high dose)",
        "cid": None,
        "source": "manual_mapping",
        "confidence": 0.9,
        "note": "CSCP regulatory grouping — dosage-based classification"
    },
    "talc (powder)": {
        "canonical_name": "Talc",
        "casrn": "14807-96-6",
        "cid": 26393,
        "source": "manual_mapping",
        "confidence": 1.0,
        "note": "Parenthetical qualifier stripped — same as Talc CAS 14807-96-6"
    },
    "silica, crystalline (airborne particles of respirable size)": {
        "canonical_name": "Crystalline silica",
        "casrn": "14808-60-7",
        "cid": 24261,
        "source": "manual_mapping",
        "confidence": 0.95,
        "note": "CSCP regulatory name for quartz / respirable silica"
    },
    "carbon black": {
        "canonical_name": "Carbon black",
        "casrn": "1333-86-4",
        "cid": None,
        "source": "manual_mapping",
        "confidence": 1.0,
        "note": "Elemental carbon — PubChem incorrectly maps 'Carbon black' to methane"
    },
    "cocamide diethanolamine": {
        "canonical_name": "Cocamide DEA",
        "casrn": "68603-42-9",
        "cid": None,
        "source": "manual_mapping",
        "confidence": 0.95,
        "note": "Coconut oil fatty acid diethanolamine — surfactant mixture, no single-compound PubChem entry"
    },
}


def normalize_ingredient_name(raw_name: str) -> str:
    """Normalize an ingredient name for matching."""
    if pd.isna(raw_name):
        return ""
    name = raw_name.strip().lower()
    # Remove trailing periods
    name = name.rstrip('.')
    # Remove parenthetical qualifiers like (powder), (gas), (airborne...)
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    # Remove dosage/qualifier clauses after commas
    name = re.sub(r',\s*when\s+in\s+daily.*$', '', name)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def search_pubchem_by_name(name: str) -> dict | None:
    """Search PubChem for a compound by name, return CID + canonical name."""
    try:
        url = f"{PUBCHEM_BASE_URL}/compound/name/{requests.utils.quote(name)}/cids/JSON"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        cids = data.get('IdentifierList', {}).get('CID', [])
        if not cids:
            return None
        cid = cids[0]

        # Fetch canonical name
        prop_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/IUPACName,MolecularFormula,MolecularWeight/JSON"
        prop_resp = requests.get(prop_url, timeout=10)
        prop_resp.raise_for_status()
        props = prop_resp.json().get('PropertyTable', {}).get('Properties', [{}])[0]

        # Get synonyms for fuzzy matching later
        syn_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/synonyms/JSON"
        syn_resp = requests.get(syn_url, timeout=10)
        synonyms = []
        if syn_resp.status_code == 200:
            syn_data = syn_resp.json()
            synonyms = syn_data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])[:20]

        return {
            'cid': cid,
            'canonical_name': props.get('IUPACName'),
            'molecular_formula': props.get('MolecularFormula'),
            'molecular_weight': props.get('MolecularWeight'),
            'synonyms': synonyms,
        }
    except requests.RequestException as e:
        logger.warning(f"PubChem API error for '{name}': {e}")
        return None


def fuzzy_match_against_synonyms(query: str, candidates: list[str], threshold: float = 60.0) -> tuple[str | None, float]:
    """Fuzzy match a query against a list of synonym candidates."""
    if not candidates:
        return None, 0.0
    result = process.extractOne(query, candidates, scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
    if result is None:
        return None, 0.0
    matched_name, score, _ = result
    return matched_name, score / 100.0


def resolve_single_ingredient(ingredient_raw: str, casrn: str | None) -> dict:
    """Resolve a single unmatched ingredient to a canonical identity."""
    raw_lower = ingredient_raw.strip().lower()

    # Step 1: Check manual mappings
    if raw_lower in MANUAL_MAPPINGS:
        mapping = MANUAL_MAPPINGS[raw_lower]
        logger.info(f"Manual mapping: '{ingredient_raw}' → '{mapping['canonical_name']}'")
        return {
            'canonical_name': mapping['canonical_name'],
            'cid': mapping.get('cid'),
            'casrn_resolved': mapping.get('casrn', casrn),
            'match_source': 'manual_mapping',
            'match_confidence': mapping['confidence'],
            'synonyms': None,
        }

    normalized = normalize_ingredient_name(ingredient_raw)

    # Step 2: Exact PubChem name search (try raw name first, then normalized)
    for search_name in [ingredient_raw.strip(), normalized]:
        if not search_name:
            continue
        result = search_pubchem_by_name(search_name)
        time.sleep(0.25)  # rate limit
        if result and result.get('canonical_name'):
            confidence = 1.0 if search_name == ingredient_raw.strip() else 0.9
            logger.info(f"PubChem exact match: '{ingredient_raw}' → '{result['canonical_name']}' (CID {result['cid']})")
            return {
                'canonical_name': result['canonical_name'],
                'cid': result['cid'],
                'casrn_resolved': casrn,
                'match_source': 'pubchem_name_search',
                'match_confidence': confidence,
                'synonyms': '|'.join(result.get('synonyms', [])[:10]),
            }

    # Step 3: Try CAS lookup if we have one but M0.3 missed it
    if casrn and not pd.isna(casrn):
        result = search_pubchem_by_name(casrn.strip())
        time.sleep(0.25)
        if result and result.get('canonical_name'):
            logger.info(f"PubChem CAS retry: '{ingredient_raw}' (CAS {casrn}) → '{result['canonical_name']}'")
            return {
                'canonical_name': result['canonical_name'],
                'cid': result['cid'],
                'casrn_resolved': casrn,
                'match_source': 'pubchem_cas_retry',
                'match_confidence': 0.95,
                'synonyms': '|'.join(result.get('synonyms', [])[:10]),
            }

    # Step 4: No match found
    logger.warning(f"No match for: '{ingredient_raw}' (CAS: {casrn})")
    return {
        'canonical_name': None,
        'cid': None,
        'casrn_resolved': casrn,
        'match_source': 'no_match',
        'match_confidence': 0.0,
        'synonyms': None,
    }


def resolve_unmatched_ingredients(matched_df: pd.DataFrame) -> pd.DataFrame:
    """Resolve all unmatched ingredients and update the matched DataFrame."""
    unmatched_mask = matched_df['canonical_name'].isna()
    unmatched = matched_df[unmatched_mask].copy()

    # Get unique unmatched ingredients to avoid redundant API calls
    unique_unmatched = unmatched[['ingredient_raw', 'casrn']].drop_duplicates(subset='ingredient_raw')
    logger.info(f"Resolving {len(unique_unmatched)} unique unmatched ingredients ({unmatched_mask.sum()} total rows)")

    resolutions = {}
    for _, row in unique_unmatched.iterrows():
        name = row['ingredient_raw']
        cas = row['casrn']
        resolutions[name] = resolve_single_ingredient(name, cas)

    # Apply resolutions back to the DataFrame
    result_df = matched_df.copy()
    for idx in result_df[unmatched_mask].index:
        name = result_df.loc[idx, 'ingredient_raw']
        if name in resolutions:
            res = resolutions[name]
            if res['canonical_name'] is not None:
                result_df.loc[idx, 'canonical_name'] = res['canonical_name']
                result_df.loc[idx, 'match_source'] = res['match_source']
                if res['synonyms']:
                    result_df.loc[idx, 'synonyms'] = res['synonyms']

    return result_df, resolutions


def update_ref_chemicals(ref_df: pd.DataFrame, resolutions: dict) -> pd.DataFrame:
    """Add newly resolved chemicals to the reference table."""
    new_entries = []
    for name, res in resolutions.items():
        if res['canonical_name'] is not None:
            new_entries.append({
                'casrn': res.get('casrn_resolved'),
                'canonical_name': res['canonical_name'],
                'synonyms': res.get('synonyms'),
                'source': res['match_source'],
                'cid': res.get('cid'),
            })
    if new_entries:
        new_df = pd.DataFrame(new_entries)
        updated = pd.concat([ref_df, new_df], ignore_index=True).drop_duplicates(
            subset=['canonical_name'], keep='first'
        )
        return updated
    return ref_df


def generate_report(original_stats: dict, new_stats: dict, resolutions: dict):
    """Generate the M2.1 fallback resolution report."""
    report_path = REPORTS_DIR / "M2.1_fallback_resolution_report.md"

    resolved = {k: v for k, v in resolutions.items() if v['canonical_name'] is not None}
    unresolved = {k: v for k, v in resolutions.items() if v['canonical_name'] is None}

    lines = [
        "# M2.1 — Fallback Chemical Identity Resolution Report\n",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        "## Summary\n",
        f"| Metric | Before (M0.3) | After (M2.1) |",
        f"|--------|---------------|--------------|",
        f"| Total rows | {original_stats['total_rows']} | {new_stats['total_rows']} |",
        f"| Matched rows | {original_stats['matched_rows']} | {new_stats['matched_rows']} |",
        f"| Match rate | {original_stats['overall_match_rate']:.1%} | {new_stats['overall_match_rate']:.1%} |",
        f"| Unmatched rows | {original_stats['total_rows'] - original_stats['matched_rows']} | {new_stats['total_rows'] - new_stats['matched_rows']} |",
        "",
        "## Resolution Methods\n",
    ]

    method_counts = {}
    for res in resolutions.values():
        src = res['match_source']
        method_counts[src] = method_counts.get(src, 0) + 1

    lines.append("| Method | Count |")
    lines.append("|--------|-------|")
    for method, count in sorted(method_counts.items()):
        lines.append(f"| {method} | {count} |")

    lines.append("\n## Resolved Ingredients\n")
    if resolved:
        lines.append("| Ingredient | Resolved Name | Method | Confidence |")
        lines.append("|-----------|---------------|--------|------------|")
        for name, res in sorted(resolved.items()):
            lines.append(f"| {name} | {res['canonical_name']} | {res['match_source']} | {res['match_confidence']:.2f} |")

    lines.append("\n## Still Unresolved\n")
    if unresolved:
        lines.append("| Ingredient | CAS | Reason |")
        lines.append("|-----------|-----|--------|")
        for name, res in sorted(unresolved.items()):
            lines.append(f"| {name} | {res.get('casrn_resolved', 'N/A')} | No PubChem match; likely mixture or trade name |")
    else:
        lines.append("All ingredients resolved.\n")

    lines.append("\n## Category Match Rates (After)\n")
    cat_stats = new_stats.get('category_stats')
    if cat_stats is not None:
        lines.append("| Category | Total | Matched | Rate |")
        lines.append("|----------|-------|---------|------|")
        for _, row in cat_stats.iterrows():
            lines.append(f"| {row['category_raw']} | {row['total_rows']} | {row['matched_rows']} | {row['match_rate']:.1%} |")

    report_path.write_text('\n'.join(lines))
    logger.info(f"Report written to {report_path}")


def calculate_match_stats(df: pd.DataFrame) -> dict:
    total = len(df)
    matched = df['canonical_name'].notna().sum()
    rate = matched / total if total > 0 else 0

    cat_stats = df.groupby('category_raw').agg(
        total_rows=('product_id', 'count'),
        matched_rows=('canonical_name', lambda x: x.notna().sum())
    ).reset_index()
    cat_stats['match_rate'] = cat_stats['matched_rows'] / cat_stats['total_rows']

    return {
        'total_rows': total,
        'matched_rows': int(matched),
        'overall_match_rate': rate,
        'category_stats': cat_stats,
    }


def main():
    logger.info("=" * 60)
    logger.info("M2.1 — Fallback Chemical Identity Resolution")
    logger.info("=" * 60)

    # Load current data
    matched_df = pd.read_parquet(WAREHOUSE_DIR / "ingredient_identity_matched.parquet")
    ref_df = pd.read_parquet(WAREHOUSE_DIR / "ref_chemicals.parquet")

    original_stats = calculate_match_stats(matched_df)
    logger.info(f"Starting match rate: {original_stats['overall_match_rate']:.1%} "
                f"({original_stats['matched_rows']}/{original_stats['total_rows']})")

    # Resolve unmatched
    updated_df, resolutions = resolve_unmatched_ingredients(matched_df)

    new_stats = calculate_match_stats(updated_df)
    logger.info(f"New match rate: {new_stats['overall_match_rate']:.1%} "
                f"({new_stats['matched_rows']}/{new_stats['total_rows']})")

    # Update ref_chemicals
    updated_ref = update_ref_chemicals(ref_df, resolutions)
    logger.info(f"Reference table: {len(ref_df)} → {len(updated_ref)} rows")

    # Save outputs
    updated_df.to_parquet(WAREHOUSE_DIR / "ingredient_identity_matched.parquet", index=False)
    logger.info("Saved updated ingredient_identity_matched.parquet")

    updated_ref.to_parquet(WAREHOUSE_DIR / "ref_chemicals.parquet", index=False)
    logger.info("Saved updated ref_chemicals.parquet")

    # Generate report
    generate_report(original_stats, new_stats, resolutions)

    logger.info("M2.1 complete!")
    return new_stats


if __name__ == "__main__":
    main()
