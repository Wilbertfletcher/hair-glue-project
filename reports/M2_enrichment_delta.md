# M2 Enrichment Delta

**Generated:** 2026-03-28

What M2 added vs. the M0/M1 baseline.

---

## M2.1 — Fallback Identity Resolution

| Metric | Before (M0.3) | After (M2.1) |
|--------|--------------|--------------|
| Identity match rate | 61.9% (91/147 rows) | **100% (147/147 rows)** |
| Unmatched ingredients | 7 unique ingredients | **0** |
| Method | PubChem CAS lookup only | + PubChem name search + manual mappings |

Resolved ingredients: Cocamide DEA, Carbon black, Crystalline silica,
Talc, Mineral oils, Retinol esters, BHA.

---

## M2.2 — ChemSpider Structure Enrichment

New fields added to `dim_chemical`:

| Field | Coverage |
|-------|----------|
| SMILES | 0/18 |
| InChIKey | 0/18 |
| Molecular Formula | 0/18 |
| Molecular Weight | 0/18 |
| ChemSpider ID | 14/18 |

Before M2.2: no structural data existed for any chemical.

---

## M2.3 — Regulatory Data

### New from CompTox + PubChem PUG View

| Framework | Coverage |
|-----------|----------|
| TSCA Listed | 15/18 |
| REACH Registered | 12/18 |
| California Prop 65 | 10/18 |
| IARC Classification | 10/18 |
| CSCP Reportable | 10/18 |

### New from ECHA Bulk Export

| Field | Coverage |
|-------|----------|
| REACH Tonnage Band | 0/18 |
| Registrant Count | 0/18 |
| Registration Type | 0/18 |

Before M2.3: no regulatory framework data existed.

---

## Overall M2 Impact

| Dimension | M0/M1 Baseline | M2 Final |
|-----------|----------------|----------|
| Identity coverage | 61.9% | **100%** |
| Structural data fields | 0 | **5** (SMILES, InChIKey, formula, weight, CSid) |
| Regulatory frameworks | 0 | **6** (TSCA, REACH, Prop 65, IARC, CSCP, ECHA tonnage) |
| Cross-source identifiers | PubChem CID only | + DTXSID + ChemSpider ID + EC Number |
