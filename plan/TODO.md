# Hair Glue Project — TODO List

> **Last updated:** 2026-03-25
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
**Status:** Ready to start (M0 complete)  
**Gate:** M1.4 must complete before M2 scope is finalized
**Blockers before proceeding:** None — M0 is 100% complete

> **GATE:** All M1 tasks must pass acceptance criteria before starting M2.

### 1.1 — Source & Integrate Hazard/Regulatory Reference Data *(Size: M–L)*

**File:** `warehouse/ref_chemicals_hazard.parquet` (new extended reference)  
**Status:** 🟡 IN PROGRESS — Framework complete, BLOCKED on US hazard data source integration  
**Date Started:** 2026-03-25  
**Root cause:** M0 matched 91 chemicals successfully (61.9% match rate) but left 56 rows with null canonical_name. Need GHS hazard classifications from authoritative sources to enable regulatory risk analysis.

**✅ COMPLETED:**
- Designed and implemented M1.1 infrastructure script: `warehouse/source_hazard_data.py`
- Attempted EPA CompTox API integration (API structure not accessible)
- Attempted PubChem fallback strategy implementation
- Created `warehouse/ref_chemicals_hazard.parquet` with correct schema: casrn, canonical_name, ghs_hazard_class, ghs_signal_word, h_codes, p_codes, pictograms, hazard_summary, acute_tox_*, reproductive_hazard, carcinogenicity, data_source, match_confidence, hazard_url
- Generated `reports/M1.1_hazard_sourcing_report.md` quality metrics template
- Logged execution trace: `logs/M1.1_hazard_sourcing.log`
- Documented blocker in GOTCHAS.md and STATUS.md
- Cleaned up all unnecessary Python virtual environments; unified on .venv
- Installed and tested GHScrunch; confirmed it does not support US data out of the box

**❌ BLOCKED:**
- US GHS hazard data not natively supported by GHScrunch; requires external dataset (e.g., EPA CompTox Dashboard CSV)
- EPA CompTox public APIs do not reliably provide structured GHS classifications
- PubChem does not return GHS data in structured format via REST API
- Hazard reference table created but all hazard columns remain NULL

**TO COMPLETE M1.1:**
- [ ] Download EPA CompTox GHS hazard CSV (or equivalent US dataset) and place in data/raw/
- [ ] Write/extend script to join hazard data to chemical dimension by CASRN
- [ ] Register for ECHA and ChemSpider API keys if not already done
- [ ] Test ECHA hazard enrichment with real data: `python -m pipeline.cli enrich-hazards`
- [ ] Test ChemSpider structure enrichment with real data: `python -m pipeline.cli enrich-chemspider`
- [ ] Create DEC-004 (Hazard Data Source Resolution) documenting final choice
- [ ] Modify `warehouse/source_hazard_data.py` with chosen data source integration
- [ ] Re-run M1.1 script with working API integration
- [ ] Populate `warehouse/ref_chemicals_hazard.parquet` with actual hazard data
- [ ] Verify ≥80% M0-matched coverage, ≥50% unmatched coverage
- [ ] Confirm report reflects actual hazard statistics

**Pitfall:** Free public APIs have significant limitations. Hazard classification data is expensive and tightly controlled. Budget and licensing must be considered.

**References:**
- [GOTCHAS.md — EPA CompTox & PubChem Limitation](GOTCHAS.md#epa-comptox--pubchem-apis-have-inconsistent-hazard-data-endpoints--discovered-m11)
- [ROADMAP-M1.md Task M1.1](ROADMAP-M1.md#task-m11-source--integrate-hazard-regulatory-reference-data)
- `warehouse/source_hazard_data.py` — Ready for data source plug-in

---

### 1.2 — Create Hazard Classification Dimension & Risk Scoring *(Size: M)*

**File:** `warehouse/dim_hazard_classes.parquet`, `warehouse/fact_chemical_hazards.parquet`, `warehouse/product_hazard_summary.parquet` (new)  
**Description:** Build canonical dimension tables for GHS hazard classes and compute product-level hazard risk scores. Risk scoring algorithm: base score 0–100 weighted by signal word (Danger=50, Warning=25 per hazard) + reproductive/carcinogen penalties.

**Acceptance criteria:**

- [ ] `warehouse/dim_hazard_classes.parquet` created with all unique GHS classes found in ref_chemicals_hazard
- [ ] `warehouse/fact_chemical_hazards.parquet` created linking chemicals to hazards (many-to-many bridge table)
- [ ] `warehouse/product_hazard_summary.parquet` created; one row per product_id (139 rows)
- [ ] Hazard flags ("HIGH" / "MEDIUM" / "LOW" / "NO_DATA") assigned to all products per scoring rules
- [ ] Hazard scores (0.0–100.0) calculated for all products
- [ ] Manual spot-check: 10 random products, hazard scores validated against source data
- [ ] Report: `reports/M1.2_hazard_classification_report.md` with hazard distribution histograms and category breakdowns
- [ ] Log: `logs/M1.2_hazard_classification.log` with calculation summaries

**Pitfall:** Scoring algorithm is somewhat arbitrary. If stakeholder disagrees with weightings, update DECISIONS.md with DEC-002 (Hazard Risk Scoring Model) and re-run calculations.

**References:** See [ROADMAP-M1.md Task M1.2](ROADMAP-M1.md#task-m12-create-regulatory-classification-dimension--hazard-risk-scoring) for risk scoring logic and formulas.

---

### 1.3 — Brand/Manufacturer Market Analysis & Risk Exposure *(Size: S–M)*

**File:** `warehouse/dim_brands.parquet`, `warehouse/category_hazard_analysis.parquet` (new)  
**Description:** Aggregate hazard insights by brand, manufacturer, and product category. Calculate market concentration of high-risk products.

**Acceptance criteria:**

- [ ] `warehouse/dim_brands.parquet` created with brand_id, brand_name, company, product_count, avg_hazard_score, max_hazard_flag
- [ ] `warehouse/category_hazard_analysis.parquet` created with product_count, avg_hazard_score, pct_high_hazard, pct_reproductive_hazard, pct_carcinogen per category
- [ ] Market report: `reports/M1.3_brand_market_analysis.md` with top risky brands and categories
- [ ] Spot-check: Verify 5 brand aggregations match product-level data
- [ ] Log: `logs/M1.3_market_analysis.log` with aggregation summaries

---

### 1.4 — Generate Summary Reports & Dashboards *(Size: M)*

**File:** Markdown reports in `reports/` (M1_regulatory_summary.md, M1_hazard_inventory.md, M1_market_trends.md)  
**Description:** Synthesize all M1 outputs into human-readable markdown reports and executive summaries.

**Acceptance criteria:**

- [ ] `reports/M1_regulatory_summary.md` created with top 10 highest-risk products, category hazard distribution, gaps in data coverage
- [ ] `reports/M1_hazard_inventory.md` created with sortable table of ingredient_raw → canonical_name → hazard_class → H-codes → source
- [ ] `reports/M1_market_trends.md` created with brand risk analysis and category-level insights
- [ ] All reports include data statistics and executive summary (≥3 key findings per report)
- [ ] Navigation links added to [STATUS.md](STATUS.md) for easy access to reports
- [ ] Automated report generation script created: `warehouse/generate_m1_reports.py` for future updates

---

## Tier B Backlog (future ideas, not scheduled)

> Items that are wanted but not yet prioritized. Promote to a milestone when the time comes.

- Fallback chemical identity matching (without CAS) using ingredient name fuzzy matching — Deferred pending M1.1 coverage
- ECHA REACH registration lookup for high-priority chemicals — Phase 2 (M2+)
- Occupational exposure limits (NIOSH PEG, ACGIH TLV) integration — Phase 2
- Formulation optimization recommendations — M2 scope
- Web UI / interactive dashboard — M2 scope
- Brand/manufacturer analysis and market trends
- UI / reporting dashboard for findings
- Automated data quality monitoring pipeline

---

## Size Reference

| Size | Rough effort | Typical scope |
| ---- | ------------ | ------------- |
| XS | < 30 min | One-liner fix, rename, add a config key |
| S | 30–90 min | Single-function change, small new utility |
| M | 2–4 hours | New module, significant refactor, test suite for a component |
| L | 4–8+ hours | Multi-file feature, complex state changes, new CLI command + tests |
