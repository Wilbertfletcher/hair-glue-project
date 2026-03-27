"""
ChemSpider Enrichment Transform

Enriches dim_chemical with chemical structure data from ChemSpider API.
"""

import pandas as pd
from pathlib import Path
from pipeline.extract.chemspider import ChemSpiderAPI


def enrich_chemicals_with_chemspider(dim_chemical_path: str, output_path: str) -> None:
    """
    Enrich dim_chemical table with ChemSpider data (structures, identifiers).

    Args:
        dim_chemical_path: Path to dim_chemical.parquet
        output_path: Path to write enriched dim_chemical.parquet
    """
    # Load current chemical dimension
    dim_chemical = pd.read_parquet(dim_chemical_path)
    print(f"Loaded {len(dim_chemical)} chemicals from {dim_chemical_path}")

    # Get CASRNs that have values
    casrns = dim_chemical['casrn'].dropna().unique().tolist()
    print(f"Found {len(casrns)} chemicals with CASRNs")

    if not casrns:
        print("No CASRNs found, skipping ChemSpider enrichment")
        return

    # Initialize ChemSpider API client
    import os
    api_key = os.getenv('CHEMSPIDER_API_KEY')
    api = ChemSpiderAPI(api_key=api_key)

    # Fetch ChemSpider data in batches
    chemspider_df = api.fetch_batch(casrns, batch_size=5, delay=0.5)
    print(f"Fetched ChemSpider data for {len(chemspider_df)} chemicals")

    # Merge ChemSpider data back to dim_chemical
    chemspider_merge = chemspider_df[[
        'casrn', 'chemspider_id', 'smiles', 'inchi', 'inchikey',
        'molecular_formula', 'molecular_weight', 'common_name',
        'systematic_name', 'pubchem_cid', 'data_source', 'last_updated'
    ]].copy()

    # Merge with dim_chemical on casrn
    enriched = dim_chemical.merge(
        chemspider_merge,
        on='casrn',
        how='left',
        suffixes=('', '_cs')
    )

    # Update ChemSpider fields where data is available
    chemspider_fields = [
        'chemspider_id', 'smiles', 'inchi', 'inchikey',
        'molecular_formula', 'molecular_weight', 'common_name',
        'systematic_name', 'pubchem_cid', 'data_source', 'last_updated'
    ]

    for field in chemspider_fields:
        cs_col = f'{field}_cs'
        if cs_col in enriched.columns:
            # Update only where ChemSpider data exists
            mask = enriched[cs_col].notna()
            enriched.loc[mask, field] = enriched.loc[mask, cs_col]
            enriched.drop(columns=[cs_col], inplace=True)

    # Save enriched chemical dimension
    enriched.to_parquet(output_path, index=False)
    print(f"Saved enriched chemical dimension to {output_path}")

    # Print summary
    found_count = chemspider_df['chemspider_id'].notna().sum()
    total_count = len(chemspider_df)
    print("ChemSpider enrichment summary:")
    print(f"Chemicals found: {found_count}/{total_count} ({100.0 * found_count / total_count:.1f}%)")


if __name__ == "__main__":
    # Example usage
    dim_chemical_path = "data/curated/dim_chemical.parquet"
    output_path = "data/curated/dim_chemical_chemspider.parquet"

    enrich_chemicals_with_chemspider(dim_chemical_path, output_path)