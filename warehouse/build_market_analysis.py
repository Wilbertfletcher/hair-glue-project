#!/usr/bin/env python3
"""
Hair Glue Project — M1.3 Brand/Manufacturer Market Analysis & Risk Exposure

Builds:
1. warehouse/dim_brands.parquet — Brand dimension with aggregate hazard metrics
2. warehouse/category_hazard_analysis.parquet — Category-level hazard analysis
3. reports/M1.3_brand_market_analysis.md — Market risk report
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/M1.3_market_analysis.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE = Path("warehouse")
REPORTS = Path("reports")
LOGS = Path("logs")

FLAG_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NO_DATA": 0}


def build_dim_brands(dim_products: pd.DataFrame, prod_summary: pd.DataFrame) -> pd.DataFrame:
    """Build brand dimension with aggregate hazard metrics."""
    merged = dim_products.merge(
        prod_summary[["product_id", "hazard_score", "hazard_flag",
                       "reproductive_hazard_ingredient_count", "carcinogen_count"]],
        on="product_id",
        how="left",
    )

    brands = (
        merged.groupby(["brand", "company"])
        .agg(
            product_count=("product_id", "nunique"),
            avg_hazard_score=("hazard_score", "mean"),
            max_hazard_score=("hazard_score", "max"),
            total_repro_products=("reproductive_hazard_ingredient_count", lambda x: (x > 0).sum()),
            total_carc_products=("carcinogen_count", lambda x: (x > 0).sum()),
            hazard_flags=("hazard_flag", list),
        )
        .reset_index()
    )

    # Determine max_hazard_flag per brand
    brands["max_hazard_flag"] = brands["hazard_flags"].apply(
        lambda flags: max(flags, key=lambda f: FLAG_ORDER.get(f, 0))
    )
    brands.drop(columns=["hazard_flags"], inplace=True)

    # Add synthetic brand_id
    brands.insert(0, "brand_id", range(1, len(brands) + 1))
    brands["avg_hazard_score"] = brands["avg_hazard_score"].round(1)
    brands["max_hazard_score"] = brands["max_hazard_score"].round(1)

    logger.info(f"Built dim_brands: {len(brands)} brands")
    return brands


def build_category_analysis(dim_products: pd.DataFrame, prod_summary: pd.DataFrame) -> pd.DataFrame:
    """Build category-level hazard analysis."""
    merged = dim_products[["product_id", "category_raw"]].merge(
        prod_summary, on="product_id", how="left",
    )

    cats = (
        merged.groupby("category_raw")
        .agg(
            product_count=("product_id", "nunique"),
            avg_hazard_score=("hazard_score", "mean"),
            max_hazard_score=("hazard_score", "max"),
            pct_high_hazard=("hazard_flag", lambda x: (x == "HIGH").sum() / len(x) * 100),
            pct_reproductive_hazard=("reproductive_hazard_ingredient_count", lambda x: (x > 0).sum() / len(x) * 100),
            pct_carcinogen=("carcinogen_count", lambda x: (x > 0).sum() / len(x) * 100),
        )
        .reset_index()
    )

    # Most common hazard class per category
    def most_common_class(cat_name):
        cat_products = merged[merged["category_raw"] == cat_name]
        all_classes = []
        for classes in cat_products["hazard_classes_present"].dropna():
            all_classes.extend(str(classes).split("|"))
        if not all_classes:
            return "—"
        return pd.Series(all_classes).value_counts().index[0]

    cats["most_common_hazard_class"] = cats["category_raw"].apply(most_common_class)

    # Recommendations
    def make_recommendation(row):
        if row["pct_high_hazard"] > 80:
            return "HIGH RISK — Most products contain dangerous chemicals. Prioritize for regulatory review."
        elif row["pct_carcinogen"] > 50:
            return "CARCINOGEN CONCERN — Majority of products contain suspected/confirmed carcinogens."
        elif row["pct_reproductive_hazard"] > 50:
            return "REPRODUCTIVE CONCERN — Majority of products contain reproductive toxicants."
        elif row["avg_hazard_score"] > 50:
            return "ELEVATED RISK — Above-average hazard scores. Monitor ingredient trends."
        else:
            return "MODERATE — Hazard levels are within acceptable ranges for the category."

    cats["recommendation"] = cats.apply(make_recommendation, axis=1)

    # Round
    for col in ["avg_hazard_score", "max_hazard_score", "pct_high_hazard",
                 "pct_reproductive_hazard", "pct_carcinogen"]:
        cats[col] = cats[col].round(1)

    logger.info(f"Built category_hazard_analysis: {len(cats)} categories")
    return cats


def generate_report(
    dim_brands: pd.DataFrame,
    cat_analysis: pd.DataFrame,
    prod_summary: pd.DataFrame,
    dim_products: pd.DataFrame,
):
    """Generate M1.3 brand market analysis report."""
    report_path = REPORTS / "M1.3_brand_market_analysis.md"
    today = date.today().isoformat()

    with open(report_path, "w") as f:
        f.write("# Hair Glue Project — M1.3 Brand & Market Analysis Report\n\n")
        f.write(f"**Generated:** {today}\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total brands analyzed:** {len(dim_brands)}\n")
        f.write(f"- **Total companies:** {dim_brands['company'].nunique()}\n")
        f.write(f"- **Product categories:** {len(cat_analysis)}\n")
        high_brands = len(dim_brands[dim_brands["max_hazard_flag"] == "HIGH"])
        f.write(f"- **Brands with HIGH-risk products:** {high_brands} ({high_brands/len(dim_brands)*100:.0f}%)\n\n")

        # Top 15 riskiest brands
        f.write("## Top 15 Highest-Risk Brands\n\n")
        f.write("| Rank | Brand | Company | Products | Avg Score | Max Score | Flag | Repro | Carc |\n")
        f.write("|------|-------|---------|----------|-----------|-----------|------|-------|------|\n")
        top_brands = dim_brands.nlargest(15, "avg_hazard_score")
        for rank, (_, row) in enumerate(top_brands.iterrows(), 1):
            brand = str(row["brand"])[:25]
            company = str(row["company"])[:25]
            f.write(
                f"| {rank} | {brand} | {company} | {row['product_count']} | "
                f"{row['avg_hazard_score']:.0f} | {row['max_hazard_score']:.0f} | "
                f"{row['max_hazard_flag']} | {row['total_repro_products']} | {row['total_carc_products']} |\n"
            )
        f.write("\n")

        # Category analysis
        f.write("## Category Hazard Analysis\n\n")
        f.write("| Category | Products | Avg Score | % HIGH | % Repro | % Carc | Most Common Hazard | Recommendation |\n")
        f.write("|----------|----------|-----------|--------|---------|--------|-------------------|----------------|\n")
        for _, row in cat_analysis.sort_values("avg_hazard_score", ascending=False).iterrows():
            cat = str(row["category_raw"])[:30]
            rec = str(row["recommendation"])[:40]
            f.write(
                f"| {cat} | {row['product_count']} | {row['avg_hazard_score']:.0f} | "
                f"{row['pct_high_hazard']:.0f}% | {row['pct_reproductive_hazard']:.0f}% | "
                f"{row['pct_carcinogen']:.0f}% | {row['most_common_hazard_class']} | {rec}... |\n"
            )
        f.write("\n")

        # Companies with most products
        f.write("## Top 10 Companies by Product Count\n\n")
        f.write("| Company | Brands | Products | Avg Score | Max Flag |\n")
        f.write("|---------|--------|----------|-----------|----------|\n")
        company_agg = (
            dim_brands.groupby("company")
            .agg(
                brand_count=("brand", "nunique"),
                product_count=("product_count", "sum"),
                avg_score=("avg_hazard_score", "mean"),
                max_flag=("max_hazard_flag", lambda x: max(x, key=lambda f: FLAG_ORDER.get(f, 0))),
            )
            .nlargest(10, "product_count")
        )
        for company, row in company_agg.iterrows():
            f.write(f"| {str(company)[:30]} | {row['brand_count']} | {row['product_count']} | {row['avg_score']:.0f} | {row['max_flag']} |\n")
        f.write("\n")

        # Key findings
        f.write("## Key Findings\n\n")
        high_pct = len(prod_summary[prod_summary["hazard_flag"] == "HIGH"]) / len(prod_summary) * 100
        f.write(f"1. **{high_pct:.0f}% of hair-glue products are classified HIGH risk** — "
                "driven primarily by formaldehyde, styrene, and other acute toxicants common in adhesive formulations.\n\n")

        worst_cat = cat_analysis.loc[cat_analysis["avg_hazard_score"].idxmax()]
        f.write(f"2. **Highest-risk category: {worst_cat['category_raw']}** — "
                f"average hazard score of {worst_cat['avg_hazard_score']:.0f} with "
                f"{worst_cat['pct_carcinogen']:.0f}% of products containing carcinogens.\n\n")

        repro_pct = len(prod_summary[prod_summary["reproductive_hazard_ingredient_count"] > 0]) / len(prod_summary) * 100
        f.write(f"3. **{repro_pct:.0f}% of products contain reproductive/developmental hazards** — "
                "these chemicals (H360/H361 classified) pose particular concern for consumer products.\n\n")

    logger.info(f"Report: {report_path}")


def main():
    logger.info("=" * 80)
    logger.info("M1.3 Brand/Manufacturer Market Analysis")
    logger.info("=" * 80)

    WAREHOUSE.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)

    dim_products = pd.read_parquet(WAREHOUSE / "dim_products.parquet")
    prod_summary = pd.read_parquet(WAREHOUSE / "product_hazard_summary.parquet")
    logger.info(f"Loaded: {len(dim_products)} products, {len(prod_summary)} hazard summaries")

    dim_brands = build_dim_brands(dim_products, prod_summary)
    dim_brands.to_parquet(WAREHOUSE / "dim_brands.parquet", index=False)
    logger.info(f"Saved: dim_brands.parquet ({len(dim_brands)} rows)")

    cat_analysis = build_category_analysis(dim_products, prod_summary)
    cat_analysis.to_parquet(WAREHOUSE / "category_hazard_analysis.parquet", index=False)
    logger.info(f"Saved: category_hazard_analysis.parquet ({len(cat_analysis)} rows)")

    generate_report(dim_brands, cat_analysis, prod_summary, dim_products)

    logger.info("=" * 80)
    logger.info("M1.3 COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
