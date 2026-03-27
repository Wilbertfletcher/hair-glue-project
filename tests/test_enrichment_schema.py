import pandas as pd
from pipeline.transform.enrich_ctx import enrich_chemicals_with_ctx


def test_enrichment_schema(tmp_path):
    df = pd.DataFrame({
        'casrn': ['50-00-0'],
        'ingredient_normalized': ['formaldehyde']
    })
    input_path = tmp_path / "dim_chemical.parquet"
    output_path = tmp_path / "dim_chemical_enriched.parquet"
    stats_path = tmp_path / "fact_resolution_stats.parquet"
    df.to_parquet(input_path, index=False)
    # Patch CTX client to return minimal details
    from unittest.mock import patch
    with (
        patch('pipeline.extract.comptox_ctx.search_by_cas_batch') as mock_cas,
        patch(
            'pipeline.extract.comptox_ctx.search_by_name_batch'
        ) as mock_name,
        patch(
            'pipeline.extract.comptox_ctx.get_chemical_details_batch'
        ) as mock_details
    ):
        mock_cas.return_value = pd.DataFrame([
            {
                'dtxsid': 'DTXSID2020001',
                'casrn': '50-00-0',
                'preferredName': 'Formaldehyde'
            }
        ])
        mock_name.return_value = pd.DataFrame([])
        mock_details.return_value = pd.DataFrame([
            {
                'dtxsid': 'DTXSID2020001',
                'dtxcid': 'DTXCID101',
                'preferredName': 'Formaldehyde',
                'smiles': 'C=O',
                'inchikey': 'WSFSSNUMVMOOMR-UHFFFAOYSA-N',
                'inchi': 'InChI=1S/CH2O/c1-2/h1H2',
                'molFormula': 'CH2O',
                'molWeight': 30.03
            }
        ])
        enrich_chemicals_with_ctx(
            str(input_path), str(output_path), str(stats_path)
        )
        enriched = pd.read_parquet(output_path)
        # Check required columns
        for col in [
            'dtxsid',
            'dtxcid',
            'smiles',
            'inchikey',
            'molFormula',
            'molWeight',
            'hazard_status',
        ]:
            assert col in enriched.columns
        # Hazard fields remain NULL
        assert enriched['hazard_status'].iloc[0] == 'PENDING_SOURCE'
