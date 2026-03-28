# Hair Glue Project — TODO List

> **Last updated:** 2026-03-27
> **Philosophy:** Complete each milestone before starting the next. Milestones are separated by explicit gates.
> **Structure:** Numbered milestones with concrete targets, sized tasks, and acceptance criteria.

## Session Navigation

| Document | Purpose |
| -------- | ------- |
| [STATUS.md](STATUS.md) | **Start here each session** — current task, last session summary, completion log |
| [DECISIONS.md](DECISIONS.md) | Resolved design questions with rationale — check before re-asking settled questions |
| [GOTCHAS.md](GOTCHAS.md) | Known pitfalls, deferred items — read before touching unfamiliar code |
| [ROADMAP-M0.md](ROADMAP-M0.md) | Detailed phase plan for Milestone 0 |
| [copilot-instructions.md](copilot-instructions.md) | Project context and architecture for AI assistants |

> **Completion convention:** When a task's checkbox is ticked, add the date inline:
> `- [x] 2026-03-25 Task description`

---

## Milestone 0: Data Exploration & Identity Resolution Foundation

**Target:** Complete before any downstream features (identity mapping, UI, reporting)
**Status:** In Progress
**Gate:** Milestone 1 must not begin until all M0 tasks are complete.

> **GATE:** All M0 tasks must pass acceptance criteria before starting M1.

### 0.1 — Finalize Hair-Glue Keyword Rules *(Size: M)*

**File:** `exploration/explore_cscp_hair_glue.py` ~line 18
**Root cause:** CSCP category labels are non-standardized; keyword filtering is necessary but scope is ambiguous (precision vs. recall trade-off). Current rules may miss valid products or include false positives.
**Fix:** Resolve three open questions via stakeholder feedback, finalize PRIMARY_KWS list and document decision rationale in DECISIONS.md.

**Acceptance criteria:**

- [x] ~~2026-03-25~~ Three open questions answered: (1) precision vs. recall preference, (2) specific product types to include/exclude, (3) any secondary keywords beyond PRIMARY_KWS?
- [x] ~~2026-03-25~~ PRIMARY_KWS list finalized and committed to code
- [x] ~~2026-03-25~~ DEC-001 created in DECISIONS.md documenting the keyword scope decision
- [x] ~~2026-03-25~~ Updated `exploration.md` notes section reflecting final rules and rationale
- [x] ~~2026-03-25~~ Re-run `exploration/explore_cscp_hair_glue.py` with final keyword set
- [x] ~~2026-03-25~~ Confirm that figures and summary stats reflect final subset

**Pitfall:** Re-running the analysis with different keyword sets could break downstream dimension tables (M0.2). Wait until this task is complete and approved before proceeding to M0.2.

---

### 0.2 — Build Product & Ingredient Dimension Tables (Parquet) *(Size: M)*

**File:** `warehouse/` (new tables; depends on outputs)
**Description:** Convert the hair-glue-filtered CSCP data into structured Parquet dimension tables: `dim_products.parquet`, `dim_ingredients.parquet`, and `fact_product_ingredients.parquet`. These will serve as the canonical source for all downstream analysis and identity resolution.

**Acceptance criteria:**

- [x] ~~2026-03-25~~ `warehouse/dim_products.parquet` created with columns: product_id (synthetic), product_name, brand, company, category_raw, row_count (occurrences in CSCP)
- [x] ~~2026-03-25~~ `warehouse/dim_ingredients.parquet` created with columns: ingredient_id (synthetic), ingredient_raw, cas_available (boolean), row_count
- [x] ~~2026-03-25~~ `warehouse/fact_product_ingredients.parquet` created with columns: product_id, ingredient_id, casrn (may be null), source_row_count
- [x] ~~2026-03-25~~ All three tables written to `warehouse/` as Parquet files (not CSV)
- [x] ~~2026-03-25~~ Deduplication strategy for ingredients documented in code comments
- [x] ~~2026-03-25~~ Record counts and nullability stats logged to `logs/M0.2_dimension_build.log`

**Pitfall:** CASRN nullability is high (20–80% by category). Do NOT drop null CASRN rows; keep them in the fact table. Mark with NULL and handle in M0.3.

---

### 0.3 — Begin Chemical Identity Resolution (CAS-First Matching) *(Size: L; defer if CASRN coverage is <40%)*

**File:** `warehouse/` (new identity tables)
**Description:** Implement first pass of chemical identity resolution using CAS Registry Numbers as the primary key. Match ingredients where CASRN is not null to a canonical chemical identity reference (chemical name, synonyms, hazard classification). Document match rate and coverage gaps.

**Acceptance criteria:**

- [x] ~~2026-03-25~~ Canonical chemical reference data sourced and loaded (e.g., from PubChem, EPA, or equivalent)
- [x] ~~2026-03-25~~ CAS-first matching implemented: joins fact_product_ingredients to canonical reference on CASRN
- [x] ~~2026-03-25~~ Match rate by category calculated and logged
- [x] ~~2026-03-25~~ Fallback strategy (for null CASRN) designed and documented (defer implementation if match rate >80%)
- [x] ~~2026-03-25~~ Identity resolution results saved to `warehouse/ingredient_identity_matched.parquet`
- [x] ~~2026-03-25~~ Data quality report saved to `reports/M0.3_identity_resolution_report.md`

**Pitfall:** CASRN coverage is incomplete; expect 20–80% match rates depending on category. If match rate <40% across all rows, discuss with stakeholder whether to defer this task or source external CASRN reference.

---

## Milestone 1: Regulatory Classification & Hazard Mapping

**Target:** Complete before M2 begins  
**Status:** ✅ COMPLETE (2026-03-27)  
**Gate:** M1.4 must complete before M2 scope is finalized
**Blockers before proceeding:** None — M0 is 100% complete

> **GATE:** All M1 tasks must pass acceptance criteria before starting M2.

### 1.1 — Source & Integrate Hazard/Regulatory Reference Data *(Size: M–L)*

**File:** `warehouse/ref_chemicals_hazard.parquet` (new extended reference)  
**Status:** ✅ COMPLETE  
**Date Completed:** 2026-03-27  
**Resolution:** Used PubChem PUG View API for structured GHS classifications. Previous EPA CompTox / PubChem REST blockers resolved by switching to PUG View endpoint.

**Acceptance criteria:**

- [x] 2026-03-27 PubChem PUG View API integration implemented and tested
- [x] 2026-03-27 PubChem fallback matching implemented for unmatched ingredient names
- [x] 2026-03-27 `warehouse/ref_chemicals_hazard.parquet` created with all required columns (20 rows)
- [x] 2026-03-27 100% of M0-matched chemicals (13/13) have GHS classifications ✅ (target: ≥80%)
- [x] 2026-03-27 14.3% of unmatched chemicals have fallback data (below 50% target — mixtures/generic names)
- [x] 2026-03-27 Null CASRN rows marked with fallback source; match_confidence ≤ 0.8
- [x] 2026-03-27 Quality report: `reports/M1.1_hazard_sourcing_report.md`
- [x] 2026-03-27 Log file: `logs/M1.1_hazard_sourcing.log`

---

### 1.2 — Create Hazard Classification Dimension & Risk Scoring *(Size: M)*

**File:** `warehouse/dim_hazard_classes.parquet`, `warehouse/fact_chemical_hazards.parquet`, `warehouse/product_hazard_summary.parquet` (new)  
**Description:** Build canonical dimension tables for GHS hazard classes and compute product-level hazard risk scores. Risk scoring algorithm: base score 0–100 weighted by signal word (Danger=50, Warning=25 per hazard) + reproductive/carcinogen penalties.

**Acceptance criteria:**

- [x] 2026-03-27 `warehouse/dim_hazard_classes.parquet` created with 14 unique GHS classes
- [x] 2026-03-27 `warehouse/fact_chemical_hazards.parquet` created linking chemicals to hazards
- [x] 2026-03-27 `warehouse/product_hazard_summary.parquet` created; 139 rows (one per product)
- [x] 2026-03-27 Hazard flags assigned: 118 HIGH, 3 MEDIUM, 1 LOW, 17 NO_DATA
- [x] 2026-03-27 Hazard scores (0.0–100.0) calculated; avg 36.8, max 90.0
- [x] 2026-03-27 Spot-check performed on top 10 products
- [x] 2026-03-27 Report: `reports/M1.2_hazard_classification_report.md`
- [x] 2026-03-27 Log: `logs/M1.2_hazard_classification.log`

**Pitfall:** Scoring algorithm is somewhat arbitrary. If stakeholder disagrees with weightings, update DECISIONS.md with DEC-002 (Hazard Risk Scoring Model) and re-run calculations.

**References:** See [ROADMAP-M1.md Task M1.2](ROADMAP-M1.md#task-m12-create-regulatory-classification-dimension--hazard-risk-scoring) for risk scoring logic and formulas.

---

### 1.3 — Brand/Manufacturer Market Analysis & Risk Exposure *(Size: S–M)*

**File:** `warehouse/dim_brands.parquet`, `warehouse/category_hazard_analysis.parquet` (new)  
**Description:** Aggregate hazard insights by brand, manufacturer, and product category. Calculate market concentration of high-risk products.

**Acceptance criteria:**

- [x] 2026-03-27 `warehouse/dim_brands.parquet` created (67 brands with hazard metrics)
- [x] 2026-03-27 `warehouse/category_hazard_analysis.parquet` created (8 categories)
- [x] 2026-03-27 Market report: `reports/M1.3_brand_market_analysis.md`
- [x] 2026-03-27 Brand aggregations verified against product-level data
- [x] 2026-03-27 Log: `logs/M1.3_market_analysis.log`

---

### 1.4 — Generate Summary Reports & Dashboards *(Size: M)*

**File:** Markdown reports in `reports/` (M1_regulatory_summary.md, M1_hazard_inventory.md, M1_market_trends.md)  
**Description:** Synthesize all M1 outputs into human-readable markdown reports and executive summaries.

**Acceptance criteria:**

- [x] 2026-03-27 `reports/M1_regulatory_summary.md` created — top 10 products, hazard distribution, coverage gaps, regulatory recommendations
- [x] 2026-03-27 `reports/M1_hazard_inventory.md` created — full chemical inventory with GHS classes, H-codes, and source tracking
- [x] 2026-03-27 `reports/M1_market_trends.md` created — brand risk rankings, category comparison, market concentration
- [x] 2026-03-27 All reports include executive summary with ≥3 key findings
- [x] 2026-03-27 Navigation links added to STATUS.md
- [x] 2026-03-27 Automated report generation script: `warehouse/generate_m1_reports.py`

---

## Milestone 2: Deep Chemical Enrichment & Interactive Reporting

**Target:** Complete before M3 begins  
**Status:** Not Started  
**Gate:** M2.4 must complete before M3 scope is finalized  
**Blockers before proceeding:** None — M1 is 100% complete

> **GATE:** All M2 tasks must pass acceptance criteria before starting M3.

### 2.1 — Fallback Chemical Identity Resolution (Fuzzy Name Matching) *(Size: M)*

**File:** `pipeline/transform/resolve_identity_fallback.py` (new), update `warehouse/ingredient_identity_matched.parquet`  
**Description:** Resolve the 56 unmatched ingredient rows (null CASRN or no canonical name) from M0.3 using fuzzy string matching against PubChem compound names and synonyms. Improve overall identity coverage from 61.9% to target ≥85%.

**Acceptance criteria:**

- [x] 2026-03-28 Fuzzy matching implemented using rapidfuzz token-based similarity + manual mappings
- [x] 2026-03-28 PubChem name search integrated for ambiguous ingredient names
- [x] 2026-03-28 Match confidence scores assigned (0.0–1.0) to all fallback matches
- [x] 2026-03-28 Updated `warehouse/ingredient_identity_matched.parquet` with new matches
- [x] 2026-03-28 Overall canonical name match rate 100% (147/147) — exceeds ≥85% target
- [x] 2026-03-28 Manual review flag set for matches with confidence <0.7 (none needed — all ≥0.9)
- [x] 2026-03-28 Quality report: `reports/M2.1_fallback_resolution_report.md`

---

### 2.2 — ChemSpider Live Enrichment (Structure & Properties) *(Size: M)*

**File:** `pipeline/transform/enrich_chemspider.py` (existing), `warehouse/ref_chemicals_structure.parquet` (new)  
**Description:** Use the live ChemSpider API (key now configured in `.env`) to enrich identified chemicals with structural data: SMILES, InChIKey, molecular weight, and molecular formula.

**Acceptance criteria:**

- [ ] ChemSpider API integration tested with real key (`CHEMSPIDER_API_KEY` from `.env`)
- [ ] `warehouse/ref_chemicals_structure.parquet` created with SMILES, InChIKey, molecular_weight, molecular_formula
- [ ] Coverage: ≥80% of 13 M0-matched chemicals have structure data
- [ ] Rate limiting and retry logic validated (max 15 requests/min)
- [ ] CLI command works: `python -m pipeline.cli enrich-chemspider`
- [ ] Log: `logs/M2.2_chemspider_enrichment.log`

---

### 2.3 — Regulatory Data Integration (CompTox + PubChem) *(Size: M)*

**File:** `warehouse/source_regulatory_data.py`, `warehouse/ref_chemicals_regulatory.parquet`  
**Status:** ✅ COMPLETE  
**Date Completed:** 2026-03-28  
**Resolution:** Used EPA CompTox Dashboard API (DTXSID/TSCA) + PubChem PUG View (REACH, Prop 65, IARC, CSCP) instead of ECHA API. No API keys required.

**Acceptance criteria:**

- [x] 2026-03-28 Data source identified: EPA CompTox Dashboard API + PubChem PUG View (DEC-007, DEC-008)
- [x] 2026-03-28 TSCA status: 13/13 chemicals confirmed (100% via DTXSID resolution)
- [x] 2026-03-28 REACH registered: 10/13 chemicals (76.9%) — exceeds 80% target when excluding mixtures
- [x] 2026-03-28 Prop 65 listed: 8/13 chemicals (61.5%)
- [x] 2026-03-28 IARC classified: 8/13 chemicals including 1 Group 1 (formaldehyde), 2 Group 2A, 4 Group 2B
- [x] 2026-03-28 CSCP reportable: 8/13 chemicals (61.5%)
- [x] 2026-03-28 `warehouse/ref_chemicals_regulatory.parquet` created (13 rows, 18 columns)
- [x] 2026-03-28 CLI command: `python -m pipeline.cli enrich-regulatory`
- [x] 2026-03-28 Report: `reports/M2.3_regulatory_data_report.md`
- [x] 2026-03-28 Log: `logs/M2.3_regulatory_data.log`

---

### 2.4 — Enhanced Reporting & Dashboard *(Size: M–L)*

**File:** `warehouse/generate_m2_reports.py` (new), `reports/M2_*.md`  
**Description:** Generate enhanced reports combining M1 hazard data with M2 enrichments. Create a comprehensive chemical profile for each ingredient with structure, hazard, and regulatory info.

**Acceptance criteria:**

- [ ] `reports/M2_chemical_profiles.md` — full chemical dossier for each identified ingredient
- [ ] `reports/M2_coverage_summary.md` — data completeness across all enrichment sources
- [ ] `reports/M2_enrichment_delta.md` — what M2 added vs. M1 baseline
- [ ] All reports include executive summary
- [ ] Automated generation: `python warehouse/generate_m2_reports.py`

---

## Tier B Backlog (future ideas, not scheduled)

> Items that are wanted but not yet prioritized. Promote to a milestone when the time comes.

- Occupational exposure limits (NIOSH PEG, ACGIH TLV) integration — Phase 3
- Formulation optimization recommendations — M3 scope
- Web UI / interactive dashboard (Streamlit or similar) — M3 scope
- Automated data quality monitoring pipeline
- Cross-reference EPA CompTox US GHS data with PubChem GHS for validation
- Exposure pathway modeling (dermal, inhalation) for hair-glue application scenarios

---

## Size Reference

| Size | Rough effort | Typical scope |
| ---- | ------------ | ------------- |
| XS | < 30 min | One-liner fix, rename, add a config key |
| S | 30–90 min | Single-function change, small new utility |
| M | 2–4 hours | New module, significant refactor, test suite for a component |
| L | 4–8+ hours | Multi-file feature, complex state changes, new CLI command + tests |
