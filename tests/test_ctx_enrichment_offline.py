
import pandas as pd
from unittest.mock import patch
from pipeline.transform.enrich_ctx import enrich_chemicals_with_ctx


def test_enrich_ctx_offline(tmp_path):
    # Prepare fixture dim_chemical
    df = pd.DataFrame({
        'casrn': ['50-00-0', None],
        'ingredient_normalized': ['formaldehyde', 'water']
    })
    input_path = tmp_path / "dim_chemical.parquet"
    output_path = tmp_path / "dim_chemical_enriched.parquet"
    stats_path = tmp_path / "fact_resolution_stats.parquet"
    df.to_parquet(input_path, index=False)

    # Mock CTX client functions
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
        mock_name.return_value = pd.DataFrame([
            {
                'dtxsid': 'DTXSID2020002',
                'preferredName': 'Water'
            }
        ])
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
            },
            {
                'dtxsid': 'DTXSID2020002',
                'dtxcid': 'DTXCID102',
                'preferredName': 'Water',
                'smiles': 'O',
                'inchikey': 'XLYOFNOQVPJJNP-UHFFFAOYSA-N',
                'inchi': 'InChI=1S/H2O/h1H2',
                'molFormula': 'H2O',
                'molWeight': 18.02
            }
        ])
        enrich_chemicals_with_ctx(
            str(input_path), str(output_path), str(stats_path)
        )
        enriched = pd.read_parquet(output_path)
        stats = pd.read_parquet(stats_path)
        assert 'dtxsid' in enriched.columns
        assert 'smiles' in enriched.columns
        assert enriched['dtxsid'].notna().sum() == 2
        assert stats['resolved_dtxsid_count'][0] == 2
