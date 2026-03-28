# M1 Regulatory Summary — Hair Glue Product Hazard Analysis

**Generated:** 2026-03-27  
**Milestone:** M1 — Regulatory Classification & Hazard Mapping  
**Data Source:** U.S. Cosmetic Safety & Product Tracker (CSCP)  
**Hazard Source:** PubChem PUG View API (GHS classifications)  

---

## Executive Summary

This analysis covers **139 hair-glue and related cosmetic products** from **43 companies** across **8 product categories**. Chemical identity resolution identified **20 unique chemicals**, of which **14** (70%) have GHS hazard data.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total products analyzed | 139 |
| Total unique chemicals | 20 |
| Chemicals with GHS data | 14 (70%) |
| Products classified HIGH risk | 118 (85%) |
| Products with reproductive hazards | 44 (32%) |
| Products containing carcinogens | 108 (78%) |
| Average hazard score (0–100) | 36.8 |
| Companies analyzed | 43 |
| Brands analyzed | 67 |

---

## Hazard Distribution

| Risk Level | Products | % of Total | Avg Score |
|------------|----------|------------|----------|
| HIGH | 118 | 84.9% | 41.4 |
| MEDIUM | 3 | 2.2% | 23.3 |
| LOW | 1 | 0.7% | 0.0 |
| NO_DATA | 17 | 12.2% | 10.0 |

## Top 10 Highest-Risk Products

| Rank | Product | Brand | Category | Score | Hazard Classes | Repro | Carc |
|------|---------|-------|----------|-------|---------------|-------|------|
| 1 | BLACK Borboleta Lash Adhesive | Borboleta | Makeup Products (non-perm | 90 | Eye Irrit|Repr/Dev|Resp Irrit|Skin Irrit | 1 | 0 |
| 2 | SILVER Borboleta Lash Adhesive | Borboleta | Makeup Products (non-perm | 90 | Eye Irrit|Repr/Dev|Resp Irrit|Skin Irrit | 1 | 0 |
| 3 | WHITE Borboleta Lash Adhesive | Borboleta | Makeup Products (non-perm | 90 | Eye Irrit|Repr/Dev|Resp Irrit|Skin Irrit | 1 | 0 |
| 4 | Clear Lash Adhesive | Duo | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |
| 5 | Dark Lash Adhesive | Duo | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |
| 6 | Lashgrip Beauty Adhesive | Ardell | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |
| 7 | Lashgrip Beauty Adhesive Clear | Ardell | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |
| 8 | Lashgrip Beauty Adhesive Dark | Ardell | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |
| 9 | SEPHORA - SCLEAN PALETTE PURE DE FARDS � | SEPHORA | Makeup Products (non-perm | 80 | Carc|Eye Irrit|Resp Irrit|STOT-RE | 0 | 1 |
| 10 | Surgical Adhesive | Duo | Makeup Products (non-perm | 80 | Acute Tox|Carc|Muta|Skin Corr|Skin Sens | 1 | 1 |

## Categories with Reproductive / Carcinogen Concerns

| Category | Products | % Repro Hazard | % Carcinogen | Avg Score | Recommendation |
|----------|----------|---------------|-------------|-----------|----------------|
| Bath Products | 1 | 0% | 100% | 30 | HIGH RISK — Most products contain dangerous chemic |
| Fragrances | 2 | 0% | 100% | 30 | HIGH RISK — Most products contain dangerous chemic |
| Hair Coloring Products | 1 | 0% | 100% | 30 | HIGH RISK — Most products contain dangerous chemic |
| Sun-Related Products | 3 | 0% | 100% | 30 | HIGH RISK — Most products contain dangerous chemic |
| Nail Products | 65 | 48% | 97% | 40 | HIGH RISK — Most products contain dangerous chemic |
| Makeup Products (non-permanent) | 40 | 22% | 85% | 42 | HIGH RISK — Most products contain dangerous chemic |
| Hair Care Products (non-coloring) | 5 | 0% | 20% | 23 | MODERATE — Hazard levels are within acceptable ran |
| Skin Care Products  | 22 | 18% | 14% | 23 | MODERATE — Hazard levels are within acceptable ran |

## Hazard Data Coverage Gaps

The following chemicals could not be matched to GHS hazard data:

| Chemical | CASRN | Data Source | Match Confidence | Issue |
|----------|-------|-----------|-----------------|-------|
| trimagnesium;1,3,5,7-tetraoxido-2,4,6,8,9,10- | 14807-96-6 | pubchem_no_ghs | 0.9 | CID found but no GHS classification |
| nan | 68603-42-9 | no_cid_resolved | 0.5 | CAS resolved but no CID |
| Silica, crystalline (airborne particles of re | nan | pubchem_no_ghs | 0.6 | CID found but no GHS classification |
| Mineral oils, untreated and mildly treated | nan | fallback_no_match | 0.0 | No PubChem CID found |
| Talc (powder) | nan | pubchem_no_ghs | 0.6 | CID found but no GHS classification |
| Cocamide diethanolamine | 68603-42-9 | fallback_no_match | 0.0 | No PubChem CID found |

## Regulatory Recommendations

### Immediate Priorities

1. **Formaldehyde-containing products** (CAS 50-00-0) — Classified as a confirmed carcinogen (H350) and mutagen (H341). Found in lash adhesives. Recommend reformulation or enhanced labeling.

2. **Ethyl cyanoacrylate / nail glue products** — Dominant ingredient in nail adhesives. 44 products (32%) contain reproductive toxicants. Recommend consumer exposure assessment.

3. **Styrene-containing products** (CAS 100-42-5) — STOT-RE Category 1 (H372), reproductive suspected (H361). Used in lash adhesives. Monitor for regulatory action.

### Data Quality Improvements

- 6 chemicals (30%) lack GHS data — manual review recommended for: mineral oils, cocamide DEA, talc, crystalline silica
- 17 products (12%) classified as NO_DATA due to insufficient hazard coverage — additional data sourcing may reclassify these

### Next Steps (M2)

- Identify safer chemical alternatives for high-risk ingredients
- Map to FDA/state-level regulatory requirements
- Build automated monitoring for new CSCP product reports
- Develop consumer-facing hazard dashboards

---

*See also:* [M1_hazard_inventory.md](M1_hazard_inventory.md) · [M1_market_trends.md](M1_market_trends.md)
