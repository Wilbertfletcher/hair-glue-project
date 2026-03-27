#!/usr/bin/env python3
"""
Hair Glue Project — M0.3 Chemical Identity Resolution (CAS-First Matching)

This script implements CAS-first chemical identity resolution for hair-glue ingredients.
It sources canonical chemical reference data from PubChem and matches against the fact table.

Output:
- warehouse/ref_chemicals.parquet: Canonical reference table
- warehouse/ingredient_identity_matched.parquet: Matched identities
- reports/M0.3_identity_resolution_report.md: Analysis report
- logs/M0.3_identity_resolution.log: Execution log

Author: AI Assistant
Date: 2026-03-25
"""

import pandas as pd
import requests
import time
import logging
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/M0.3_identity_resolution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
WAREHOUSE_DIR = Path("warehouse")
REPORTS_DIR = Path("reports")
LOGS_DIR = Path("logs")

def normalize_casrn(cas: str) -> str:
    """Normalize CASRN to standard format for API calls."""
    if pd.isna(cas) or cas.strip() == "":
        return None
    cas = cas.strip().replace(" ", "").replace("-", "")
    if len(cas) < 5:
        return None
    # Re-insert hyphens: XXXXXXX-XX-X format
    if len(cas) >= 7:
        cas = f"{cas[:-3]}-{cas[-3:-1]}-{cas[-1]}"
    return cas

def get_pubchem_compound_data(casrn: str) -> dict:
    """Fetch compound data from PubChem API."""
    try:
        # First, get CID from CASRN
        lookup_url = f"{PUBCHEM_BASE_URL}/compound/name/{casrn}/cids/JSON"
        response = requests.get(lookup_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'IdentifierList' not in data or not data['IdentifierList'].get('CID'):
            logger.warning(f"No CID found for CASRN {casrn}")
            return None

        cid = data['IdentifierList']['CID'][0]

        # Get full compound record
        record_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/JSON"
        response = requests.get(record_url, timeout=10)
        response.raise_for_status()
        record_data = response.json()

        if 'PC_Compounds' not in record_data or not record_data['PC_Compounds']:
            logger.warning(f"No compound record found for CID {cid} (CASRN {casrn})")
            return None

        compound = record_data['PC_Compounds'][0]

        # Extract title (canonical name)
        canonical_name = None
        synonyms = []

        for section in compound.get('props', []):
            if section.get('urn', {}).get('label') == 'IUPAC Name':
                canonical_name = section.get('value', {}).get('sval')
            elif section.get('urn', {}).get('label') == 'Synonyms':
                if 'value' in section and 'slist' in section['value']:
                    synonyms.extend(section['value']['slist'])

        # Fallback: use first synonym as canonical if no IUPAC name
        if not canonical_name and synonyms:
            canonical_name = synonyms[0]
            synonyms = synonyms[1:]

        # Filter synonyms
        synonyms = list(set([s for s in synonyms if len(s) <= 100]))[:10]

        return {
            'casrn': casrn,
            'canonical_name': canonical_name,
            'synonyms': '|'.join(synonyms),
            'source': 'pubchem',
            'cid': cid
        }

    except requests.RequestException as e:
        logger.error(f"API error for CASRN {casrn}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for CASRN {casrn}: {e}")
        return None

def build_reference_table(unique_casrns: list) -> pd.DataFrame:
    """Build canonical chemical reference table from PubChem."""
    logger.info(f"Fetching data for {len(unique_casrns)} unique CASRNs")

    reference_data = []
    for i, casrn in enumerate(unique_casrns):
        logger.info(f"Processing CASRN {i+1}/{len(unique_casrns)}: {casrn}")
        data = get_pubchem_compound_data(casrn)
        if data:
            reference_data.append(data)
        else:
            # Add placeholder for unmatched CASRNs
            reference_data.append({
                'casrn': casrn,
                'canonical_name': None,
                'synonyms': None,
                'source': 'pubchem_unmatched',
                'cid': None
            })
        time.sleep(0.2)  # Rate limiting

    df = pd.DataFrame(reference_data)
    logger.info(f"Reference table built with {len(df)} rows")
    return df

def perform_cas_matching(fact_df: pd.DataFrame, ref_df: pd.DataFrame) -> pd.DataFrame:
    """Perform CAS-first matching between fact table and reference data."""
    logger.info("Performing CAS-first matching")

    # Load dimension tables for ingredient_raw
    dim_products = pd.read_parquet(WAREHOUSE_DIR / "dim_products.parquet")
    dim_ingredients = pd.read_parquet(WAREHOUSE_DIR / "dim_ingredients.parquet")

    # Merge fact with dimensions to get ingredient_raw
    matched_df = fact_df.merge(dim_ingredients[['ingredient_id', 'ingredient_raw']],
                              on='ingredient_id', how='left')
    matched_df = matched_df.merge(dim_products[['product_id', 'product_name', 'category_raw']],
                                 on='product_id', how='left')

    # Left join with reference data on normalized CASRN
    matched_df['casrn_normalized'] = matched_df['casrn'].apply(normalize_casrn)
    ref_df['casrn_normalized'] = ref_df['casrn'].apply(normalize_casrn)

    matched_df = matched_df.merge(ref_df[['casrn_normalized', 'canonical_name', 'synonyms', 'source']],
                                 on='casrn_normalized', how='left')

    # Rename source to match_source
    matched_df = matched_df.rename(columns={'source': 'match_source'})

    # Clean up columns
    matched_df = matched_df[[
        'product_id', 'ingredient_id', 'ingredient_raw', 'casrn',
        'canonical_name', 'synonyms', 'match_source', 'category_raw'
    ]]

    # Fill match_source
    matched_df['match_source'] = matched_df['match_source'].fillna('no_match')

    logger.info(f"Matching complete: {len(matched_df)} rows processed")
    return matched_df

def calculate_match_stats(matched_df: pd.DataFrame) -> dict:
    """Calculate match rate statistics."""
    total_rows = len(matched_df)
    matched_rows = len(matched_df[matched_df['canonical_name'].notna()])
    match_rate = matched_rows / total_rows if total_rows > 0 else 0

    # By category
    category_stats = matched_df.groupby('category_raw').agg(
        total_rows=('product_id', 'count'),
        matched_rows=('canonical_name', lambda x: x.notna().sum())
    ).reset_index()
    category_stats['match_rate'] = category_stats['matched_rows'] / category_stats['total_rows']

    return {
        'overall_match_rate': match_rate,
        'total_rows': total_rows,
        'matched_rows': matched_rows,
        'category_stats': category_stats
    }

def generate_report(stats: dict, matched_df: pd.DataFrame):
    """Generate the identity resolution report."""
    report_path = REPORTS_DIR / "M0.3_identity_resolution_report.md"

    with open(report_path, 'w') as f:
        f.write("# Hair Glue Project — M0.3 Identity Resolution Report\n\n")
        f.write(f"**Generated:** 2026-03-25\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total rows processed:** {stats['total_rows']}\n")
        f.write(f"- **Overall match rate:** {stats['overall_match_rate']:.1%}\n")
        f.write(f"- **Matched rows:** {stats['matched_rows']}\n\n")

        f.write("## Match Rate by Category\n\n")
        f.write("| Category | Total Rows | Matched | Match Rate |\n")
        f.write("|----------|------------|---------|------------|\n")
        for _, row in stats['category_stats'].iterrows():
            f.write(f"| {row['category_raw']} | {row['total_rows']} | {row['matched_rows']} | {row['match_rate']:.1%} |\n")
        f.write("\n")

        f.write("## Sample Matched Results\n\n")
        sample = matched_df.head(20)[['ingredient_raw', 'casrn', 'canonical_name', 'match_source']]
        f.write(sample.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recommendations\n\n")
        if stats['overall_match_rate'] > 0.8:
            f.write("✅ **High match rate achieved.** Proceed with current approach. Fallback matching (name-based) can be deferred to M1.\n\n")
        elif stats['overall_match_rate'] > 0.4:
            f.write("⚠️ **Moderate match rate.** Acceptable for Phase 1. Consider fallback strategies in future phases.\n\n")
        else:
            f.write("❌ **Low match rate.** Discuss with stakeholder: defer identity resolution or source external CASRN mappings.\n\n")

        f.write("## Data Quality Notes\n\n")
        f.write("- CASRN normalization applied for API compatibility\n")
        f.write("- Synonyms limited to 10 per compound for storage efficiency\n")
        f.write("- Unmatched CASRNs marked with 'pubchem_unmatched' source\n\n")

    logger.info(f"Report generated: {report_path}")

def main():
    """Main execution function."""
    logger.info("Starting M0.3 Chemical Identity Resolution")

    # Ensure directories exist
    WAREHOUSE_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    # Load fact table
    fact_path = WAREHOUSE_DIR / "fact_product_ingredients.parquet"
    if not fact_path.exists():
        raise FileNotFoundError(f"Fact table not found: {fact_path}")

    fact_df = pd.read_parquet(fact_path)
    logger.info(f"Loaded fact table: {len(fact_df)} rows")

    # Get unique non-null CASRNs
    unique_casrns = fact_df['casrn'].dropna().unique().tolist()
    logger.info(f"Found {len(unique_casrns)} unique CASRNs to resolve")

    # Build reference table
    ref_df = build_reference_table(unique_casrns)
    ref_path = WAREHOUSE_DIR / "ref_chemicals.parquet"
    ref_df.to_parquet(ref_path, index=False)
    logger.info(f"Reference table saved: {ref_path}")

    # Perform matching
    matched_df = perform_cas_matching(fact_df, ref_df)
    matched_path = WAREHOUSE_DIR / "ingredient_identity_matched.parquet"
    matched_df.to_parquet(matched_path, index=False)
    logger.info(f"Matched results saved: {matched_path}")

    # Calculate statistics
    stats = calculate_match_stats(matched_df)

    # Generate report
    generate_report(stats, matched_df)

    logger.info("M0.3 Chemical Identity Resolution completed successfully")

if __name__ == "__main__":
    main()