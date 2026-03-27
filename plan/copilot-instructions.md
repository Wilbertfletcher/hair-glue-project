# Hair Glue Project — AI Assistant Context

> This file provides stable project context for AI coding assistants (GitHub Copilot,
> Claude, Cursor, etc.). It describes what the project IS, not where it currently stands
> (that's STATUS.md). Update this file when architecture or conventions change, not
> every session.
>
> For GitHub Copilot: place a copy at `.github/copilot-instructions.md` for automatic
> injection. For other assistants, attach this file when starting a new session.

---

## Overview

Hair Glue Project is a data analysis and chemical identity resolution pipeline for hair-glue and weaving-adhesive products reported in the U.S. Cosmetic Safety & Product Tracker (CSCP) database. The goal is to:

1. Extract and validate hair-glue products from CSCP (114k+ reported product-ingredient records)
2. Resolve chemical identities using CAS Registry Numbers and supplementary reference data
3. Classify chemicals by hazard/regulatory status (future phases)

Current phase (M0): Establish data foundation, finalize keyword filtering rules, and implement basic CAS-first identity resolution.

---

## Repository Structure

```
hair-glue-project/
├── data/
│   ├── raw/                          ← CSCP data (read-only source)
│   │   └── cscp_chemicals_in_cosmetics.csv (~114k rows)
│   ├── curated/                      ← (placeholder for processed snapshots)
│   └── stage/                        ← (placeholder for intermediate transforms)
├── exploration/
│   ├── explore_cscp_hair_glue.py    ← Main EDA script (keyword filtering, plots)
│   ├── explore_cscp_hair_glue.md    ← Notes from exploration
│   └── exploration_summary.csv      ← Summary stats from last run
├── figures/                          ← Output plots (8 exploratory charts)
├── warehouse/                        ← Canonical dimension/fact tables (Parquet)
│   ├── dim_products.parquet         ← (M0.2: product dimension)
│   ├── dim_ingredients.parquet      ← (M0.2: ingredient dimension)
│   ├── fact_product_ingredients.parquet ← (M0.2: fact table)
│   └── ingredient_identity_matched.parquet ← (M0.3: identity resolution results)
├── reports/                          ← Data quality & analysis reports
├── logs/                             ← Task execution logs
├── plan/                             ← Project planning hub (START HERE)
│   ├── STATUS.md                    ← **Read first each session**
│   ├── TODO.md                      ← Milestone tasks and progress
│   ├── DECISIONS.md                 ← Design decision log
│   ├── GOTCHAS.md                   ← Known pitfalls & deferrals
│   ├── ROADMAP-M0.md                ← M0 detailed specifications
│   ├── copilot-instructions.md      ← This file
│   ├── feature-requests.md          ← Feature inbox
│   └── bug-reports.md               ← Bug inbox
├── status/                           ← Session checkpoints (legacy; deprecated in favor of plan/)
│   ├── checkpoint_1.md              ← Archived pre-framework notes
│   └── needtorefernce/              ← Reference templates (framework source)
├── .git, LICENSE, .gitignore, etc.
└── .venv/                            ← Python virtualenv
```

---

## Architecture

**Single-cycle ETL pipeline:**

```
CSCP CSV (raw)
  ↓
[Filter by keywords] → Hair-Glue Subset (114k → ~20k–50k rows depending on keyword scope)
  ↓
[Deduplicate & dimension] → Product & Ingredient Dimensions + Fact Table (Parquet)
  ↓
[CAS-first matching] → Identity Resolution (supplement with canonical chemical names, synonyms)
  ↓
Reports & Analysis (future: classification, hazard mapping, UI)
```

**Data flow:**
1. **Source:** `data/raw/cscp_chemicals_in_cosmetics.csv` (read-only)
2. **Filter & Explore:** `exploration/explore_cscp_hair_glue.py` (keyword-based subsetting, visualization)
3. **Dimension tables:** Synthetic product_id and ingredient_id; fact table joins them
4. **Identity matching:** CAS-first (CSCP CASRN → canonical reference), fallback TBD

---

## Key Files

| File | Purpose | Status |
| ---- | ------- | ------ |
| `exploration/explore_cscp_hair_glue.py` | Main EDA script; defines PRIMARY_KWS and generates plots | Active |
| `plan/STATUS.md` | **Start here each session** — priorities & completion status | Active |
| `plan/TODO.md` | Milestone tasks with acceptance criteria | Active |
| `plan/DECISIONS.md` | Design decisions log (e.g., keyword rules) | Building |
| `plan/GOTCHAS.md` | Known data quality issues & deferrals | Building |
| `plan/ROADMAP-M0.md` | Detailed M0 implementation spec | Building |
| `warehouse/`.parquet | Canonical tables (M0.2 and M0.3 outputs) | (Not yet built) |
| `data/raw/cscp_chemicals_in_cosmetics.csv` | Source CSCP data — DO NOT MODIFY | Immutable |

---

## Naming Conventions

- **Functions & scripts:** `verb_noun()` (e.g., `keyword_filter()`, `load_cscp()`, `plot_bar()`)
- **Classes:** PascalCase (e.g., `DataFrameTransformer`)
- **Config keys / column names:** `snake_case` (e.g., `primary_keywords`, `casrn`, `product_name`)
- **Synthetic IDs:** `product_id`, `ingredient_id` (integer, auto-generated)
- **Files:** `verb_noun.py` or `noun_descriptor.csv` (e.g., `explore_cscp_hair_glue.py`, `dim_products.parquet`)

---

## How to Run

### Prerequisites
```bash
# Ensure Python 3.8+ and pip installed
python --version
pip --version

# Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install pandas matplotlib pyarrow  # Add more as needed
```

### Main Exploration Script
```bash
# Load CSCP, filter by hair-glue keywords, generate plots
python exploration/explore_cscp_hair_glue.py

# Output: figures/ (8 PNG plots) + exploration/exploration_summary.csv
```

### Dimension Table Building (M0.2 — not yet implemented)
```bash
# (placeholder) python warehouse/build_dimensions.py
```

### Identity Resolution (M0.3 — not yet implemented)
```bash
# (placeholder) python warehouse/resolve_identity.py
```

---

## Important Constraints

> These are hard rules that must be respected during any implementation work.

1. **Never modify source data (`data/raw/`)** — Always work on copies or transformed outputs in `warehouse/` or `data/curated/`
2. **Parquet for canonical tables** — Use Parquet (not CSV) for dimension and fact tables in `warehouse/` for efficiency and schema preservation
3. **Keyword rules are controlled** — Do NOT change PRIMARY_KWS in `explore_cscp_hair_glue.py` without updating DECISIONS.md and confirming with stakeholder
4. **CASRN nullability is expected** — Do NOT drop rows with null CASRN; handle gracefully in identity resolution logic
5. **All AI session handoffs require closing protocol** — Update STATUS.md at the end of every session using the Closing Protocol checklist

---

## External Dependencies & Data Sources

| Dependency | How it's configured | Notes |
| ---------- | ------------------- | ----- |
| CSCP CSV (`data/raw/cscp_chemicals_in_cosmetics.csv`) | File path hardcoded in `explore_cscp_hair_glue.py` line 13 | Provided by project owner; read-only reference |
| Canonical chemical reference (for M0.3) | TBD — PubChem API, EPA, or local CSV | To be sourced during M0.3 implementation; not yet integrated |
| pandas, matplotlib, pyarrow | `pip install` (see requirements section) | Standard data science stack |

---

## Decision Log Reference

See `plan/DECISIONS.md` for:
- **DEC-001 (pending):** Hair-glue keyword filtering scope (precision vs. recall) — awaiting stakeholder input

---

## Gotchas Reference

See `plan/GOTCHAS.md` for known issues:
- CASRN completeness varies (20–80% by category)
- CSCP category labels are non-standardized
- Some valid hair-glue products may be filtered out (false negatives)
- Chemical identity resolution without CAS (fallback) is deferred to M1

---

## Getting Help

1. **Starting a session?** Read `plan/STATUS.md` first
2. **Confused about a task?** Check `plan/ROADMAP-M0.md` for detailed specs
3. **Hit an error?** Check `plan/GOTCHAS.md` — the issue may already be documented
4. **Re-asking an old question?** Check `plan/DECISIONS.md` for prior rationale
