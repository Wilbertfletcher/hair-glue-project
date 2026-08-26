# Hair Glue Project — What This Project Does

## Purpose

This project analyzes the chemical safety of hair-glue and weaving-adhesive products sold in the United States. It uses data from the **U.S. Cosmetic Safety & Product Tracker (CSCP)** database — a public dataset of 114,000+ product-ingredient records reported by cosmetics companies.

The pipeline extracts hair-glue products, identifies their chemical ingredients, classifies each chemical by GHS hazard, and scores every product for safety risk. The results are available through an interactive web dashboard and a set of analysis reports.

---

## What It Does, Step by Step

1. **Extracts** hair-glue-related products from the CSCP database using keyword filtering (glue, adhesive, bond, wig, lace, weave, closure, frontal)
2. **Resolves chemical identities** — matches raw CSCP ingredient names to canonical chemical identities using CAS Registry Numbers and PubChem (100% match rate achieved)
3. **Sources GHS hazard data** — pulls Globally Harmonized System classifications from PubChem PUG View for each identified chemical
4. **Classifies risk** — assigns hazard scores (0–100) to every product based on ingredient toxicity, carcinogenicity, and reproductive hazard
5. **Analyzes market exposure** — ranks brands and product categories by hazard risk
6. **Presents results** — interactive Streamlit dashboard + detailed markdown reports

---

## Interactive Dashboard

**Launch locally (Windows):**
```bash
cd c:\Users\admin\Desktop\Thesis\hair-glue-project\hair-glue-project
.venv\Scripts\activate
streamlit run app.py
```

**Local URL (when running):**
http://localhost:8501

The dashboard has 7 pages:

| Page | What It Shows |
|------|--------------|
| **Overview** | Executive summary — product count, match rate, hazard distribution pie chart, category risk bar chart |
| **Products** | Searchable product table with filters by category and hazard level; click any product to see its ingredients |
| **Chemicals** | Search chemicals by CAS number or name; view GHS hazard profile and which products contain each chemical |
| **Brands** | Brand hazard rankings, sortable by avg score, max score, carcinogen count, etc. |
| **Categories** | Side-by-side category hazard comparison; % high hazard and % carcinogen breakdowns |
| **Certifications** | Certification readiness — what EWG VERIFIED, Cradle to Cradle Certified and the Living Product Challenge require, and an unofficial pre-screen of every product against their published ingredient rules (see `docs/CERTIFICATIONS.md`) |
| **Identity Resolution** | Coverage statistics — how each ingredient was matched (CAS lookup, PubChem search, manual mapping) |

---

## Reports

| Report | Description |
|--------|-------------|
| [M0.3 Identity Resolution](../reports/M0.3_identity_resolution_report.md) | CAS-first chemical identity matching — how 91/147 rows were matched in the first pass |
| [M1.1 Hazard Sourcing](../reports/M1.1_hazard_sourcing_report.md) | GHS hazard data sourcing from PubChem PUG View — coverage and data quality |
| [M1.2 Hazard Classification](../reports/M1.2_hazard_classification_report.md) | Risk scoring methodology, hazard flag distribution, top 10 highest-risk products |
| [M1.3 Brand Market Analysis](../reports/M1.3_brand_market_analysis.md) | Brand-level risk aggregation, market concentration of high-hazard products |
| [M1 Regulatory Summary](../reports/M1_regulatory_summary.md) | Executive summary — top findings, regulatory recommendations |
| [M1 Hazard Inventory](../reports/M1_hazard_inventory.md) | Full chemical inventory with GHS classes, H-codes, and data sources |
| [M1 Market Trends](../reports/M1_market_trends.md) | Brand risk rankings, category comparison, market concentration analysis |
| [M2.1 Fallback Resolution](../reports/M2.1_fallback_resolution_report.md) | How the remaining 56 unmatched rows were resolved to reach 100% match rate |
| [M2.3 Regulatory Data](../reports/M2.3_regulatory_data_report.md) | Regulatory data integration (TSCA, Prop 65, REACH, IARC) |
| [M2.3 REACH Detail](../reports/M2.3_reach_detail_report.md) | ECHA REACH tonnage band and registrant count per chemical |
| [M2 Chemical Profiles](../reports/M2_chemical_profiles.md) | Per-chemical deep profile — identity, structure, hazard, regulatory |
| [M2 Coverage Summary](../reports/M2_coverage_summary.md) | Data completeness matrix across all 16 fields with source attribution |
| [M2 Enrichment Delta](../reports/M2_enrichment_delta.md) | Before/after comparison across M0–M2 enrichment stages |

---

## Data Tables (Warehouse)

All canonical data lives in `warehouse/` as Parquet files:

| File | Rows | Description |
|------|------|-------------|
| `dim_products.parquet` | 139 | Product dimension — name, brand, company, category |
| `dim_ingredients.parquet` | 16 | Unique ingredient dimension |
| `fact_product_ingredients.parquet` | 147 | Product ↔ ingredient linkage (with CAS numbers) |
| `ref_chemicals.parquet` | 18 | Canonical chemical reference (PubChem-sourced names, CIDs) |
| `ref_chemicals_hazard.parquet` | 20 | GHS hazard classifications per chemical |
| `ref_chemicals_regulatory.parquet` | 13 | Regulatory status (TSCA, Prop 65, REACH boolean, IARC) |
| `ref_chemicals_reach.parquet` | 14 | ECHA REACH detail — tonnage band, registrant count, registration type |
| `dim_hazard_classes.parquet` | 14 | GHS hazard class dimension |
| `fact_chemical_hazards.parquet` | 55 | Chemical ↔ hazard class linkage (H-codes, P-codes) |
| `product_hazard_summary.parquet` | 139 | Product-level hazard scores and flags |
| `dim_brands.parquet` | 67 | Brand dimension with aggregated hazard metrics |
| `category_hazard_analysis.parquet` | 8 | Category-level hazard analysis with recommendations |
| `ingredient_identity_matched.parquet` | 147 | Full identity resolution results (100% matched) |

---

## Exploratory Figures

Generated by `exploration/explore_cscp_hair_glue.py`:

| Figure | Description |
|--------|-------------|
| `figures/explore_1_top_categories_hair_glue.png` | Top product categories in the hair-glue subset |
| `figures/explore_2_top_ingredients_hair_glue.png` | Most common ingredients across hair-glue products |
| `figures/explore_3_cas_missingness_by_category.png` | CAS number availability by category |
| `figures/explore_4_top_brands_hair_glue.png` | Top brands by product count |
| `figures/explore_5_top_4_categories_pie.png` | Category distribution (pie) |
| `figures/explore_6_top_4_ingredients_pie.png` | Ingredient distribution (pie) |
| `figures/explore_7_top_4_brands_pie.png` | Brand distribution (pie) |
| `figures/explore_8_top_4_companies_pie.png` | Company distribution (pie) |

---

## Pipeline CLI

The pipeline can be run via command line:

```bash
# Ingest CSCP data → build dimension tables
pipeline-cli ingest-cscp --csv data/raw/cscp_chemicals_in_cosmetics.csv

# Load into DuckDB warehouse
pipeline-cli build-warehouse

# Enrich with CompTox identifiers
pipeline-cli enrich-ctx

# Enrich with ChemSpider structure data (M2.2)
python -m pipeline.cli enrich-chemspider

# Fetch regulatory data — TSCA, Prop 65, REACH, IARC (M2.3)
python -m pipeline.cli enrich-regulatory

# Load ECHA bulk export → REACH tonnage/registrant detail (M2.3)
# Requires: data/raw/echa_registered_substances.xlsx (manual download)
python -m pipeline.cli enrich-reach

# Launch interactive dashboard
streamlit run app.py
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Source records (CSCP) | ~114,000 |
| Hair-glue filtered products | 139 |
| Unique ingredients | 16 |
| Chemical identity match rate | 100% (147/147 rows) |
| Chemicals with GHS data | 13/18 (72%) |
| Products flagged HIGH risk | 118/139 (85%) |
| Product categories analyzed | 8 |
| Brands tracked | 67 |
| Average hazard score | 36.8 / 100 |
| Highest hazard score | 90.0 / 100 |

---

## Project Status

- **M0 (Data Foundation):** Complete
- **M1 (Hazard Classification):** Complete
- **M2 (Deep Enrichment & Reporting):** Complete
  - M2.1 Fallback identity resolution — 100% match rate (147/147)
  - M2.2 ChemSpider structure enrichment — 12/13 chemicals (SMILES, InChIKey, MW)
  - M2.3 Regulatory data — TSCA, Prop 65, REACH, IARC, ECHA tonnage
  - M2.4 Interactive dashboard + 3 cross-source reports
- **M3:** Not yet defined — see [STATUS.md](STATUS.md)

For detailed task status, see [STATUS.md](STATUS.md) and [TODO.md](TODO.md).
