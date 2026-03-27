# CompTox CTX Enrichment — Hair Glue Project

## What CTX Enrichment Does
- Resolves chemicals in `dim_chemical.parquet` to EPA CompTox DTXSID/DTXCID
- Populates structure identifiers: SMILES, InChIKey, InChI, formula, molecular weight, preferred name
- Uses batch endpoints for CASRN and name-based lookup
- All hazard fields remain NULL (hazard enrichment deferred to M2)
- Writes output to `data/curated/dim_chemical_enriched.parquet`
- Writes stats to `data/curated/fact_resolution_stats.parquet`

## What It Does NOT Do
- Does NOT fetch or populate GHS hazard classifications (deferred)
- Does NOT use ChemSpider or ECHA APIs
- Does NOT require any paid or proprietary data

## Setup
1. Register for a free EPA CompTox API key: https://comptox.epa.gov/dashboard/api
2. Set your API key in your environment (do NOT commit to repo):
   ```bash
   export CTX_API_KEY=your_key_here
   ```
   Or add to a `.env` file if using dotenv.

## How to Run
```bash
python -m pipeline.cli ingest-cscp --csv <path_to_cscp_snapshot.csv>
python -m pipeline.cli enrich-ctx
python -m pipeline.cli build-warehouse
```

## DuckDB Views
- `v_resolution_summary`: Summary of chemical resolution stats
- `v_unresolved_chemicals`: List of unresolved chemicals for manual review

## Notes
- All API calls are cached to `data/raw/ctx_cache/` by request hash
- No secrets or API keys are stored in outputs
- If CTX API endpoints change, update `pipeline/extract/comptox_ctx.py` accordingly
