"""
Hazard Enrichment Transform

Enriches dim_chemical with hazard data from ECHA REACH API.
"""

import pandas as pd
from pathlib import Path
from pipeline.extract.echa_reach import ECHARearchAPI


def enrich_chemicals_with_hazards(dim_chemical_path: str, output_path: str) -> None:
    """
    Enrich dim_chemical table with hazard data from ECHA REACH.

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
        print("No CASRNs found, skipping hazard enrichment")
        return

    # Initialize ECHA API client
    api = ECHARearchAPI()

    # Fetch hazard data in batches
    hazard_df = api.fetch_hazards_batch(casrns, batch_size=5, delay=0.5)
    print(f"Fetched hazard data for {len(hazard_df)} chemicals")

    # Merge hazard data back to dim_chemical
    # First, prepare hazard data for merging
    hazard_cols = [
        'casrn', 'ec_number', 'substance_name', 'ghs_classes',
        'hazard_statements', 'precautionary_statements', 'signal_word',
        'data_source', 'last_updated'
    ]

    hazard_merge = hazard_df[hazard_cols].copy()

    # Update hazard status based on data availability
    hazard_merge['hazard_status'] = hazard_merge.apply(
        lambda row: 'ENRICHED' if pd.notna(row['ghs_classes']) and row['ghs_classes'] != ''
        else 'PENDING_SOURCE',
        axis=1
    )

    # Merge with dim_chemical on casrn
    enriched = dim_chemical.merge(
        hazard_merge,
        on='casrn',
        how='left',
        suffixes=('', '_echa')
    )

    # Update hazard fields where ECHA data is available
    hazard_fields = [
        'ec_number', 'substance_name', 'ghs_classes',
        'hazard_statements', 'precautionary_statements', 'signal_word',
        'data_source', 'last_updated', 'hazard_status'
    ]

    for field in hazard_fields:
        echa_col = f'{field}_echa'
        if echa_col in enriched.columns:
            # Update only where ECHA data exists
            mask = enriched[echa_col].notna()
            enriched.loc[mask, field] = enriched.loc[mask, echa_col]
            enriched.drop(columns=[echa_col], inplace=True)

    # For chemicals without CASRN, keep status as PENDING_SOURCE
    no_casrn_mask = enriched['casrn'].isna()
    enriched.loc[no_casrn_mask, 'hazard_status'] = 'PENDING_SOURCE'

    # Save enriched chemical dimension
    enriched.to_parquet(output_path, index=False)
    print(f"Saved enriched chemical dimension to {output_path}")

    # Print summary
    status_counts = enriched['hazard_status'].value_counts()
    print("Hazard enrichment summary:")
    print(status_counts)

    enriched_count = status_counts.get('ENRICHED', 0)
    total_count = len(enriched)
    print(".1f")


if __name__ == "__main__":
    # Example usage
    dim_chemical_path = "data/curated/dim_chemical.parquet"
    output_path = "data/curated/dim_chemical_enriched.parquet"

    enrich_chemicals_with_hazards(dim_chemical_path, output_path)