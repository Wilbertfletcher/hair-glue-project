# Hair Glue Project — ROADMAP for Milestone 0

**Milestone:** M0 — Data Exploration & Identity Resolution Foundation  
**Target:** Complete before M1 begins  
**Owners:** Wilbert Fletcher (primary decision maker)  
**Last Updated:** 2026-03-25

---

## Overview

Milestone 0 establishes the data foundation for the hair-glue analysis project. Three sequential tasks:
1. **M0.1** Finalize keyword rules for hair-glue subset (stakeholder decision)
2. **M0.2** Build canonical dimension tables (product, ingredient, fact) in Parquet format
3. **M0.3** Implement CAS-first chemical identity resolution

This roadmap provides the implementation specs for each task. See `TODO.md` for progress tracking and acceptance criteria.

---

## Agent Primer (Reading List)

Before working on M0, read these files in order:

1. [STATUS.md](STATUS.md) — Current status and blockers (2 min)
2. [GOTCHAS.md](GOTCHAS.md) — Known data quality issues (3 min)
3. [DECISIONS.md](DECISIONS.md) — Prior design decisions (1 min)
4. [copilot-instructions.md](copilot-instructions.md) — Project architecture & constraints (5 min)
5. This file (ROADMAP-M0.md) — Detailed M0 specs ← *You are here*

Total: ~15 min to full context.

---

## Task M0.1: Finalize Hair-Glue Keyword Rules

### Current State

The `exploration/explore_cscp_hair_glue.py` script defines `PRIMARY_KWS` (line 18):
```python
PRIMARY_KWS = [
    "glue", "adhesive", "bond", "bonding",
    "wig", "lace", "weave", "closure", "frontal"
]
```

This produces a subset of ~20k–50k rows from 114k total, depending on filtering strictness.

### Finalized Decisions (2026-03-25)

**1. Precision vs. Recall:** HIGH-PRECISION approach. Keep PRIMARY_KWS strict and accept false negatives. Do NOT expand with vague terms like "hold", "grip", or "sealer" in Phase 1.

**2. Product Scope:** 
- INCLUDE: lace glue, wig glue, bonding glue, weave glue, closure/frontal adhesives, edge control
- EXCLUDE: gels, sprays, pomades, waxes, lash/nail glue, non-cosmetic adhesives

**3. Secondary Keywords / Brands:** Do NOT use brand names or product lines as inclusion criteria. Brands may be analyzed only AFTER subset selection, never for filtering.

**Rationale:** Minimize false positives to preserve interpretability of chemical frequency, functional use mapping, and downstream analysis. Broader recall is Phase 2.

**Updated PRIMARY_KWS:**
```python
PRIMARY_KWS = [
    "glue", "adhesive", "bond", "bonding",
    "wig", "lace", "weave", "closure", "frontal"
]
```

**Note:** Initially tested adding "edge" to capture edge control products, but it matched shaving products (false positives). Removed to maintain high precision. Edge control products without explicit glue terms are acceptable false negatives for Phase 1.

### Acceptance Criteria (To Complete M0.1)

- [ ] Stakeholder provides answers to all 3 questions
- [ ] PRIMARY_KWS list finalized and committed to code
- [ ] Decision documented in `plan/DECISIONS.md` as DEC-001
- [ ] Update `exploration.md` with:
  - Final keyword list and rationale
  - Observed subset size and major category breakdown
  - Any known false positives or negatives discovered during exploration
- [ ] Re-run `exploration/explore_cscp_hair_glue.py` with final keyword set
- [ ] Confirm that figures and summary stats reflect final subset

### Implementation Notes

- **File to modify:** `exploration/explore_cscp_hair_glue.py` (line 18, PRIMARY_KWS list)
- **Plotting is automatic:** The script already generates 8 exploratory plots (bar + pie charts for categories, ingredients, brands, companies)
- **Logging:** Execution logs are saved to `logs/` (create if needed)
- **Deferral:** Do NOT proceed to M0.2 until this task is approved; changes here cascade to downstream tables

---

## Task M0.2: Build Product & Ingredient Dimension Tables

### Overview

Transform the hair-glue-filtered CSCP data (output of M0.1) into normalized, deduplicated Parquet dimension tables suitable for analytics and identity resolution.

### Specification: Three Output Tables

#### 1. `warehouse/dim_products.parquet`

**Purpose:** Canonical product dimension. One row per unique product (across all ingredients).

**Columns:**

| Column | Type | Nullability | Notes |
| ------ | ---- | ----------- | ----- |
| `product_id` | INT64 | NOT NULL | Synthetic surrogate key (1, 2, 3, ...) |
| `product_name` | STRING | NOT NULL | Original product name from CSCP |
| `brand` | STRING | NULLABLE | Brand (or NULL if missing) |
| `company` | STRING | NULLABLE | Manufacturer/company (or NULL if missing) |
| `category_raw` | STRING | NOT NULL | Raw category label from CSCP (non-standardized) |
| `row_count` | INT32 | NOT NULL | How many rows in CSCP reference this product + ingredient combo |

**Index:** product_id (primary key)

**Source:** Generated from filtered CSCP data after M0.1; group by (product_name, brand, company, category_raw) to deduplicate.

#### 2. `warehouse/dim_ingredients.parquet`

**Purpose:** Canonical ingredient dimension. One row per unique ingredient.

**Columns:**

| Column | Type | Nullability | Notes |
| ------ | ---- | ----------- | ----- |
| `ingredient_id` | INT64 | NOT NULL | Synthetic surrogate key (1, 2, 3, ...) |
| `ingredient_raw` | STRING | NOT NULL | Original ingredient name from CSCP |
| `cas_available` | BOOLEAN | NOT NULL | True if any row with this ingredient has non-null CASRN |
| `row_count` | INT32 | NOT NULL | Total CSCP rows for this ingredient (across all products) |

**Index:** ingredient_id (primary key)

**Source:** Generated from filtered CSCP data; group by ingredient_raw; compute cas_available as `any(casrn != NULL AND casrn.strip() != "")`.

#### 3. `warehouse/fact_product_ingredients.parquet`

**Purpose:** Fact table linking products to ingredients with CASRN. One row per (product_id, ingredient_id) pair.

**Columns:**

| Column | Type | Nullability | Notes |
| ------ | ---- | ----------- | ----- |
| `product_id` | INT64 | NOT NULL | Foreign key → dim_products |
| `ingredient_id` | INT64 | NOT NULL | Foreign key → dim_ingredients |
| `casrn` | STRING | NULLABLE | CAS Registry Number (or NULL if missing) |
| `source_row_count` | INT32 | NOT NULL | How many rows in original CSCP had this (product, ingredient, casrn) combo |

**Index:** Composite (product_id, ingredient_id); useful secondary index on casrn for M0.3 join performance.

**Notes:**
- Do NOT drop rows with NULL CASRN; keep them for fallback matching in M0.3
- If the same (product_id, ingredient_id) pair appears with multiple CASRN values in source CSCP (data quality issue), keep the most common one (mode) and log the conflict in `logs/M0.2_dimension_build.log`

### Implementation Steps

1. **Load & Filter:**
   ```python
   df = load_cscp(CSV_PATH)  # Existing function
   glue_df = keyword_filter(df, PRIMARY_KWS)  # Use finalized keywords from M0.1
   ```

2. **Deduplicate & Generate Dimensions:**
   - For dim_products: groupby(product_name, brand, company, category_raw), assign product_id
   - For dim_ingredients: groupby(ingredient_raw), check for CASRN presence, assign ingredient_id
   - For fact table: Inner join filtered CSCP to both dimension tables, keep casrn and source_row_count

3. **Write to Parquet:**
   ```python
   dim_products.to_parquet("warehouse/dim_products.parquet", index=False)
   dim_ingredients.to_parquet("warehouse/dim_ingredients.parquet", index=False)
   fact_table.to_parquet("warehouse/fact_product_ingredients.parquet", index=False)
   ```

4. **Log & Report:**
   - Write `logs/M0.2_dimension_build.log` with row counts and nullability stats
   - Example:
     ```
     [2026-03-XX] M0.2 Dimension Build
     - Rows in filtered CSCP: 42,354
     - Unique products: 1,203
     - Unique ingredients: 485
     - fact table rows: 42,354
     - CASRN coverage: 38.2% (16,221 not NULL)
     - Conflicts resolved: 7 (mode CASRN kept for duplicates)
     ```

### Acceptance Criteria (To Complete M0.2)

- [ ] `warehouse/dim_products.parquet` created with expected schema and row counts
- [ ] `warehouse/dim_ingredients.parquet` created with expected schema and row counts
- [ ] `warehouse/fact_product_ingredients.parquet` created; row count = input rows (no filtering)
- [ ] Foreign key integrity verified (all product_id and ingredient_id in fact table exist in respective dimensions)
- [ ] CASRN coverage stats logged to `logs/M0.2_dimension_build.log`
- [ ] Any data quality conflicts (multiple CASRN per ingredient) documented in log
- [ ] Parquet files confirm via schema inspection (e.g., `import pyarrow.parquet as pq; table = pq.read_table("..."); print(table.schema)`)

### Pitfall: CASRN Nullability

**Expected state:** 20–80% of rows will have NULL CASRN depending on category. This is normal. Do NOT drop these rows; instead, keep them in fact table for future fallback matching. The identity resolution task (M0.3) will handle this.

---

## Task M0.3: Begin Chemical Identity Resolution (CAS-First Matching)

### Overview

Implement the first phase of chemical identity resolution: match hair-glue ingredients by CAS Registry Number to a canonical chemical reference. This yields a mapping of raw ingredient names → standardized chemical identities.

**Note:** This task is sizeable (L) and acceptance criteria depend on CASRN coverage. If CASRN coverage <40% across all rows, discuss with stakeholder whether to defer or source external CASRN reference data.

### Specification

### Phase 1: Canonical Reference Sourcing & Integration

**Goal:** Acquire a reference table of (CASRN, canonical_name, synonyms) to join against CSCP data.

**Options:**

1. **PubChem API** (free, online)
   - Pros: Up-to-date, comprehensive, free
   - Cons: API rate limits; may require batching requests
   - Approach: Call `/rest/v1/compound/lookup/` endpoint with CASRN; cache results locally

2. **EPA Chemical Substitute Finder / CompTox** (free)
   - Pros: Regulatory focus; includes hazard data
   - Cons: Smaller subset; may not cover all CASRN
   - Approach: Download CSV snapshot or use API

3. **Local reference file** (if provided by stakeholder)
   - Sourced from prior database or external vendor
   - Format: CSV with (casrn, name, synonyms, hazard_class)

**Acceptance:** Reference data acquired, deduplicated, and saved to `warehouse/ref_chemicals.parquet` (columns: casrn, canonical_name, synonyms [list or comma-separated], source).

### Phase 2: CAS-First Matching

**Join Logic:**

```
fact_product_ingredients (casrn)
  LEFT JOIN ref_chemicals (casrn)
  → result: product_id, ingredient_id, ingredient_raw, casrn, canonical_name, synonyms
```

**Coverage Metrics:**
- Match rate = (rows with non-null canonical_name) / (total rows with non-null casrn)
- By-category analysis: recalculate match rate grouped by category_raw

**Low Coverage Strategy:**
- If overall match rate <40%: escalate to stakeholder. Options:
  - Proceed with best-effort approach (accept gaps)
  - Source external CASRN mappings (paid or alternative sources)
  - Defer fallback matching (fuzzy name-based) to later phase
- If match rate 40–80%: proceed; document coverage gaps by category
- If match rate >80%: consider deferring fallback matching to M2 (lower priority)

### Phase 3: Output & Reporting

**Output Table:** `warehouse/ingredient_identity_matched.parquet`

**Columns:**

| Column | Type | Nullability | Notes |
| ------ | ---- | ----------- | ----- |
| `product_id` | INT64 | NOT NULL | FK to dim_products |
| `ingredient_id` | INT64 | NOT NULL | FK to dim_ingredients |
| `ingredient_raw` | STRING | NOT NULL | Original CSCP ingredient name |
| `casrn` | STRING | NULLABLE | CAS Number (may be null) |
| `canonical_name` | STRING | NULLABLE | Matched canonical name (null if no match) |
| `synonyms` | STRING | NULLABLE | Alternative names / synonyms |
| `match_source` | STRING | NOT NULL | "pubchem" / "epa" / "local" / "fallback" |

**Report:** `reports/M0.3_identity_resolution_report.md`

**Contents:**
- Executive summary: total rows, match rate %, coverage by category
- Matched sample (first 20 rows of ingredient_identity_matched)
- Coverage gaps: categories with <50% match rate
- Recommendations: whether to defer fallback matching or source external data
- Log of reference source used, date, and version

### Acceptance Criteria (To Complete M0.3)

- [ ] Canonical reference data sourced, deduplicated, saved to `warehouse/ref_chemicals.parquet`
- [ ] CAS-first matching logic implemented and tested on sample data
- [ ] `warehouse/ingredient_identity_matched.parquet` created with all expected columns
- [ ] Row count in matched table = sum of rows from fact_product_ingredients (no filtering)
- [ ] Match rate calculated overall and by category; logged in report
- [ ] `reports/M0.3_identity_resolution_report.md` written with findings & recommendations
- [ ] If match rate <40%: include decision (proceed vs. defer) with stakeholder sign-off

### Pitfall: Incomplete Source Data

If the reference source (e.g., PubChem) is inconsistent with CSCP CASRN format (e.g., CSCP uses "7732-18-5", PubChem expects "7732185"), implement a normalization function:

```python
def normalize_casrn(cas: str) -> str:
    """Normalize CASRN to hyphenated format: XXXXX-XX-X or XX-XX-X"""
    if pd.isna(cas) or cas.strip() == "":
        return None
    cas = cas.strip().replace(" ", "")
    # Match patterns like "7732-18-5" or "773218-5" and normalize
    # Return normalized or None if unrecognized format
    return cas
```

Use this normalization before joining against the reference table.

---

## Rollback & Undo Plan

If M0.2 or M0.3 fail and need to restart:

1. **Delete corrupted outputs:**
   ```bash
   rm warehouse/dim_*.parquet warehouse/fact_*.parquet warehouse/ref_*.parquet warehouse/ingredient_identity_matched.parquet
   rm reports/M0.3_*.md logs/M0.*.log
   ```

2. **Return to previous state:**
   - M0.1 keyword rules: stored in DECISIONS.md; no rollback needed
   - M0.2 dimensions: re-run script with same keywords; deterministic output
   - M0.3 matching: skip until reference data issue is resolved

3. **Document lessons learned:** Add entry to GOTCHAS.md with `RESOLVED:` annotation if resolved, or deferral if deferred.

---

## Success Criteria

M0 is complete when:

1. ✅ Keyword rules finalized (DEC-001 complete)
2. ✅ Dimension tables built and validated (M0.2 all criteria met)
3. ✅ Identity resolution report generated (M0.3 all criteria met, or deferral documented)
4. ✅ STATUS.md updated with completion dates and next steps for M1
5. ✅ GOTCHAS.md includes any new pitfalls or deferrals discovered during M0

---

## Timeline Estimate

| Task | Effort | Duration |
| ---- | ------ | -------- |
| M0.1 (keyword finalization) | M | 2–4 hrs (plus waiting for stakeholder feedback) |
| M0.2 (dimension building) | M | 2–4 hrs (mostly data wrangling & validation) |
| M0.3 (identity resolution) | L | 4–8 hrs (if reference source is well-documented); longer if sourcing is slow |
| **Total** | **M+M+L** | **8–16 hrs** (excluding stakeholder feedback waiting time) |

---

## Next Steps After M0

Once M0 is complete, M1 will focus on:
- Regulatory classification & hazard mapping
- Brand/manufacturer market analysis
- Automated data quality monitoring
- (TBD based on stakeholder feedback)

See Tier B Backlog in [TODO.md](TODO.md) for future scope.
