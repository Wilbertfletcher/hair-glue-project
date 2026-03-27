# Hair Glue Project — ROADMAP for Milestone 1

**Milestone:** M1 — Regulatory Classification & Hazard Mapping  
**Target:** Complete before M2 begins  
**Owners:** Wilbert Fletcher (primary decision maker)  
**Last Updated:** 2026-03-25

---

## Overview

Milestone 1 builds on the M0 data foundation to add regulatory and hazard information. Four sequential tasks:

1. **M1.1** Source and integrate hazard/regulatory reference data (GHS, EPA, ECHA)
2. **M1.2** Map chemicals to hazard classifications and create regulatory dimension table
3. **M1.3** Brand & manufacturer market analysis and risk exposure calculation
4. **M1.4** Generate summary reports and regulatory insights dashboard (markdown)

This roadmap provides the implementation specs for each task. See `TODO.md` for progress tracking.

---

## Prerequisites: What M0 Provides

Before starting M1, verify these M0 outputs exist:

- ✅ `warehouse/ingredient_identity_matched.parquet` (147 rows, 61.9% canonical name match rate)
- ✅ `warehouse/dim_products.parquet` (139 products with brand/company/category)
- ✅ `warehouse/dim_ingredients.parquet` (16 ingredients with CASRN availability flags)
- ✅ `warehouse/fact_product_ingredients.parquet` (147 product-ingredient links)
- ✅ `warehouse/ref_chemicals.parquet` (13 chemicals sourced from PubChem)

**Data Quality Notes:**
- CASRN coverage: 87.8% (129/147 rows)
- Canonical name match rate: 61.9% (91/147 rows — 56 rows have null canonical names, will use fallback)
- 8 product categories represented; Makeup Products (non-permanent) and Nail Products are 75% of dataset

---

## Task M1.1: Source & Integrate Hazard/Regulatory Reference Data

### Overview

Acquire authoritative GHS hazard classifications and regulatory data for the 13 unique chemicals identified in M0.3, plus the 56 unmatched chemicals (using fallback strategies).

### Hazard Data Sources (Evaluated)

#### Primary Sources (Recommended for M0 matched chemicals)

**1. EPA CompTox Dashboard / DTXSID** ⭐ Recommended
- **Coverage:** ~700k chemicals with hazard data
- **Formats:** GHS classifications, hazard phrases (H-codes), pictograms, signal words
- **API:** Available via EPA CompTox API (`https://comptox.epa.gov/dashboard/api/`)
- **Cost:** Free
- **Latency:** Real-time API, no rate limits for research use
- **Integration ease:** Straightforward JSON/REST API
- **Hazard granularity:** GHS hazard classes (acute toxicity, skin/eye irritation, respiratory, reproductive, carcinogenicity, etc.)
- **Recommendation:** Primary source for M1.1 — query by CAS number, retrieve H-codes and pictograms

**2. PubChem Hazard Summaries** ⭐ Secondary (fallback)
- **Coverage:** Similar to CompTox (~680k)
- **Formats:** Text summaries, GHS classifications (embedded in compound records)
- **API:** PubChem PUG REST API (already used in M0.3)
- **Cost:** Free
- **Latency:** Rate-limited but generous (~5 requests/sec)
- **Hazard granularity:** GHS hazard statements, P-codes (precautionary), pictograms
- **Recommendation:** Use for fallback (unmatched chemicals) using ingredient names or fuzzy matching

**3. ECHA (European Chemical Agency)** ⭐ Comprehensive but slower
- **Coverage:** ~20k registered chemicals (REACH database)
- **Formats:** Full GHS hazard classification, exposure routes, toxicological profiles
- **API:** Available via ECHA REACH Substance Information API (`echa.europa.eu/rest`)
- **Cost:** Free
- **Latency:** Slower API responses (1-2 sec); rate limits enforced
- **Hazard granularity:** Most detailed — includes specific concentration limits, reproductive/developmental hazards
- **Recommendation:** Use for high-priority chemicals or regulatory verification (Phase 2)

#### Secondary Sources (Deferred to M1.3+ if needed)

**4. NIOSH Pocket Guide to Chemical Hazards** 
- Coverage: ~600 chemicals
- Updated: Annually
- Format: Text descriptions + hazard classifications
- Recommendation: Reference for occupational exposure limits (OELs)

**5. ATSDR Toxicological Profiles**
- Coverage: ~150 high-priority chemicals
- Detail: Extensive health effects summaries
- Recommendation: For high-risk chemicals found in popular products

#### Not Recommended for M1.1

- **ChemSpider** (now owned by Merck, limited free tier)
- **Material Safety Data Sheets (MSDS)** (inconsistent, manufacturer-specific)
- **Paid databases** (e.g., Scifinder, Chemcats) — defer to M2 if budget allows

### Implementation: Three-Phase Approach

#### Phase 1: Match Hazard Data (For M0-Matched Chemicals, 91 rows)

**Strategy:** Direct CAS lookup using EPA CompTox API

```python
def fetch_epa_hazard_data(casrn: str) -> dict:
    """
    Query EPA CompTox Dashboard for GHS hazard information.
    
    Returns:
        {
            'casrn': str,
            'epa_dtxsid': str (DTXSID identifier),
            'ghs_hazard_class': list (e.g., ["Acute Tox", "Skin Irrit"]),
            'ghs_signal_word': str (e.g., "Danger", "Warning"),
            'h_codes': list (e.g., ["H301", "H315"]),
            'pictograms': list,
            'hazard_summary': str,
            'source': 'epa'
        }
    """
    # Call EPA API endpoint: /dashboard/api/substance/search/box/smiles
    # or /dashboard/SearchResults?search=<casrn>
```

**Acceptance:** 80%+ match rate (≥73 of 91 chemicals)

#### Phase 2: Fallback Hazard Data (For Unmatched/Null Chemicals, 56 rows)

**Strategy:** Fuzzy ingredient name matching against PubChem + ECHA

For each unmatched ingredient (e.g., "Water", "Hexane"):
1. Query PubChem by ingredient_raw name 
2. If multiple matches, score by name similarity + common cosmetic use
3. Return top match + hazard data
4. Flag as "fallback_fuzzy_match" in source field

```python
def fetch_pubchem_hazard_fallback(ingredient_name: str) -> dict:
    """
    Fuzzy match ingredient by name to PubChem compound.
    Returns hazard summaries for best match.
    """
```

**Acceptance:** 50%+ match rate (≥28 of 56 unmatched chemicals)

#### Phase 3: Manual Review / Data Quality (DEFERRED to M1.3)

For chemicals with no match after Phases 1–2, flag for manual review. Consider:
- Proprietary/trade names (require manual lookup)
- Mixtures (not individual chemicals; need component-level analysis)
- Obsolete CASRN or data entry errors

---

### Specification: Output Table

#### `warehouse/ref_chemicals_hazard.parquet`

**Purpose:** Extended chemical reference with hazard classifications. One row per unique chemical.

**Columns:**

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `casrn` | STRING | ✓ | CAS Registry Number (if available) |
| `canonical_name` | STRING | ✓ | From M0.3 identity resolution |
| `ghs_hazard_class` | STRING | ✓ | Pipe-separated GHS classes (e.g., "Acute Tox\|Skin Irrit\|Eye Irrit") |
| `ghs_signal_word` | STRING | ✓ | "Danger" or "Warning" |
| `h_codes` | STRING | ✓ | Pipe-separated H-codes (e.g., "H301\|H315\|H319") |
| `p_codes` | STRING | ✓ | Pipe-separated P-codes (precautionary) |
| `pictograms` | STRING | ✓ | Pipe-separated pictogram names (e.g., "Exclamation\|Corrosion") |
| `hazard_summary` | STRING | ✓ | Text description of primary hazards |
| `acute_tox_oral` | STRING | ✓ | Acute toxicity (oral route); e.g., "Category 3", "Category 4" |
| `acute_tox_dermal` | STRING | ✓ | Acute toxicity (dermal route) |
| `skin_irritation` | STRING | ✓ | Skin irritation category (1–2) or None |
| `eye_irritation` | STRING | ✓ | Eye irritation category (1–2A–2B) or None |
| `reproductive_hazard` | BOOLEAN | NOT NULL | True if any reproductive/developmental hazard present |
| `carcinogenicity` | STRING | ✓ | "Suspected" / "Probable" / "Confirmed" or None |
| `data_source` | STRING | NOT NULL | "epa_comptox" / "pubchem" / "echa" / "fallback_fuzzy" |
| `match_confidence` | FLOAT | NOT NULL | 0.0–1.0; 1.0 = exact CAS match via EPA, <1.0 = fuzzy match |
| `hazard_url` | STRING | ✓ | Link to authoritative source (EPA dashboard, PubChem, ECHA) |

**Indexes:** 
- Primary: `casrn` (join key with fact table)
- Secondary: `data_source` (for filtering by confidence)

---

### Acceptance Criteria (To Complete M1.1)

- [ ] EPA CompTox API integration implemented and tested on sample chemical
- [ ] PubChem fallback matching implemented for unmatched ingredient names
- [ ] `warehouse/ref_chemicals_hazard.parquet` created with all required columns
- [ ] ≥80% of M0-matched chemicals (≥73/91) have GHS classifications
- [ ] ≥50% of unmatched chemicals (≥28/56 null casrn rows) have fallback hazard data
- [ ] Null CASRN rows marked with fallback source; match_confidence ≤ 0.8
- [ ] Quality report: `reports/M1.1_hazard_sourcing_report.md` with match rates and coverage gaps
- [ ] Log file: `logs/M1.1_hazard_sourcing.log` with API call summaries and failures

---

## Task M1.2: Create Regulatory Classification Dimension & Hazard Risk Scoring

### Overview

Transform hazard reference data into a regulatory classification dimension table and compute risk exposure for each product.

### Specification: Output Tables

#### 1. `warehouse/dim_hazard_classes.parquet`

**Purpose:** Canonical hazard classification dimension. One row per GHS hazard class.

**Columns:**

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `hazard_id` | INT64 | NOT NULL | Synthetic key (1, 2, ...) |
| `hazard_class` | STRING | NOT NULL | GHS class name (e.g., "Acute Tox", "Skin Irrit") |
| `hazard_category` | STRING | NOT NULL | Category (e.g., "1", "2", "3–4") |
| `signal_word` | STRING | NOT NULL | "Danger" or "Warning" |
| `definition` | STRING | NOT NULL | Definition/description of hazard |
| `target_organs` | STRING | ✓ | Comma-separated (e.g., "respiratory system, nervous system") |

**Index:** Primary `hazard_id`; secondary on `hazard_class`

#### 2. `warehouse/fact_chemical_hazards.parquet`

**Purpose:** Bridge table linking chemicals to hazard classes. Many-to-many relationship.

**Columns:**

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `chemical_id` | INT64 | NOT NULL | FK to ref_chemicals_hazard via casrn or ingredient_raw |
| `hazard_id` | INT64 | NOT NULL | FK to dim_hazard_classes |
| `ghs_h_code` | STRING | ✓ | Specific H-code (e.g., "H301") |
| `ghs_p_code` | STRING | ✓ | Corresponding P-code (e.g., "P301+P310") |
| `source_data` | STRING | NOT NULL | "epa_comptox" / "pubchem" / "fallback" |

**Index:** Composite `(chemical_id, hazard_id)`

#### 3. `warehouse/product_hazard_summary.parquet`

**Purpose:** Aggregated hazard summary per product. One row per product_id.

**Columns:**

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `product_id` | INT64 | NOT NULL | FK to dim_products |
| `product_name` | STRING | NOT NULL | Product name (denormalized for reporting) |
| `num_ingredients` | INT32 | NOT NULL | Count of unique ingredients in product |
| `num_hazardous_ingredients` | INT32 | NOT NULL | Count with →any← GHS hazard |
| `max_hazard_severity` | STRING | ✓ | Highest severity hazard → ("Danger" > "Warning" > None) |
| `hazard_classes_present` | STRING | ✓ | Pipe-separated unique GHS classes (e.g., "Acute Tox\|Skin Irrit") |
| `reproductive_hazard_ingredient_count` | INT32 | NOT NULL | Count of ingredients with reproductive/developmental hazard |
| `carcinogen_count` | INT32 | NOT NULL | Count of suspected/confirmed carcinogens |
| `hazard_flag` | STRING | NOT NULL | "HIGH" / "MEDIUM" / "LOW" / "NO_DATA" (see scoring below) |
| `hazard_score` | FLOAT | NOT NULL | 0.0–100.0; calculated risk exposure (see formula) |

**Index:** Primary `product_id`

---

### Risk Scoring Logic

**Hazard Flag:**
```
HIGH      if max_severity = "Danger" OR reproductive_count > 0 OR carcinogen_count > 0
MEDIUM    if max_severity = "Warning" AND no reproductive/carcinogen hazards
LOW       if num_hazardous_ingredients = 0 and match_confidence > 0.8
NO_DATA   if match_confidence < 0.5 (high fuzzy match; unreliable)
```

**Hazard Score (0.0–100.0):**
```
Base:         0.0
+ If "Danger" signal word: +50 per hazard
+ If "Warning" signal word: +25 per hazard
+ If reproductive hazard: +15 per chemical
+ If carcinogen (suspected): +10
+ If carcinogen (confirmed): +20
- If high match_confidence (≥0.9): -5 (confidence bonus)
+ If low match_confidence (<0.5): +10 (uncertainty penalty)

Capped at 100
```

**Example:**
- Product A: 5 ingredients, 3 with "Danger" (Acute Tox), 1 with reproductive hazard
  - Score = 50×3 + 15×1 = 165 → capped at 100 (HIGH)
- Product B: 3 ingredients, all "Warning" (Skin Irrit), no special hazards
  - Score = 25×3 = 75 (MEDIUM)
- Product C: 2 ingredients, both matched via fallback, no hazard data
  - Score = 0 + 10 = 10 (LOW, but flagged NO_DATA)

---

### Acceptance Criteria (To Complete M1.2)

- [ ] `warehouse/dim_hazard_classes.parquet` created with all GHS classes present in data
- [ ] `warehouse/fact_chemical_hazards.parquet` created linking all chemicals to hazards
- [ ] `warehouse/product_hazard_summary.parquet` created with 139 products (one per dim_products)
- [ ] Hazard flags and scores calculated for all rows
- [ ] Manual spot-check: 10 random products, hazard scores validated against source data
- [ ] Report: `reports/M1.2_hazard_classification_report.md` with hazard distribution statistics
- [ ] Log: `logs/M1.2_hazard_classification.log` with calculation summaries

---

## Task M1.3: Brand/Manufacturer Market Analysis & Risk Exposure

### Overview

Analyze product distribution by brand, manufacturer, and category. Calculate aggregate risk exposure metrics.

### Specification: Output Tables

#### 1. `warehouse/dim_brands.parquet`

**Purpose:** Canonical brand dimension.

**Columns:**
- `brand_id` (synthetic key)
- `brand_name` (from dim_products.brand)
- `company` (from dim_products.company)
- `product_count` (unique products from this brand)
- `avg_hazard_score` (average of product_hazard_summary.hazard_score)
- `max_hazard_flag` (worst flag present: HIGH > MEDIUM > LOW > NO_DATA)

#### 2. `warehouse/category_hazard_analysis.parquet`

**Purpose:** Hazard statistics aggregated by product category.

**Columns:**
- `category_raw` (category from dim_products)
- `product_count`
- `avg_hazard_score`
- `pct_high_hazard` (% with hazard_flag = "HIGH")
- `pct_reproductive_hazard`
- `pct_carcinogen`
- `most_common_hazard_class` (e.g., "Skin Irrit")
- `recommendation` (text summary)

### Acceptance Criteria (To Complete M1.3)

- [ ] Brand dimension and market analysis tables created
- [ ] Aggregate statistics calculated for all categories
- [ ] Market report: `reports/M1.3_brand_market_analysis.md` with top risky brands/categories
- [ ] Risk exposure dashboard data prepared for M1.4

---

## Task M1.4: Summary Reports & Dashboards

### Overview

Synthesize M1.1–M1.3 outputs into markdown reports and data-driven dashboards.

### Outputs

1. **`reports/M1_regulatory_summary.md`**
   - High-level findings: total products, categories, hazard distribution
   - Top 10 highest-risk products
   - Categories with reproductive/carcinogen concerns
   - Gaps in hazard data coverage
   - Regulatory recommendations (e.g., products needing reformulation)

2. **`reports/M1_hazard_inventory.md`**
   - Detailed chemical inventory with GHS classifications
   - Sortable table: ingredient_raw → canonical_name → hazard_class → H-codes → data_source
   - Coverage statistics: % with EPA vs. PubChem vs. fallback data

3. **`reports/M1_market_trends.md`**
   - Brand/company market analysis
   - Risk concentration: which brands use highest-hazard chemicals
   - Category-level insights: nail products vs. makeup vs. hair care (hazard comparison)

### Acceptance Criteria (To Complete M1.4)

- [ ] All three markdown reports generated with tables and summaries
- [ ] Reports include data visualizations (can be static images or embedded tables)
- [ ] Navigation links between reports in STATUS.md
- [ ] Automated report generation script created for future updates

---

## Success Criteria (M1 Complete)

1. ✅ Hazard data sourced & integrated (M1.1)
2. ✅ Regulatory dimension tables built (M1.2)
3. ✅ Brand/category analysis complete (M1.3)
4. ✅ Summary reports generated (M1.4)
5. ✅ STATUS.md updated with M1 completion dates
6. ✅ GOTCHAS.md updated with new pitfalls (e.g., unmatched hazard data)

---

## Timeline Estimate

| Task | Effort | Duration |
|------|--------|----------|
| M1.1 (hazard data sourcing) | M–L | 3–6 hrs (API integration + data validation) |
| M1.2 (classification & scoring) | M | 2–4 hrs (dimension building + calculations) |
| M1.3 (market analysis) | S–M | 1–3 hrs (aggregations + statistical calcs) |
| M1.4 (reporting) | M | 2–4 hrs (markdown generation + polish) |
| **Total** | **M–L** | **8–17 hrs** |

---

## Dependencies & Blockers

- **Blocker:** M0 must be 100% complete before M1.1 starts
- **Dependency:** M1.1 hazard sourcing must complete before M1.2 classification
- **Optional:** M1.3 (brand analysis) can run in parallel with M1.2 once product_{hazard}_summary exists

---

## Failure Modes & Mitigation

| Risk | Mitigation |
|------|-----------|
| EPA API rate limits or downtime | Use PubChem as fallback; cache results locally |
| Low fallback match rate (<50%) | Escalate to stakeholder; consider manual lookup of high-priority chemicals |
| Conflicting hazard data across sources | EPA CompTox is primary; log discrepancies in report |
| Unmatched chemicals (56 null CASRN rows) | Flag as NO_DATA; don't force matches; document coverage gaps |

---

## Next Steps After M1

Once M1 is complete, M2 will focus on:
- **Formulation optimization:** Recommend safer alternatives for high-risk chemicals
- **Regulatory compliance:** Map to relevant laws (EC, FDA, state-level restrictions)
- **UI/Dashboard:** Web interface for browsing products and hazards
- **Automated monitoring:** Pipeline for tracking new CSCP reports and hazard updates

See Tier B Backlog in [TODO.md](TODO.md) for future scope.
