"""
CTX Enrichment Transform

Enriches dim_chemical with CompTox CTX structure and identifier data.
"""
import pandas as pd
from pipeline.extract.comptox_ctx import search_by_cas_batch, search_by_name_batch, get_chemical_details_batch

def enrich_chemicals_with_ctx(dim_chemical_path: str, output_path: str, stats_path: str) -> None:
    dim_chem = pd.read_parquet(dim_chemical_path)
    cas_mask = dim_chem['casrn'].notna() & (dim_chem['casrn'].str.strip() != "")
    cas_list = dim_chem.loc[cas_mask, 'casrn'].unique().tolist()
    name_mask = ~cas_mask & dim_chem['ingredient_normalized'].notna()
    name_list = dim_chem.loc[name_mask, 'ingredient_normalized'].unique().tolist()

    # CASRN batch search
    cas_df = search_by_cas_batch(cas_list) if cas_list else pd.DataFrame()
    # Name batch search
    name_df = search_by_name_batch(name_list) if name_list else pd.DataFrame()

    # Merge DTXSID into dim_chem
    dim_chem = dim_chem.copy()
    dim_chem['dtxsid'] = None
    dim_chem['dtxsid_source'] = None
    if not cas_df.empty:
        dim_chem = dim_chem.merge(cas_df[['casrn', 'dtxsid']], on='casrn', how='left', suffixes=('', '_cas'))
        dim_chem['dtxsid'] = dim_chem['dtxsid'].combine_first(dim_chem['dtxsid_cas'])
        dim_chem['dtxsid_source'] = dim_chem['dtxsid_source'].combine_first(dim_chem['dtxsid'].notna().map(lambda x: 'CAS' if x else None))
        dim_chem = dim_chem.drop(columns=['dtxsid_cas'])
    if not name_df.empty:
        dim_chem = dim_chem.merge(name_df[['ingredient_normalized', 'dtxsid']], on='ingredient_normalized', how='left', suffixes=('', '_name'))
        dim_chem['dtxsid'] = dim_chem['dtxsid'].combine_first(dim_chem['dtxsid_name'])
        dim_chem['dtxsid_source'] = dim_chem['dtxsid_source'].combine_first(dim_chem['dtxsid'].notna().map(lambda x: 'NAME' if x else None))
        dim_chem = dim_chem.drop(columns=['dtxsid_name'])

    # Fetch details for resolved DTXSIDs
    resolved = dim_chem['dtxsid'].notna()
    dtxsid_list = dim_chem.loc[resolved, 'dtxsid'].unique().tolist()
    details_df = get_chemical_details_batch(dtxsid_list) if dtxsid_list else pd.DataFrame()
    if not details_df.empty:
        dim_chem = dim_chem.merge(details_df, on='dtxsid', how='left')

    # Set source_priority and hazard fields
    dim_chem['source_priority'] = 'CTX'
    dim_chem['hazard_status'] = 'PENDING_SOURCE'
    # All hazard fields remain NULL

    # Write output
    dim_chem.to_parquet(output_path, index=False)

    # Write stats
    stats = {
        'total_chemicals': len(dim_chem),
        'cas_present_count': cas_mask.sum(),
        'resolved_dtxsid_count': dim_chem['dtxsid'].notna().sum(),
        'resolved_by_cas_count': cas_df['dtxsid'].notna().sum() if not cas_df.empty else 0,
        'resolved_by_name_count': name_df['dtxsid'].notna().sum() if not name_df.empty else 0,
        'unresolved_count': dim_chem['dtxsid'].isna().sum(),
        'resolution_rate': float(dim_chem['dtxsid'].notna().sum()) / len(dim_chem) if len(dim_chem) else 0.0
    }
    pd.DataFrame([stats]).to_parquet(stats_path, index=False)
