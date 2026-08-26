# Hair Glue Project — Quick Reference Guide

Welcome! This document is your sanity map for the main repository. It provides a high-level overview and direct links to the most important files, scripts, and planning docs.

---

## Project Overview

A data analysis and chemical identity resolution pipeline for hair-glue and weaving-adhesive products reported in the U.S. Cosmetic Safety & Product Tracker (CSCP) database.

**Current Milestone:** M2 — Deep Chemical Enrichment & Interactive Reporting

---

## Key Directories & Files

- **Data Source:**
  - [data/raw/cscp_chemicals_in_cosmetics.csv](data/raw/cscp_chemicals_in_cosmetics.csv) — Main CSCP data (read-only)
  - [data/curated/](data/curated/) — Curated Parquet outputs (dim_chemical, dim_product, bridge tables)

- **Exploration & Filtering:**
  - [exploration/explore_cscp_hair_glue.py](exploration/explore_cscp_hair_glue.py) — Main EDA script (keyword filtering, plots)
  - [exploration/exploration_summary.csv](exploration/exploration_summary.csv) — Summary stats from last run
  - [exploration/exploration.md](exploration/exploration.md) — Keyword rules and EDA notes
  - [figures/](figures/) — Output plots

- **Pipeline & ETL:**
  - [pipeline/cli.py](pipeline/cli.py) — CLI entry point (`pipeline-cli` commands)
  - [pipeline/extract/](pipeline/extract/) — Data extraction modules (cscp, chemspider, comptox_ctx, echa_reach)
  - [pipeline/transform/](pipeline/transform/) — Enrichment & identity resolution (build_dims_facts, enrich_chemspider, enrich_ctx, enrich_hazards, resolve_identity_fallback)
  - [pipeline/load/](pipeline/load/) — Loaders (to_parquet, to_duckdb)
  - [pipeline/utils/http.py](pipeline/utils/http.py) — Shared HTTP utilities

- **Warehouse Scripts:**
  - [warehouse/build_dimensions.py](warehouse/build_dimensions.py) — Dimension table builder (M0.2)
  - [warehouse/resolve_identity.py](warehouse/resolve_identity.py) — Chemical identity resolution (M0.3)
  - [warehouse/source_hazard_data.py](warehouse/source_hazard_data.py) — PubChem GHS hazard sourcing (M1.1)
  - [warehouse/build_hazard_classification.py](warehouse/build_hazard_classification.py) — Hazard classification & risk scoring (M1.2)
  - [warehouse/build_market_analysis.py](warehouse/build_market_analysis.py) — Brand/market risk analysis (M1.3)
  - [warehouse/generate_m1_reports.py](warehouse/generate_m1_reports.py) — M1 report generation
  - [warehouse/source_regulatory_data.py](warehouse/source_regulatory_data.py) — ECHA regulatory data sourcing (M2.3)

- **Warehouse Outputs (Parquet):**
  - `warehouse/dim_products.parquet`, `dim_ingredients.parquet`, `dim_brands.parquet`, `dim_hazard_classes.parquet`
  - `warehouse/fact_product_ingredients.parquet`, `fact_chemical_hazards.parquet`
  - `warehouse/ref_chemicals.parquet`, `ref_chemicals_hazard.parquet`, `ref_chemicals_regulatory.parquet`
  - `warehouse/ingredient_identity_matched.parquet`, `product_hazard_summary.parquet`, `category_hazard_analysis.parquet`
  - `warehouse.db` — DuckDB database

- **Interactive Dashboard:**
  - [app.py](app.py) — Streamlit web app (7 pages: Overview, Product Browser, Chemical Database, Brand Risk, Category Analysis, Certification Readiness, Identity Resolution)
  - [certifications.py](certifications.py) — Certification standards (EWG VERIFIED, Cradle to Cradle, Living Product Challenge) and the ingredient screening rules behind the Certifications page — see [docs/CERTIFICATIONS.md](docs/CERTIFICATIONS.md)

- **Planning & Status:**
  - [plan/STATUS.md](plan/STATUS.md) — **Start here each session** (current milestone, blockers, next steps)
  - [plan/TODO.md](plan/TODO.md) — Milestone tasks
  - [plan/PROJECT_GUIDE.md](plan/PROJECT_GUIDE.md) — Project conventions and workflow guide
  - [plan/DECISIONS.md](plan/DECISIONS.md) — Design decisions log
  - [plan/GOTCHAS.md](plan/GOTCHAS.md) — Known pitfalls
  - [plan/ROADMAP-M0.md](plan/ROADMAP-M0.md) — M0 implementation spec (complete)
  - [plan/ROADMAP-M1.md](plan/ROADMAP-M1.md) — M1 implementation spec (complete)
  - [plan/ROADMAP-M2.md](plan/ROADMAP-M2.md) — M2 implementation spec (in progress)

- **Documentation:**
  - [docs/DECISIONS.md](docs/DECISIONS.md) — Authoritative design decisions (DEC-001 through DEC-005)
  - [docs/CTX_ENRICHMENT.md](docs/CTX_ENRICHMENT.md) — CompTox CTX API enrichment notes

- **Reports:**
  - [reports/M0.3_identity_resolution_report.md](reports/M0.3_identity_resolution_report.md)
  - [reports/M1.1_hazard_sourcing_report.md](reports/M1.1_hazard_sourcing_report.md)
  - [reports/M1.2_hazard_classification_report.md](reports/M1.2_hazard_classification_report.md)
  - [reports/M1.3_brand_market_analysis.md](reports/M1.3_brand_market_analysis.md)
  - [reports/M1_hazard_inventory.md](reports/M1_hazard_inventory.md), [M1_market_trends.md](reports/M1_market_trends.md), [M1_regulatory_summary.md](reports/M1_regulatory_summary.md)
  - [reports/M2.1_fallback_resolution_report.md](reports/M2.1_fallback_resolution_report.md)
  - [reports/M2.3_regulatory_data_report.md](reports/M2.3_regulatory_data_report.md)

- **Tests:**
  - [tests/](tests/) — Unit tests (pytest)

- **API & Notebooks:**
  - [api/chemspider_search.py](api/chemspider_search.py) — ChemSpider API client prototype
  - [api/Data_Extraction.ipynb](api/Data_Extraction.ipynb) — Data extraction notebook

---

## How to Run

1. **Set up environment (Windows):**
   - `python -m venv .venv && .venv/Scripts/activate`
   - `pip install pandas matplotlib pyarrow duckdb requests rapidfuzz streamlit plotly`
   - Or install editable package: `pip install -e .`

2. **Configure API keys:**
   - Copy `.env.example` to `.env` and fill in `CHEMSPIDER_API_KEY`

3. **Run main EDA script:**
   - `python exploration/explore_cscp_hair_glue.py`

4. **Run pipeline CLI commands:**
   - `python -m pipeline.cli --help`
   - `python -m pipeline.cli enrich-chemspider`

5. **Launch interactive dashboard:**
   - `streamlit run app.py`

6. **Run tests:**
   - `pytest tests/`

7. **Check outputs:**
   - Plots in [figures/](figures/)
   - Summary in [exploration/exploration_summary.csv](exploration/exploration_summary.csv)
   - Warehouse Parquet files in [warehouse/](warehouse/)

---

## Start Here Each Session
- [plan/STATUS.md](plan/STATUS.md) — current milestone, blockers, and exact next task

---

## Getting Help
- Check [plan/GOTCHAS.md](plan/GOTCHAS.md) for known issues
- Review [docs/DECISIONS.md](docs/DECISIONS.md) for design choices
- See [plan/PROJECT_GUIDE.md](plan/PROJECT_GUIDE.md) for project conventions

---

Stay focused, and refer to this doc whenever you need to re-orient yourself!
