# Hair Glue Project — Quick Reference Guide

Welcome! This document is your sanity map for the main repository. It provides a high-level overview and direct links to the most important files, scripts, and planning docs.

---

## 🚀 Project Overview

A data analysis and chemical identity resolution pipeline for hair-glue and weaving-adhesive products reported in the U.S. Cosmetic Safety & Product Tracker (CSCP) database.

---

## 🗂️ Key Directories & Files

- **Data Source:**
  - [data/raw/cscp_chemicals_in_cosmetics.csv](data/raw/cscp_chemicals_in_cosmetics.csv) — Main CSCP data (read-only)

- **Exploration & Filtering:**
  - [exploration/explore_cscp_hair_glue.py](exploration/explore_cscp_hair_glue.py) — Main EDA script (keyword filtering, plots)
  - [exploration/exploration_summary.csv](exploration/exploration_summary.csv) — Summary stats from last run
  - [figures/](figures/) — Output plots

- **Pipeline & ETL:**
  - [pipeline/extract/](pipeline/extract/) — Data extraction modules
  - [pipeline/transform/](pipeline/transform/) — Data transformation/enrichment
  - [pipeline/load/](pipeline/load/) — Loaders (to Parquet, DuckDB)
  - [warehouse/build_dimensions.py](warehouse/build_dimensions.py) — Dimension table builder (M0.2)
  - [warehouse/resolve_identity.py](warehouse/resolve_identity.py) — Chemical identity resolution (M0.3)

- **Canonical Tables:**
  - [warehouse/](warehouse/) — Parquet outputs (dimensions, facts, identity matches)

- **Planning & Status:**
  - [plan/STATUS.md](plan/STATUS.md) — **Start here each session**
  - [plan/TODO.md](plan/TODO.md) — Milestone tasks
  - [plan/DECISIONS.md](plan/DECISIONS.md) — Design decisions
  - [plan/GOTCHAS.md](plan/GOTCHAS.md) — Known pitfalls
  - [plan/ROADMAP-M0.md](plan/ROADMAP-M0.md) — M0 implementation spec

- **Reports:**
  - [reports/](reports/) — Data quality & analysis reports

- **External Reference:**
  - [external/GHScrunch/](external/GHScrunch/) — GHS hazard data tools

---

## 📝 How to Run

1. **Set up environment:**
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install pandas matplotlib pyarrow`
2. **Run main EDA script:**
   - `python exploration/explore_cscp_hair_glue.py`
3. **Check outputs:**
   - Plots in [figures/](figures/)
   - Summary in [exploration/exploration_summary.csv](exploration/exploration_summary.csv)

---

## 🧭 Start Here Each Session
- [plan/STATUS.md](plan/STATUS.md)

---

## 🆘 Getting Help
- Check [plan/GOTCHAS.md](plan/GOTCHAS.md) for known issues
- Review [plan/DECISIONS.md](plan/DECISIONS.md) for design choices

---

Stay focused, and refer to this doc whenever you need to re-orient yourself!
