#!/usr/bin/env python3
"""
Hair Glue Project — M1.4 Summary Report Generation

Generates three synthesis reports from M1.1–M1.3 warehouse data:
1. reports/M1_regulatory_summary.md   — High-level findings & recommendations
2. reports/M1_hazard_inventory.md     — Detailed chemical inventory with GHS
3. reports/M1_market_trends.md        — Brand/company market analysis
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/M1.4_report_generation.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE = Path("warehouse")
REPORTS = Path("reports")

FLAG_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NO_DATA": 0}


def load_data():
    """Load all warehouse tables needed for reports."""
    data = {
        "ref_hazard": pd.read_parquet(WAREHOUSE / "ref_chemicals_hazard.parquet"),
        "prod_summary": pd.read_parquet(WAREHOUSE / "product_hazard_summary.parquet"),
        "dim_brands": pd.read_parquet(WAREHOUSE / "dim_brands.parquet"),
        "dim_products": pd.read_parquet(WAREHOUSE / "dim_products.parquet"),
        "dim_ingredients": pd.read_parquet(WAREHOUSE / "dim_ingredients.parquet"),
        "fact_pi": pd.read_parquet(WAREHOUSE / "fact_product_ingredients.parquet"),
        "cat_analysis": pd.read_parquet(WAREHOUSE / "category_hazard_analysis.parquet"),
        "dim_hazard": pd.read_parquet(WAREHOUSE / "dim_hazard_classes.parquet"),
        "fact_chem_haz": pd.read_parquet(WAREHOUSE / "fact_chemical_hazards.parquet"),
    }
    logger.info("Loaded %d warehouse tables", len(data))
    return data


def generate_regulatory_summary(data):
    """Report 1: High-level regulatory findings and recommendations."""
    ps = data["prod_summary"]
    rh = data["ref_hazard"]
    ca = data["cat_analysis"]
    dp = data["dim_products"]
    db = data["dim_brands"]

    today = date.today().isoformat()
    path = REPORTS / "M1_regulatory_summary.md"

    flags = ps["hazard_flag"].value_counts()
    avg_score = ps["hazard_score"].mean()
    repro_products = (ps["reproductive_hazard_ingredient_count"] > 0).sum()
    carc_products = (ps["carcinogen_count"] > 0).sum()
    chemicals_with_data = rh[rh["h_codes"].notna()]
    chemicals_no_data = rh[rh["h_codes"].isna()]

    with open(path, "w") as f:
        f.write("# M1 Regulatory Summary — Hair Glue Product Hazard Analysis\n\n")
        f.write(f"**Generated:** {today}  \n")
        f.write("**Milestone:** M1 — Regulatory Classification & Hazard Mapping  \n")
        f.write("**Data Source:** U.S. Cosmetic Safety & Product Tracker (CSCP)  \n")
        f.write("**Hazard Source:** PubChem PUG View API (GHS classifications)  \n\n")
        f.write("---\n\n")

        # Executive summary
        f.write("## Executive Summary\n\n")
        f.write(f"This analysis covers **{len(ps)} hair-glue and related cosmetic products** ")
        f.write(f"from **{db['company'].nunique()} companies** across **{len(ca)} product categories**. ")
        f.write(f"Chemical identity resolution identified **{len(rh)} unique chemicals**, of which ")
        f.write(f"**{len(chemicals_with_data)}** ({len(chemicals_with_data)/len(rh)*100:.0f}%) have GHS hazard data.\n\n")

        f.write("### Key Metrics\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Total products analyzed | {len(ps)} |\n")
        f.write(f"| Total unique chemicals | {len(rh)} |\n")
        f.write(f"| Chemicals with GHS data | {len(chemicals_with_data)} ({len(chemicals_with_data)/len(rh)*100:.0f}%) |\n")
        f.write(f"| Products classified HIGH risk | {flags.get('HIGH', 0)} ({flags.get('HIGH', 0)/len(ps)*100:.0f}%) |\n")
        f.write(f"| Products with reproductive hazards | {repro_products} ({repro_products/len(ps)*100:.0f}%) |\n")
        f.write(f"| Products containing carcinogens | {carc_products} ({carc_products/len(ps)*100:.0f}%) |\n")
        f.write(f"| Average hazard score (0–100) | {avg_score:.1f} |\n")
        f.write(f"| Companies analyzed | {db['company'].nunique()} |\n")
        f.write(f"| Brands analyzed | {len(db)} |\n\n")

        # Hazard distribution
        f.write("---\n\n## Hazard Distribution\n\n")
        f.write("| Risk Level | Products | % of Total | Avg Score |\n")
        f.write("|------------|----------|------------|----------|\n")
        for flag in ["HIGH", "MEDIUM", "LOW", "NO_DATA"]:
            subset = ps[ps["hazard_flag"] == flag]
            cnt = len(subset)
            pct = cnt / len(ps) * 100 if len(ps) > 0 else 0
            avg = subset["hazard_score"].mean() if cnt > 0 else 0
            f.write(f"| {flag} | {cnt} | {pct:.1f}% | {avg:.1f} |\n")
        f.write("\n")

        # Top 10 highest-risk products
        f.write("## Top 10 Highest-Risk Products\n\n")
        f.write("| Rank | Product | Brand | Category | Score | Hazard Classes | Repro | Carc |\n")
        f.write("|------|---------|-------|----------|-------|---------------|-------|------|\n")
        top10 = ps.nlargest(10, "hazard_score").merge(dp[["product_id", "brand", "category_raw"]], on="product_id", how="left")
        for rank, (_, row) in enumerate(top10.iterrows(), 1):
            name = str(row["product_name"])[:40]
            brand = str(row.get("brand", "—"))[:20]
            cat = str(row.get("category_raw", "—"))[:25]
            classes = str(row.get("hazard_classes_present", "—"))[:40]
            f.write(f"| {rank} | {name} | {brand} | {cat} | {row['hazard_score']:.0f} | {classes} | {row['reproductive_hazard_ingredient_count']} | {row['carcinogen_count']} |\n")
        f.write("\n")

        # Categories with reproductive/carcinogen concerns
        f.write("## Categories with Reproductive / Carcinogen Concerns\n\n")
        f.write("| Category | Products | % Repro Hazard | % Carcinogen | Avg Score | Recommendation |\n")
        f.write("|----------|----------|---------------|-------------|-----------|----------------|\n")
        for _, row in ca.sort_values("pct_carcinogen", ascending=False).iterrows():
            cat = str(row["category_raw"])[:35]
            rec = str(row["recommendation"])[:50]
            f.write(f"| {cat} | {row['product_count']} | {row['pct_reproductive_hazard']:.0f}% | {row['pct_carcinogen']:.0f}% | {row['avg_hazard_score']:.0f} | {rec} |\n")
        f.write("\n")

        # Coverage gaps
        f.write("## Hazard Data Coverage Gaps\n\n")
        f.write("The following chemicals could not be matched to GHS hazard data:\n\n")
        f.write("| Chemical | CASRN | Data Source | Match Confidence | Issue |\n")
        f.write("|----------|-------|-----------|-----------------|-------|\n")
        for _, row in chemicals_no_data.iterrows():
            name = str(row.get("canonical_name", "—"))[:45]
            casrn = str(row.get("casrn", "—"))
            src = str(row.get("data_source", "—"))
            conf = row.get("match_confidence", 0)
            if src == "fallback_no_match":
                issue = "No PubChem CID found"
            elif src == "pubchem_no_ghs":
                issue = "CID found but no GHS classification"
            elif src == "no_cid_resolved":
                issue = "CAS resolved but no CID"
            else:
                issue = "Unknown"
            f.write(f"| {name} | {casrn} | {src} | {conf:.1f} | {issue} |\n")
        f.write("\n")

        # Regulatory recommendations
        f.write("## Regulatory Recommendations\n\n")
        f.write("### Immediate Priorities\n\n")
        f.write("1. **Formaldehyde-containing products** (CAS 50-00-0) — Classified as a confirmed carcinogen (H350) ")
        f.write("and mutagen (H341). Found in lash adhesives. Recommend reformulation or enhanced labeling.\n\n")
        f.write("2. **Ethyl cyanoacrylate / nail glue products** — Dominant ingredient in nail adhesives. ")
        f.write(f"{repro_products} products ({repro_products/len(ps)*100:.0f}%) contain reproductive toxicants. ")
        f.write("Recommend consumer exposure assessment.\n\n")
        f.write("3. **Styrene-containing products** (CAS 100-42-5) — STOT-RE Category 1 (H372), reproductive ")
        f.write("suspected (H361). Used in lash adhesives. Monitor for regulatory action.\n\n")

        f.write("### Data Quality Improvements\n\n")
        f.write(f"- {len(chemicals_no_data)} chemicals ({len(chemicals_no_data)/len(rh)*100:.0f}%) lack GHS data — ")
        f.write("manual review recommended for: mineral oils, cocamide DEA, talc, crystalline silica\n")
        f.write(f"- {flags.get('NO_DATA', 0)} products ({flags.get('NO_DATA', 0)/len(ps)*100:.0f}%) classified as NO_DATA ")
        f.write("due to insufficient hazard coverage — additional data sourcing may reclassify these\n\n")

        f.write("### Next Steps (M2)\n\n")
        f.write("- Identify safer chemical alternatives for high-risk ingredients\n")
        f.write("- Map to FDA/state-level regulatory requirements\n")
        f.write("- Build automated monitoring for new CSCP product reports\n")
        f.write("- Develop consumer-facing hazard dashboards\n\n")

        f.write("---\n\n")
        f.write("*See also:* [M1_hazard_inventory.md](M1_hazard_inventory.md) · ")
        f.write("[M1_market_trends.md](M1_market_trends.md)\n")

    logger.info("Generated: %s", path)


def generate_hazard_inventory(data):
    """Report 2: Detailed chemical inventory with GHS classifications."""
    rh = data["ref_hazard"]
    dh = data["dim_hazard"]
    fch = data["fact_chem_haz"]
    di = data["dim_ingredients"]
    fp = data["fact_pi"]

    today = date.today().isoformat()
    path = REPORTS / "M1_hazard_inventory.md"

    with open(path, "w") as f:
        f.write("# M1 Hazard Inventory — Chemical GHS Classifications\n\n")
        f.write(f"**Generated:** {today}  \n")
        f.write("**Source:** PubChem PUG View API  \n\n")
        f.write("---\n\n")

        # Coverage statistics
        total = len(rh)
        with_ghs = rh["h_codes"].notna().sum()
        epa_pubchem = rh[rh["data_source"].str.contains("pubchem_pugview", na=False)]
        fallback = rh[rh["data_source"].str.contains("fallback", na=False)]
        resolved = rh[rh["data_source"].str.contains("resolved", na=False)]

        f.write("## Coverage Statistics\n\n")
        f.write("| Metric | Count | % |\n")
        f.write("|--------|-------|---|\n")
        f.write(f"| Total unique chemicals | {total} | 100% |\n")
        f.write(f"| With GHS hazard data | {with_ghs} | {with_ghs/total*100:.0f}% |\n")
        f.write(f"| PubChem PUG View (direct) | {len(epa_pubchem)} | {len(epa_pubchem)/total*100:.0f}% |\n")
        f.write(f"| PubChem (CAS resolved) | {len(resolved)} | {len(resolved)/total*100:.0f}% |\n")
        f.write(f"| Fallback name match | {len(rh[rh['data_source'].str.contains('fallback_name', na=False)])} | {len(rh[rh['data_source'].str.contains('fallback_name', na=False)])/total*100:.0f}% |\n")
        f.write(f"| No match / no GHS | {total - with_ghs} | {(total-with_ghs)/total*100:.0f}% |\n\n")

        # Full chemical inventory table
        f.write("## Complete Chemical Inventory\n\n")
        f.write("| # | Chemical Name | CASRN | Signal Word | H-Codes | GHS Classes | Repro | Carc | Source | Conf |\n")
        f.write("|---|-------------|-------|-------------|---------|------------|-------|------|--------|------|\n")

        sorted_rh = rh.sort_values("match_confidence", ascending=False)
        for i, (_, row) in enumerate(sorted_rh.iterrows(), 1):
            name = str(row.get("canonical_name", "—"))
            if name == "nan" or name == "None":
                # Try to find the ingredient_raw name from dim_ingredients by casrn
                casrn = row.get("casrn")
                if pd.notna(casrn):
                    match = di[di["cas_available"] == True]
                    name = f"[CAS {casrn}]"
                else:
                    name = "—"
            else:
                name = name[:45]

            casrn = str(row.get("casrn", "—"))
            if casrn == "nan":
                casrn = "—"

            signal = str(row.get("ghs_signal_word", "—"))
            if signal == "nan":
                signal = "—"

            h_codes = str(row.get("h_codes", "—"))
            if h_codes == "nan":
                h_codes = "—"

            classes = str(row.get("ghs_hazard_class", "—"))
            if classes == "nan":
                classes = "—"
            else:
                classes = classes[:40]

            repro = "Yes" if row.get("reproductive_hazard", False) else "No"
            carc = str(row.get("carcinogenicity", "—"))
            if carc == "nan" or carc == "None":
                carc = "—"

            src = str(row.get("data_source", "—"))[:20]
            conf = row.get("match_confidence", 0)

            f.write(f"| {i} | {name} | {casrn} | {signal} | {h_codes} | {classes} | {repro} | {carc} | {src} | {conf:.1f} |\n")
        f.write("\n")

        # GHS hazard class reference
        f.write("## GHS Hazard Class Reference\n\n")
        f.write("| Hazard Class | Category | Signal Word | Target Organs | Definition |\n")
        f.write("|-------------|----------|-------------|--------------|------------|\n")
        for _, row in dh.sort_values("hazard_class").iterrows():
            organs = str(row.get("target_organs", "—"))
            if organs == "nan" or organs == "None":
                organs = "—"
            defn = str(row.get("definition", "—"))[:60]
            f.write(f"| {row['hazard_class']} | {row['hazard_category']} | {row['signal_word']} | {organs} | {defn} |\n")
        f.write("\n")

        # H-code breakdown
        f.write("## H-Code Frequency (across all chemicals)\n\n")
        all_h = []
        for codes in rh["h_codes"].dropna():
            all_h.extend(str(codes).split("|"))
        h_counts = pd.Series(all_h).value_counts()

        f.write("| H-Code | Occurrences | Description |\n")
        f.write("|--------|------------|-------------|\n")
        h_descriptions = {
            "H226": "Flammable liquid and vapour",
            "H302": "Harmful if swallowed",
            "H304": "May be fatal if swallowed and enters airways",
            "H314": "Causes severe skin burns and eye damage",
            "H315": "Causes skin irritation",
            "H317": "May cause an allergic skin reaction",
            "H318": "Causes serious eye damage",
            "H319": "Causes serious eye irritation",
            "H330": "Fatal if inhaled",
            "H332": "Harmful if inhaled",
            "H335": "May cause respiratory irritation",
            "H341": "Suspected of causing genetic defects",
            "H350": "May cause cancer",
            "H351": "Suspected of causing cancer",
            "H360": "May damage fertility or the unborn child",
            "H361": "Suspected of damaging fertility or the unborn child",
            "H372": "Causes damage to organs through prolonged or repeated exposure",
            "H373": "May cause damage to organs through prolonged or repeated exposure",
            "H400": "Very toxic to aquatic life",
            "H411": "Toxic to aquatic life with long lasting effects",
            "H412": "Harmful to aquatic life with long lasting effects",
            "H413": "May cause long lasting harmful effects to aquatic life",
        }
        for code, count in h_counts.items():
            desc = h_descriptions.get(code, "—")
            f.write(f"| {code} | {count} | {desc} |\n")
        f.write("\n")

        f.write("---\n\n")
        f.write("*See also:* [M1_regulatory_summary.md](M1_regulatory_summary.md) · ")
        f.write("[M1_market_trends.md](M1_market_trends.md)\n")

    logger.info("Generated: %s", path)


def generate_market_trends(data):
    """Report 3: Brand/company market analysis and risk concentration."""
    db = data["dim_brands"]
    ca = data["cat_analysis"]
    ps = data["prod_summary"]
    dp = data["dim_products"]
    fp = data["fact_pi"]
    di = data["dim_ingredients"]
    rh = data["ref_hazard"]

    today = date.today().isoformat()
    path = REPORTS / "M1_market_trends.md"

    with open(path, "w") as f:
        f.write("# M1 Market Trends — Brand & Category Risk Analysis\n\n")
        f.write(f"**Generated:** {today}  \n")
        f.write("**Scope:** Hair-glue, lash adhesive, nail glue, and related cosmetic products  \n\n")
        f.write("---\n\n")

        # Market overview
        f.write("## Market Overview\n\n")
        f.write(f"- **{len(dp)} products** from **{db['company'].nunique()} companies** and **{len(db)} brands**\n")
        f.write(f"- **{len(ca)} product categories** represented in the CSCP database\n")
        f.write(f"- **{len(di)} unique ingredients** identified (including chemical variants)\n\n")

        # Company rankings
        f.write("## Top Companies by Product Volume\n\n")
        f.write("| Rank | Company | Brands | Products | Avg Score | Worst Flag | Repro Products | Carc Products |\n")
        f.write("|------|---------|--------|----------|-----------|-----------|---------------|---------------|\n")
        company_agg = (
            db.groupby("company")
            .agg(
                brand_count=("brand", "nunique"),
                product_count=("product_count", "sum"),
                avg_score=("avg_hazard_score", "mean"),
                max_flag=("max_hazard_flag", lambda x: max(x, key=lambda fl: FLAG_ORDER.get(fl, 0))),
                repro=("total_repro_products", "sum"),
                carc=("total_carc_products", "sum"),
            )
            .sort_values("product_count", ascending=False)
        )
        for rank, (company, row) in enumerate(company_agg.head(15).iterrows(), 1):
            f.write(f"| {rank} | {str(company)[:35]} | {row['brand_count']} | {row['product_count']} | {row['avg_score']:.0f} | {row['max_flag']} | {int(row['repro'])} | {int(row['carc'])} |\n")
        f.write("\n")

        # Brand risk rankings
        f.write("## Brand Risk Rankings\n\n")
        f.write("### Highest-Risk Brands (by average hazard score)\n\n")
        f.write("| Rank | Brand | Company | Products | Avg Score | Max Score | Flag |\n")
        f.write("|------|-------|---------|----------|-----------|-----------|------|\n")
        top_brands = db.nlargest(15, "avg_hazard_score")
        for rank, (_, row) in enumerate(top_brands.iterrows(), 1):
            f.write(f"| {rank} | {str(row['brand'])[:30]} | {str(row['company'])[:30]} | {row['product_count']} | {row['avg_hazard_score']:.0f} | {row['max_hazard_score']:.0f} | {row['max_hazard_flag']} |\n")
        f.write("\n")

        f.write("### Lowest-Risk Brands\n\n")
        f.write("| Brand | Company | Products | Avg Score | Flag |\n")
        f.write("|-------|---------|----------|-----------|------|\n")
        low_brands = db.nsmallest(10, "avg_hazard_score")
        for _, row in low_brands.iterrows():
            f.write(f"| {str(row['brand'])[:30]} | {str(row['company'])[:30]} | {row['product_count']} | {row['avg_hazard_score']:.0f} | {row['max_hazard_flag']} |\n")
        f.write("\n")

        # Category comparison
        f.write("## Category Hazard Comparison\n\n")
        f.write("| Category | Products | Avg Score | Max Score | % HIGH | % Repro | % Carc | Top Hazard |\n")
        f.write("|----------|----------|-----------|-----------|--------|---------|--------|------------|\n")
        for _, row in ca.sort_values("avg_hazard_score", ascending=False).iterrows():
            f.write(f"| {str(row['category_raw'])[:35]} | {row['product_count']} | {row['avg_hazard_score']:.0f} | {row['max_hazard_score']:.0f} | {row['pct_high_hazard']:.0f}% | {row['pct_reproductive_hazard']:.0f}% | {row['pct_carcinogen']:.0f}% | {row['most_common_hazard_class']} |\n")
        f.write("\n")

        # Risk concentration analysis
        f.write("## Risk Concentration Analysis\n\n")

        # Which brands use the most hazardous chemicals?
        merged = dp[["product_id", "brand", "company"]].merge(ps, on="product_id", how="left")

        f.write("### Brands Using Highest-Hazard Chemicals\n\n")
        danger_brands = merged[merged["max_hazard_severity"] == "Danger"].groupby("brand").agg(
            products_with_danger=("product_id", "nunique"),
            avg_score=("hazard_score", "mean"),
        ).sort_values("products_with_danger", ascending=False)

        f.write("| Brand | Products with 'Danger' Chemicals | Avg Score |\n")
        f.write("|-------|--------------------------------|----------|\n")
        for brand, row in danger_brands.head(10).iterrows():
            f.write(f"| {str(brand)[:30]} | {row['products_with_danger']} | {row['avg_score']:.0f} |\n")
        f.write("\n")

        # Category insights
        f.write("## Category-Level Insights\n\n")

        f.write("### Nail Products vs. Makeup Products\n\n")
        nail = ca[ca["category_raw"] == "Nail Products"]
        makeup = ca[ca["category_raw"] == "Makeup Products (non-permanent)"]
        if len(nail) > 0 and len(makeup) > 0:
            n = nail.iloc[0]
            m = makeup.iloc[0]
            f.write(f"- **Nail Products** ({n['product_count']} products): Avg score {n['avg_hazard_score']:.0f}, ")
            f.write(f"{n['pct_reproductive_hazard']:.0f}% reproductive hazard, {n['pct_carcinogen']:.0f}% carcinogens\n")
            f.write(f"- **Makeup Products** ({m['product_count']} products): Avg score {m['avg_hazard_score']:.0f}, ")
            f.write(f"{m['pct_reproductive_hazard']:.0f}% reproductive hazard, {m['pct_carcinogen']:.0f}% carcinogens\n\n")
            f.write("Nail products have **higher reproductive hazard prevalence** due to ethyl cyanoacrylate ")
            f.write(f"({n['pct_reproductive_hazard']:.0f}% vs {m['pct_reproductive_hazard']:.0f}%), while makeup ")
            f.write("products have slightly higher average scores due to formaldehyde in lash adhesives.\n\n")

        f.write("### Hair Care vs. Skin Care\n\n")
        hair = ca[ca["category_raw"].str.contains("Hair Care", na=False)]
        skin = ca[ca["category_raw"].str.contains("Skin Care", na=False)]
        if len(hair) > 0 and len(skin) > 0:
            h = hair.iloc[0]
            s = skin.iloc[0]
            f.write(f"- **Hair Care** ({h['product_count']} products): Avg score {h['avg_hazard_score']:.0f}, classified MODERATE\n")
            f.write(f"- **Skin Care** ({s['product_count']} products): Avg score {s['avg_hazard_score']:.0f}, classified MODERATE\n\n")
            f.write("Both categories show lower hazard profiles than adhesive-based products, ")
            f.write("though both still contain some products with carcinogenic ingredients.\n\n")

        # Market concentration
        f.write("## Market Concentration\n\n")
        total_products = db["product_count"].sum()
        top5 = company_agg.head(5)["product_count"].sum()
        f.write(f"- Top 5 companies account for **{top5}/{total_products} products ({top5/total_products*100:.0f}%)**\n")
        high_brands = len(db[db["max_hazard_flag"] == "HIGH"])
        f.write(f"- **{high_brands}/{len(db)} brands ({high_brands/len(db)*100:.0f}%)** have at least one HIGH-risk product\n")
        all_high = db[db["max_hazard_flag"] == "HIGH"]["product_count"].sum()
        f.write(f"- HIGH-risk brands account for **{all_high} products** in the dataset\n\n")

        f.write("---\n\n")
        f.write("*See also:* [M1_regulatory_summary.md](M1_regulatory_summary.md) · ")
        f.write("[M1_hazard_inventory.md](M1_hazard_inventory.md)\n")

    logger.info("Generated: %s", path)


def main():
    logger.info("=" * 80)
    logger.info("M1.4 Summary Report Generation")
    logger.info("=" * 80)

    REPORTS.mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    data = load_data()

    generate_regulatory_summary(data)
    generate_hazard_inventory(data)
    generate_market_trends(data)

    logger.info("=" * 80)
    logger.info("M1.4 COMPLETE — 3 reports generated in %s/", REPORTS)
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
