# Hair Glue Project — ROADMAP for Milestone 2

**Milestone:** M2 — Deep Chemical Enrichment & Interactive Reporting  
**Target:** Complete before M3 begins  
**Owners:** Wilbert Fletcher (primary decision maker)  
**Last Updated:** 2026-03-28

---

## Overview

Milestone 2 builds on the M0 data foundation and M1 hazard/regulatory layer to:

1. **M2.1** Close the identity resolution gap (56 unmatched rows → target ≥85% coverage)
2. **M2.2** Enrich chemicals with structural data from ChemSpider (now that we have a live API key)
3. **M2.3** Integrate ECHA REACH registration data for regulatory completeness
4. **M2.4** Generate comprehensive chemical profile reports combining all data sources

---

## Prerequisites: What M0 + M1 Provide

| Output | Rows | Status |
|--------|------|--------|
| `warehouse/dim_products.parquet` | 139 products | ✅ |
| `warehouse/dim_ingredients.parquet` | 16 ingredients | ✅ |
| `warehouse/fact_product_ingredients.parquet` | 147 rows | ✅ |
| `warehouse/ref_chemicals.parquet` | 13 chemicals (PubChem) | ✅ |
| `warehouse/ingredient_identity_matched.parquet` | 147 rows (61.9% canonical match) | ✅ |
| `warehouse/ref_chemicals_hazard.parquet` | 20 rows (GHS from PubChem PUG View) | ✅ |
| `warehouse/dim_hazard_classes.parquet` | 14 GHS classes | ✅ |
| `warehouse/fact_chemical_hazards.parquet` | chemical→hazard links | ✅ |
| `warehouse/product_hazard_summary.parquet` | 139 products w/ risk scores | ✅ |

**Key gaps M2 addresses:**
- 56 unmatched ingredient rows (no canonical name or CASRN)
- No structural data (SMILES, InChIKey)
- No REACH registration status
- Reports lack cross-source chemical profiles

---

## Task M2.1: Fallback Chemical Identity Resolution

### Problem

M0.3 achieved 61.9% canonical name match (91/147 rows). The remaining 56 rows have either:
- Null CASRN (no CAS number reported in CSCP)
- Valid CASRN but no PubChem match (rare edge cases)
- Generic/mixture names that don't resolve to a single compound

### Approach

1. **Extract unmatched ingredient names** from `ingredient_identity_matched.parquet` where `canonical_name IS NULL`
2. **Normalize names:** lowercase, strip whitespace, remove parenthetical qualifiers (e.g., "(and)" conjunctions)
3. **PubChem synonym search:** Query PubChem REST API `/compound/name/{name}/cids/JSON` for each unmatched name
4. **Fuzzy matching:** For names that don't exact-match, use token-based similarity (e.g., `rapidfuzz` or `thefuzz`) against PubChem synonym lists
5. **Assign confidence scores:**
   - 1.0 = exact PubChem name match
   - 0.8–0.99 = synonym match
   - 0.5–0.79 = fuzzy match (flag for manual review)
   - <0.5 = no match (likely a mixture or trade name)

### Implementation

```python
# pipeline/transform/resolve_identity_fallback.py
# Key function signatures:
def normalize_ingredient_name(raw_name: str) -> str: ...
def search_pubchem_synonyms(name: str) -> Optional[dict]: ...
def fuzzy_match_chemical(name: str, candidates: list) -> tuple[str, float]: ...
def resolve_unmatched_ingredients(df: pd.DataFrame) -> pd.DataFrame: ...
```

### Dependencies
- `rapidfuzz` or `thefuzz` (install via pip)
- PubChem REST API (no key required)

### Acceptance Target
- Overall canonical match rate ≥85% (up from 61.9%)

**Actual (2026-03-28):** Achieved 100% match rate (147/147). Implemented in `pipeline/transform/resolve_identity_fallback.py`. Used PubChem name search for BHA (CAS retry), manual mappings for 6 ingredients (Carbon black, Cocamide DEA, Crystalline silica, Mineral oils, Retinol esters, Talc). Fuzzy matching via `rapidfuzz` installed but not needed — all resolved by exact search or manual mapping. Report: `reports/M2.1_fallback_resolution_report.md`.
- All fuzzy matches with confidence <0.7 flagged for manual review

---

## Task M2.2: ChemSpider Live Enrichment ✅ COMPLETE 2026-03-28

**Actual:** 12/13 chemicals enriched. Fixed status-polling bug in
`pipeline/extract/chemspider.py` (was missing GET /filter/{id}/status
poll; went straight to results before query completed). API key loaded
via `python-dotenv` in `pipeline/transform/enrich_chemspider.py`.

## Task M2.2: ChemSpider Live Enrichment (original spec)

### Problem

No structural data (SMILES, InChIKey, molecular properties) exists for identified chemicals.

### Approach

1. **Load** `ref_chemicals.parquet` (13 chemicals with CAS/names from M0.3)
2. **Query ChemSpider** by CASRN first, then by name as fallback
3. **Extract:** SMILES, InChIKey, molecular_weight, molecular_formula, ChemSpider ID
4. **Rate limit:** Max 15 requests/minute (ChemSpider free tier)
5. **Cache results** to avoid redundant API calls

### Configuration

API key is now stored in `.env` (gitignored):
```bash
# .env
CHEMSPIDER_API_KEY=<your_key>
```

Load in Python:
```python
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("CHEMSPIDER_API_KEY")
```

### Output

`warehouse/ref_chemicals_structure.parquet`:

| Column | Type | Description |
|--------|------|-------------|
| casrn | str | CAS Registry Number (join key) |
| chemspider_id | int | ChemSpider compound ID |
| smiles | str | Canonical SMILES string |
| inchikey | str | InChIKey identifier |
| molecular_formula | str | e.g., C2H6O |
| molecular_weight | float | Daltons |
| source | str | "chemspider" |
| fetched_at | datetime | Timestamp of API call |

---

## Task M2.3: ECHA REACH Registration Data ✅ COMPLETE 2026-03-28

**Actual:** Used ECHA Registered Substances bulk export (not IUCLID API —
see DEC-009). 12/14 chemicals matched. Loader: `pipeline/extract/echa_reach.py`.
Script: `warehouse/source_reach_detail.py`. CLI: `enrich-reach`.
Output: `warehouse/ref_chemicals_reach.parquet`.

## Task M2.3: ECHA REACH Registration Data (original spec)

### Problem

No regulatory registration data exists. REACH status tells us whether a chemical is registered for use in the EU, at what tonnage band, and by how many registrants.

### IMPORTANT: API Clarification

The **ECHA Submission Portal API (S2S)** that was previously referenced is for **submitting IUCLID dossiers** (CLP/PCN notifications). It is NOT suitable for looking up chemical registration data.

For M2.3, we need one of:
1. **ECHA CHEM API** — REST API at `https://echa.europa.eu/information-on-chemicals` (may require scraping)
2. **ECHA bulk download** — Structured data exports from ECHA dissemination site
3. **ECHA IUCLID substance data** — Public IUCLID datasets

### Decision Required
Document as **DEC-006** in DECISIONS.md which ECHA data source to use.

### Output

`warehouse/ref_chemicals_reach.parquet`:

| Column | Type | Description |
|--------|------|-------------|
| casrn | str | Join key |
| reach_registered | bool | Has REACH registration? |
| tonnage_band | str | e.g., "1-10 tonnes", "100-1000 tonnes" |
| registrant_count | int | Number of registrants |
| registration_type | str | "Full", "Intermediate", "PPORD" |
| last_updated | date | Data freshness |
| source | str | Data source identifier |

---

## Task M2.4: Enhanced Reporting ✅ COMPLETE 2026-03-28

**Actual:** Generated by `warehouse/generate_m2_reports.py`.
All three reports written to `reports/`.

## Task M2.4: Enhanced Reporting (original spec)

### Reports to Generate

1. **`reports/M2_chemical_profiles.md`** — For each of the 13+ identified chemicals:
   - Identity (name, CAS, synonyms)
   - Structure (SMILES, InChIKey, molecular properties) — from M2.2
   - Hazard profile (GHS classes, H-codes, signal word) — from M1
   - Regulatory status (REACH registration, tonnage) — from M2.3
   - Products containing this chemical (count, brands)

2. **`reports/M2_coverage_summary.md`** — Data completeness matrix:
   - Which chemicals have identity / structure / hazard / regulatory data
   - Gap analysis and recommendations

3. **`reports/M2_enrichment_delta.md`** — What M2 added:
   - New identity matches from fallback resolution
   - New structural data from ChemSpider
   - New regulatory data from ECHA
   - Before/after comparison tables

---

## Recommended Task Order

```
M2.1 (Fallback Identity)  →  M2.2 (ChemSpider)  →  M2.3 (ECHA REACH)  →  M2.4 (Reports)
         ↓ (improves chemical list for M2.2/M2.3)
```

M2.1 should be done first because resolving more chemicals gives M2.2 and M2.3 more targets to enrich.
