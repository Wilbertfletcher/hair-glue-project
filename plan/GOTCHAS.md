### US GHS Hazard Data Integration (EPA CompTox, GHScrunch)

US GHS hazard data is not natively supported by GHScrunch. The tool only processes Japan, Korea, and New Zealand government datasets. For US hazard data, an external dataset (e.g., EPA CompTox Dashboard CSV) must be downloaded and integrated via a custom script or pipeline extension. GHScrunch may be extended, but is not plug-and-play for US data.

Workaround / status: Download EPA CompTox GHS hazard CSV, place in data/raw/, and write a script to join by CASRN. Optionally, extend GHScrunch or pipeline for US data parsing. See STATUS.md and TODO.md for current action items.

**Reference:** [STATUS.md 2026-03-27 — US GHS integration planning, environment cleanup]
# Hair Glue Project — Codebase Gotchas

> Persistent list of known pitfalls, non-obvious behaviors, deliberate deferrals,
> and "I already looked into this and decided not to fix it yet" notes.
>
> **Add new entries when you discover something. Never delete entries —
> annotate with "RESOLVED: YYYY-MM-DD" and a brief note when resolved.**
>
> Read this before diving into a new area of the codebase.

---

## Data Quality Issues (CSCP dataset)

### CASRN Completeness Varies Widely Across Categories

CASRN (CAS Registry Number) is present in only 20–80% of rows depending on product category. Some categories (e.g., high-end hair-glue products) report CAS numbers consistently; others (e.g., distributors reporting generic "adhesive") have minimal CAS coverage. 

Workaround / status: Task M0.3 is designed to handle this: implement CAS-first matching where CASRN is available, and defer fallback matching (fuzzy name-based) to M1 or beyond. Do NOT drop rows with null CASRN in M0.2; keep them in the fact table and mark coverage gaps in the identity resolution report.

**RESOLVED: 2026-03-28** — M2.1 fallback resolution achieved 100% match rate. All null-CASRN ingredients resolved via PubChem name search or manual mappings. See `reports/M2.1_fallback_resolution_report.md`.

**Reference:** [TODO.md M0.3 pitfall](TODO.md#03--begin-chemical-identity-resolution-cas-first-matching-size-l-defer-if-casrn-coverage-is-40)

---

### CSCP Category Labels Are Not Standardized

Primary category field (`category_raw`) contains hundreds of inconsistent labels (e.g., "Hair Adhesive", "Adhesive Gel (Hair)", "Bonding Agent - Hair", "Weave Adhesive (Product Type: Wig Adhesive)"). No canonical category taxonomy exists in the raw data.

Workaround / status: Keyword filtering on both `product_name` and `category_raw` is necessary and intentional. The PRIMARY_KWS list in `explore_cscp_hair_glue.py` serves as an implicit categorization. Do NOT attempt to normalize category labels before M0.1 is complete; wait for keyword decision.

**Reference:** [DEC-001 (pending) — Keyword Filtering Scope](DECISIONS.md#dec-001-hair-glue-keyword-filtering-scope-precision-vs-recall)

---

### Some Valid Hair-Glue Products May Be Filtered Out (False Negatives)

The PRIMARY_KWS list (glue, adhesive, bond, bonding, wig, lace, weave, closure, frontal) is conservative. Products with marketing names like "Fusion Sealer" or "Hold Pro" may be missed. Conversely, some category labels might inadvertently match (e.g., "Adhesive" in a foot lotion category).

Workaround / status: This is a known trade-off in M0.1. Stakeholder decision on precision vs. recall will be recorded in DEC-001. If higher recall is desired, expand PRIMARY_KWS (but expect more false positives). If higher precision is desired, apply secondary filtering rules (e.g., exclude known foot-care categories).

**Reference:** [TODO.md M0.1 — Finalize Hair-Glue Keyword Rules](TODO.md#01--finalize-hair-glue-keyword-rules-size-m)

---

## Deliberate Deferrals

### Chemical Identity Resolution Without CAS (Fallback Matching) — Deferred to M1

Querying ingredients by fuzzy name matching (for the ~40–80% with null CASRN) requires secondary reference data (e.g., ingredient name synonyms, common misspellings). This is deferred to Milestone 1 pending M0.3's success rate with CAS-first matching.

Decision: If M0.3 achieves >80% match rate with CAS alone, defer fallback matching. If match rate is <40%, escalate to stakeholder before implementing M0.3.

**Reference:** [TODO.md M0.3 pitfall](TODO.md#03--begin-chemical-identity-resolution-cas-first-matching-size-l-defer-if-casrn-coverage-is-40)

---

### Regulatory Classification / Hazard Mapping — Not in Scope for M0

Hair-glue ingredients may be classified under different regulatory frameworks (EPA, ECHA, etc.). Mapping to hazard categories (toxicity, environmental impact, etc.) is valuable but depends on M0.3 completion. Deferred to M1 or M2.

---

### EPA CompTox & PubChem APIs Have Inconsistent Hazard Data Endpoints — Discovered M1.1

**Issue:** EPA CompTox API structure changed and does not expose GHS hazard data reliably via standard endpoints. PubChem provides chemical data but does not return structured GHS classifications in a readily accessible format via REST API.

**Workaround / status (2026-03-25):** Created M1.1 infrastructure (script, table schema, report template) that demonstrates the intended data flow, but actual hazard data collection requires one of the following approaches:

**Option A (Recommended for real implementation):**
- **ECHA REACH registration API** (`echa.europa.eu/rest`) — Most comprehensive GHS data, but slower and EU-focused
- **ChemSpider API** (requires paid license) — Comprehensive structured hazard data
- **Local GHS database** (vendor-provided or open-source) — Fast but requires initial setup

**Option B (Acceptable for Phase 1):**
- Use web scraping or manual lookup for high-priority chemicals
- Flag low-priority chemicals as NO_DATA in M1.2 risk scoring
- Proceed with best-effort data for products with matched chemicals

**Decision pending:** DEC-004 (Hazard Data Source Resolution) will specify which approach to use for M1.2+ continuation.

**References:** 
- [TODO.md M1.1](TODO.md#11--source--integrate-hazard-regulatory-reference-data-size-ml)
- [ROADMAP-M1.md Task M1.1 — Hazard Data Sources](ROADMAP-M1.md#hazard-data-sources-evaluated)
- `warehouse/source_hazard_data.py` — M1.1 implementation script (ready for alternative data sources)

**Reference:** Tier B Backlog in [TODO.md](TODO.md#tier-b-backlog-future-ideas-not-scheduled)

---

<!-- 
Guidelines:
- Keep entries short — one paragraph is ideal.
- Link to relevant DEC entries when a gotcha is connected to a design decision.
- When a gotcha is resolved: add `RESOLVED: YYYY-MM-DD — <brief explanation>` at the
  bottom of the entry. Do NOT delete the entry.
- Group related gotchas under the same heading.
-->
