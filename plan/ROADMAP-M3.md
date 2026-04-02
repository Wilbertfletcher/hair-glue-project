# Hair Glue Project — ROADMAP for Milestone 3

**Milestone:** M3 — EPA Data Integration, Exposure Analysis & Public Report  
**Target:** Complete before thesis submission  
**Owners:** Wilbert Fletcher (primary decision maker)  
**Last Updated:** 2026-04-02

---

## Overview

Milestone 3 builds on the complete chemical identity and hazard foundation from M0–M2
to answer the central thesis question: **Are Black women and girls disproportionately
exposed to dangerous chemicals through hair-glue and weaving-adhesive products?**

M3 has four sequential tasks:

1. **M3.1** Pull live data from EPA tools (ToxCast, CompTox, ChemExpo, OPERA) to fill
   remaining safety data gaps and add bioactivity + exposure context per chemical.
2. **M3.2** Exposure and demographics analysis — link product danger scores to the
   consumer populations most likely to use these products.
3. **M3.3** Comparative benchmarking — compare hair-glue chemical hazards against other
   cosmetic categories in the full CSCP dataset to quantify the disparity.
4. **M3.4** Public-facing executive report and policy recommendations — the thesis
   conclusion chapter, backed by all data collected in M0–M3.

---

## Prerequisites: What M0–M2 Provide

| Output | Rows | Status |
|--------|------|--------|
| `warehouse/dim_products.parquet` | 139 products | ✅ |
| `warehouse/dim_ingredients.parquet` | 16 ingredients | ✅ |
| `warehouse/fact_product_ingredients.parquet` | 147 rows | ✅ |
| `warehouse/ref_chemicals.parquet` | 13 chemicals | ✅ |
| `warehouse/ingredient_identity_matched.parquet` | 147 rows, 100% match | ✅ |
| `warehouse/ref_chemicals_hazard.parquet` | GHS hazard data (PubChem) | ✅ |
| `warehouse/ref_chemicals_regulatory.parquet` | TSCA, REACH, Prop 65, IARC | ✅ |
| `warehouse/ref_chemicals_reach.parquet` | ECHA REACH registration | ✅ |
| `warehouse/product_hazard_summary.parquet` | 139 products w/ danger scores | ✅ |
| `warehouse/dim_brands.parquet` | 67 brands | ✅ |
| `warehouse/category_hazard_analysis.parquet` | 8 product types | ✅ |

**Key gaps M3 addresses:**

- No ToxCast bioactivity data (how many lab tests did each chemical trigger?)
- No predicted toxicity for chemicals with incomplete GHS data (GenRA/OPERA gap-fill)
- No consumer exposure estimates (ChemExpo national exposure context)
- No demographic linkage (who uses these products?)
- No cross-category comparison (are hair-glue products worse than other cosmetics?)
- No synthesized public-facing conclusion document

---

## Task M3.1: EPA Tool Data Integration

### Problem

The EPA Tools page in the dashboard currently shows explanations and a live API demo,
but no EPA tool data is stored in the warehouse. Chemicals with missing GHS data have
no safety prediction fallback. We cannot yet show "this chemical triggered X out of
1,500 ToxCast tests" or "nationally, consumers are exposed to X µg/day of this chemical."

### Sub-tasks

#### M3.1a — CompTox Chemical Detail (structure + predicted properties)

**API:** `https://api-ccte.epa.gov/chemical/detail/search/by-dtxsid/{dtxsid}`

For each chemical in `ref_chemicals_regulatory.parquet` that has a DTXSID:
- Fetch: `preferredName`, `smiles`, `inchiKey`, `molecularFormula`, `monoisotopicMass`
- Store in `warehouse/ref_chemicals_comptox.parquet`
- Join into Chemical Database page for structure display

**Rate limit:** CCTE API is free with no key for basic detail endpoints; 
request a free key at `api-ccte.epa.gov` for higher-volume endpoints.

#### M3.1b — ToxCast Bioactivity Scores

**API:** `https://api-ccte.epa.gov/bioactivity/data/search/by-dtxsid/{dtxsid}`

For each DTXSID, fetch:
- Total assays tested against
- Number of assays with an "active" hit
- Hit ratio (active / tested) — this is the **ToxCast Activity Score**
- Endpoint categories hit (e.g., nuclear receptor, stress response, cell viability)

Store in `warehouse/ref_chemicals_toxcast.parquet`:

| Column | Type | Description |
|--------|------|-------------|
| dtxsid | str | Join key |
| casrn | str | CAS number |
| assays_tested | int | Total assays run against this chemical |
| assays_active | int | Number that returned an active hit |
| activity_score | float | assays_active / assays_tested (0–1) |
| top_hit_categories | str | Pipe-delimited list of biological endpoint categories |
| data_source | str | "toxcast_ccte_api" |
| fetched_at | datetime | Timestamp |

Add `activity_score` to the Chemical Database page as **"ToxCast Biological Activity Score"**
with plain-language label: *"X out of Y lab tests found this chemical was biologically active."*

#### M3.1c — ChemExpo Consumer Exposure Data

**API:** `https://api-ccte.epa.gov/exposure/product/search/by-dtxsid/{dtxsid}`

For each DTXSID, fetch:
- Consumer product categories where this chemical appears nationally
- Functional use (e.g., preservative, fragrance, solvent, adhesive)
- Number of products nationally containing this chemical

Store in `warehouse/ref_chemicals_chemexpo.parquet`:

| Column | Type | Description |
|--------|------|-------------|
| dtxsid | str | Join key |
| casrn | str | CAS number |
| product_categories | str | Pipe-delimited list of product types |
| functional_use | str | Primary use (e.g., preservative) |
| national_product_count | int | How many products nationally contain it |
| data_source | str | "chemexpo_ccte_api" |
| fetched_at | datetime | Timestamp |

Display in Chemical Database page as: *"Found in X products nationally across these
product types."*

#### M3.1d — OPERA Predictions for Data-Gap Chemicals

For chemicals with no GHS signal word (i.e., `ghs_signal_word IS NULL` in
`ref_chemicals_hazard.parquet`), pull OPERA model predictions from the CompTox
bulk download or API.

**Bulk download approach (preferred — avoids rate limits):**
1. Download `OPERA_models.csv` from
   `https://comptox.epa.gov/dashboard/downloads` → "OPERA 2.9 models"
2. Filter to our DTXSIDs
3. Extract: `LogBCF_pred` (bioaccumulation), `LogKow_pred` (fat solubility),
   `ReadAcuteTox_pred` (acute toxicity), `Carcino_pred` (carcinogenicity probability)

Store in `warehouse/ref_chemicals_opera.parquet`.

**Plain-language use:** For chemicals missing GHS data, show a predicted danger level
derived from OPERA instead of "Not Enough Data."

### Implementation files

```
pipeline/extract/ccte_api.py          # New: CCTE API client (CompTox, ToxCast, ChemExpo)
warehouse/source_epa_data.py          # New: orchestrates M3.1a–c API fetches
warehouse/source_opera_predictions.py # New: loads OPERA bulk CSV
```

### Acceptance Criteria

- `ref_chemicals_comptox.parquet` exists with ≥10 chemicals enriched
- `ref_chemicals_toxcast.parquet` exists with ToxCast scores for all DTXSID-matched chemicals
- `ref_chemicals_chemexpo.parquet` exists with exposure context for ≥8 chemicals
- Dashboard EPA Tools page live demo shows real fetched data, not just a button
- Chemical Database page shows ToxCast score and ChemExpo product count per chemical

---

## Task M3.2: Exposure & Demographics Analysis

### Problem

The dashboard shows which products are dangerous but not **who is most affected**.
Hair-glue and weaving-adhesive products are used disproportionately by Black women
and girls. Linking hazard data to demographics is the core thesis argument.

### Data Sources

| Source | What it provides | How to get it |
|--------|-----------------|---------------|
| CSCP `SubCategory` field | Age/gender targeting clues (e.g., "Children", "For Kids") | Already in raw CSCP CSV |
| Product name text mining | Consumer targeting signals (e.g., "girl", "kids", "men") | Parse `product_name` in dim_products |
| Mintel / Statista market data | % of Black women who use hair extensions/weave products | Manual citation — report only |
| EWG Skin Deep / CSCP brand notes | Brand demographic positioning | Manual + web research |
| U.S. Census + ACS data | Population demographics for exposure calculation | Public download |

### Analysis Steps

1. **Age targeting flag** — scan product names and categories for child-targeting signals.
   Flag products marketed at or suitable for children as `child_marketed = True`.

2. **Category demographic linkage** — create `dim_demographics.parquet`:

| Column | Type | Description |
|--------|------|-------------|
| category_raw | str | Product type (join key) |
| primary_demographic | str | e.g., "Black women", "Girls", "General" |
| market_share_black_women_pct | float | % of U.S. users who are Black women (cited) |
| citation | str | Source of demographic estimate |
| child_use_flag | bool | Commonly used on children? |

3. **Exposure burden score** — for each product type, calculate:
   ```
   exposure_burden = avg_hazard_score × market_share_black_women_pct
   ```
   This produces a single number summarizing demographic-weighted chemical risk.

4. **Disparity index** — compare hair-glue exposure burden to average across all
   CSCP cosmetic categories (requires M3.3 benchmarking data).

5. **Dashboard page: "Who Is Affected?"** — new page in app.py showing:
   - Bar chart: Exposure burden by product type
   - Callout: "X% of hair-glue product users are Black women or girls"
   - Table: Products marketed to children that contain HIGH-danger chemicals
   - Context: Why this matters (plain-language explanation)

### Acceptance Criteria

- `warehouse/dim_demographics.parquet` created with demographic estimates and citations
- At least 3 product categories have demographic linkage
- Dashboard has a new "Who Is Affected?" page
- Child-marketed HIGH-danger products are explicitly flagged

---

## Task M3.3: Comparative Benchmarking

### Problem

We cannot claim hair-glue products are *disproportionately* dangerous without
comparing them to other cosmetic categories. M3.3 runs the same hazard pipeline
on a broader CSCP slice and compares results.

### Approach

1. **Expand CSCP extraction** — run `pipeline/extract/cscp.py` without the
   hair-glue keyword filter to get all cosmetic product categories.
   Filter to categories with ≥50 products for statistical validity.

2. **Sample-based hazard comparison** — for each broad category
   (e.g., Skin Care, Nail Products, Hair Coloring, Shampoo, Makeup):
   - Pull all CASRNs from CSCP
   - Join to `ref_chemicals_hazard.parquet` to get GHS classifications
   - Compute: avg_hazard_score, pct_carc, pct_repro_hazard

   Store in `warehouse/benchmark_categories.parquet`.

3. **Disparity ratio** — for each metric:
   ```
   disparity_ratio = hair_glue_value / all_categories_mean
   ```
   A ratio > 1.5 is a "meaningful disparity"; > 2.0 is a "strong disparity."

4. **Dashboard page: "How Does Hair Glue Compare?"** — new page showing:
   - Grouped bar chart: hair-glue vs. top 10 cosmetic categories across 3 metrics
   - Disparity ratio callouts (e.g., "Hair-glue products are 2.3× more likely to
     contain a cancer-causing chemical than the average cosmetic")
   - Statistical note on sample sizes

### Implementation

```
warehouse/build_benchmark.py   # New: runs comparison pipeline
```

### Acceptance Criteria

- `benchmark_categories.parquet` covers ≥8 cosmetic categories
- Hair-glue disparity ratios calculated for: avg danger score, % carcinogen, % repro hazard
- Dashboard "How Does Hair Glue Compare?" page is live
- At least one disparity ratio is ≥ 1.5 (expected based on M1 findings)

---

## Task M3.4: Public-Facing Report & Policy Recommendations

### Problem

All analysis exists only in the dashboard and Parquet files. The thesis requires
a clean written document that a non-technical reader (policymaker, journalist,
community advocate) can read and act on.

### Deliverables

#### 1. `reports/M3_executive_summary.md`

Structure:
- **The Problem** (1 paragraph, plain language)
- **What We Found** (5 key findings as bullet points with numbers)
- **Who Is Most At Risk** (demographics section)
- **How Hair Glue Compares to Other Products** (disparity ratios from M3.3)
- **The Chemicals of Greatest Concern** (top 5 chemicals by danger + prevalence)
- **What Should Be Done** (policy recommendations — see below)
- **Methodology Note** (one paragraph for credibility)

#### 2. `reports/M3_policy_recommendations.md`

Recommendations to draft (confirm scope with stakeholder):
1. **FDA labeling reform** — require plain-language danger warnings on hair-glue packaging
2. **CSCP reporting expansion** — require all hair-glue brands to report all ingredients
   (not just those above thresholds)
3. **EPA priority review** — flag the top 5 chemicals for expedited TSCA review
4. **Consumer advisory** — draft a 1-page consumer fact sheet (plain language, shareable)
5. **Research gap** — call for funded biomonitoring studies in Black communities

#### 3. `reports/M3_consumer_factsheet.md`

A single page written at a 6th-grade reading level:
- What are hair-glue products?
- What dangerous chemicals did we find?
- What does this mean for me and my family?
- What can I do right now? (practical tips)
- Where to get more information

#### 4. Dashboard update — "Report" page

Add a final page to app.py that renders the executive summary and links to
all report files for download.

### Acceptance Criteria

- All three report files exist in `reports/`
- Executive summary is ≤ 4 pages when rendered
- Policy recommendations are specific and actionable (not vague)
- Consumer fact sheet passes Flesch-Kincaid reading level ≤ 7th grade
- Dashboard has a "Report" page

---

## Recommended Task Order

```
M3.1 (EPA Data)  →  M3.2 (Demographics)  →  M3.3 (Benchmarking)  →  M3.4 (Report)
     ↓                      ↓                        ↓
fills data gaps      adds who is harmed        proves disparity        tells the story
```

M3.1 feeds M3.2 (ToxCast scores strengthen the demographics argument).
M3.2 + M3.3 together provide the evidence base for M3.4.

---

## New Dashboard Pages Summary

| Page | Task | What it shows |
|------|------|---------------|
| EPA Research Tools *(already built)* | M3.1 | Live CompTox/ToxCast lookup |
| Who Is Affected? | M3.2 | Demographics + child-marketing flags |
| How Does Hair Glue Compare? | M3.3 | Benchmarking vs. other cosmetics |
| Report | M3.4 | Executive summary + download links |

---

## New Warehouse Files

| File | Created by | Contents |
|------|-----------|----------|
| `ref_chemicals_comptox.parquet` | M3.1a | CompTox structure + properties |
| `ref_chemicals_toxcast.parquet` | M3.1b | ToxCast bioactivity scores |
| `ref_chemicals_chemexpo.parquet` | M3.1c | ChemExpo exposure data |
| `ref_chemicals_opera.parquet` | M3.1d | OPERA predicted toxicity |
| `dim_demographics.parquet` | M3.2 | Demographic linkage per category |
| `benchmark_categories.parquet` | M3.3 | Cross-category hazard comparison |

---

## Open Decisions

| # | Decision | Options | Owner |
|---|----------|---------|-------|
| DEC-010 | Which demographic data source to use for market share estimates | Mintel report (paid), Statista, literature review, or manual citation | Wilbert |
| DEC-011 | CCTE API key — apply for free key or use unauthenticated endpoints only | Apply at api-ccte.epa.gov (free, ~1 business day) | Wilbert |
| DEC-012 | OPERA data — bulk CSV download vs. API | Bulk download preferred (avoids rate limits) | Wilbert |
| DEC-013 | Report audience — academic thesis committee only, or also community/policy | Affects tone, reading level, and length of M3.4 deliverables | Wilbert |
