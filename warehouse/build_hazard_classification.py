#!/usr/bin/env python3
"""
Hair Glue Project — M1.2 Hazard Classification & Risk Scoring

Builds:
1. warehouse/dim_hazard_classes.parquet — GHS hazard class dimension
2. warehouse/fact_chemical_hazards.parquet — Chemical-to-hazard bridge table
3. warehouse/product_hazard_summary.parquet — Per-product risk scores

Risk scoring logic (from ROADMAP-M1.md):
  HIGH:   max_severity="Danger" OR reproductive>0 OR carcinogen>0
  MEDIUM: max_severity="Warning" AND no reproductive/carcinogen
  LOW:    num_hazardous=0 AND match_confidence>0.8
  NO_DATA: match_confidence<0.5

Score formula (0-100, capped):
  +50 per "Danger" hazard, +25 per "Warning" hazard
  +15 per reproductive hazard chemical
  +10 per suspected carcinogen, +20 per confirmed carcinogen
  +10 if match_confidence<0.5 (uncertainty penalty)
  -5 if match_confidence>=0.9 (confidence bonus)
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/M1.2_hazard_classification.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

WAREHOUSE = Path("warehouse")
REPORTS = Path("reports")
LOGS = Path("logs")

# GHS hazard class definitions
HAZARD_CLASS_DEFS = {
    "Acute Tox": ("Health", "Danger", "Substances that cause death or serious harm from short-term exposure via oral, dermal, or inhalation routes", "multiple organs"),
    "Skin Corr": ("Health", "Danger", "Substances that cause irreversible skin damage", "skin"),
    "Skin Irrit": ("Health", "Warning", "Substances that cause reversible skin irritation", "skin"),
    "Skin Sens": ("Health", "Warning", "Substances that cause allergic skin reactions", "skin, immune system"),
    "Eye Damage": ("Health", "Danger", "Substances that cause irreversible eye damage", "eyes"),
    "Eye Irrit": ("Health", "Warning", "Substances that cause reversible eye irritation", "eyes"),
    "Resp Sens": ("Health", "Danger", "Substances that cause allergy or asthma if inhaled", "respiratory system, immune system"),
    "Resp Irrit": ("Health", "Warning", "Substances that irritate the respiratory tract", "respiratory system"),
    "Muta": ("Health", "Warning/Danger", "Substances that may cause genetic defects", "germ cells"),
    "Carc": ("Health", "Warning/Danger", "Substances suspected or known to cause cancer", "multiple organs"),
    "Repr/Dev": ("Health", "Danger", "Substances toxic to reproduction or development", "reproductive system"),
    "STOT-SE": ("Health", "Danger", "Specific target organ toxicity from single exposure", "varies"),
    "STOT-RE": ("Health", "Danger", "Specific target organ toxicity from repeated exposure", "varies"),
    "Aquatic Acute": ("Environmental", "Warning", "Substances toxic to aquatic organisms (acute)", None),
    "Aquatic Chronic": ("Environmental", "Warning", "Substances toxic to aquatic organisms (chronic)", None),
    "Flam Liq": ("Physical", "Danger", "Flammable liquids", None),
    "Flam Gas": ("Physical", "Danger", "Flammable gases", None),
    "Flam Aer": ("Physical", "Danger", "Flammable aerosols", None),
    "Flam Sol": ("Physical", "Danger", "Flammable solids", None),
    "Gas Press": ("Physical", "Warning", "Gases under pressure", None),
}


def build_dim_hazard_classes(hazard_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_hazard_classes from all unique GHS classes found in hazard data."""
    all_classes = set()
    for row in hazard_df["ghs_hazard_class"].dropna():
        for cls in str(row).split("|"):
            cls = cls.strip()
            if cls:
                all_classes.add(cls)

    records = []
    for i, cls in enumerate(sorted(all_classes), start=1):
        cat, signal, defn, organs = HAZARD_CLASS_DEFS.get(cls, ("Unknown", "Unknown", cls, None))
        records.append({
            "hazard_id": i,
            "hazard_class": cls,
            "hazard_category": cat,
            "signal_word": signal,
            "definition": defn,
            "target_organs": organs,
        })

    df = pd.DataFrame(records)
    logger.info(f"Built dim_hazard_classes: {len(df)} unique hazard classes")
    return df


def build_fact_chemical_hazards(hazard_df: pd.DataFrame, dim_hazard: pd.DataFrame) -> pd.DataFrame:
    """Build bridge table linking chemicals to hazard classes."""
    hazard_map = dict(zip(dim_hazard["hazard_class"], dim_hazard["hazard_id"]))

    records = []
    for chem_idx, row in hazard_df.iterrows():
        if pd.isna(row["ghs_hazard_class"]):
            continue
        h_codes = str(row["h_codes"] or "").split("|") if pd.notna(row["h_codes"]) else []
        classes = str(row["ghs_hazard_class"]).split("|")

        for cls in classes:
            cls = cls.strip()
            if cls not in hazard_map:
                continue
            # Find corresponding H-code(s) for this class
            H_CODE_TO_CLASS = {
                "H300": "Acute Tox", "H301": "Acute Tox", "H302": "Acute Tox", "H303": "Acute Tox",
                "H310": "Acute Tox", "H311": "Acute Tox", "H312": "Acute Tox", "H313": "Acute Tox",
                "H330": "Acute Tox", "H331": "Acute Tox", "H332": "Acute Tox", "H333": "Acute Tox",
                "H314": "Skin Corr", "H315": "Skin Irrit", "H316": "Skin Irrit",
                "H317": "Skin Sens",
                "H318": "Eye Damage", "H319": "Eye Irrit",
                "H334": "Resp Sens", "H335": "Resp Irrit",
                "H340": "Muta", "H341": "Muta",
                "H350": "Carc", "H350i": "Carc", "H351": "Carc",
                "H360": "Repr/Dev", "H361": "Repr/Dev", "H362": "Repr/Dev",
                "H370": "STOT-SE", "H371": "STOT-SE",
                "H372": "STOT-RE", "H373": "STOT-RE",
                "H400": "Aquatic Acute", "H401": "Aquatic Acute", "H402": "Aquatic Acute",
                "H410": "Aquatic Chronic", "H411": "Aquatic Chronic", "H412": "Aquatic Chronic", "H413": "Aquatic Chronic",
                "H220": "Flam Gas", "H221": "Flam Gas", "H222": "Flam Aer", "H223": "Flam Aer",
                "H224": "Flam Liq", "H225": "Flam Liq", "H226": "Flam Liq", "H227": "Flam Liq",
                "H228": "Flam Sol",
                "H280": "Gas Press", "H281": "Gas Press",
            }
            relevant_h = [h for h in h_codes if H_CODE_TO_CLASS.get(h) == cls]
            h_code = relevant_h[0] if relevant_h else None

            records.append({
                "chemical_id": chem_idx,
                "hazard_id": hazard_map[cls],
                "ghs_h_code": h_code,
                "ghs_p_code": None,
                "source_data": row["data_source"],
            })

    df = pd.DataFrame(records)
    logger.info(f"Built fact_chemical_hazards: {len(df)} chemical-hazard links")
    return df


def build_product_hazard_summary(
    dim_products: pd.DataFrame,
    fact_pi: pd.DataFrame,
    hazard_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build product-level hazard summaries with risk scores."""
    # Create a lookup: casrn → hazard record
    hazard_by_casrn = {}
    for _, row in hazard_df.iterrows():
        if pd.notna(row["casrn"]):
            hazard_by_casrn[row["casrn"]] = row

    # Also create ingredient_name → hazard record for unmatched
    hazard_by_name = {}
    for _, row in hazard_df.iterrows():
        if pd.notna(row["canonical_name"]):
            hazard_by_name[str(row["canonical_name"]).lower()] = row

    records = []
    for _, prod in dim_products.iterrows():
        pid = prod["product_id"]
        pname = prod["product_name"]

        # Get ingredients for this product
        prod_ingredients = fact_pi[fact_pi["product_id"] == pid]
        num_ingredients = len(prod_ingredients)

        # Collect hazard data for each ingredient
        num_hazardous = 0
        max_severity = None  # None < "Warning" < "Danger"
        all_classes = set()
        repro_count = 0
        carc_count = 0
        danger_count = 0
        warning_count = 0
        avg_confidence = []

        for _, ing in prod_ingredients.iterrows():
            casrn = ing.get("casrn")
            haz = None
            if pd.notna(casrn) and casrn in hazard_by_casrn:
                haz = hazard_by_casrn[casrn]

            if haz is None:
                continue

            conf = haz.get("match_confidence", 0)
            avg_confidence.append(conf)

            if pd.notna(haz.get("ghs_hazard_class")):
                num_hazardous += 1
                classes = str(haz["ghs_hazard_class"]).split("|")
                all_classes.update(cls.strip() for cls in classes)

                signal = haz.get("ghs_signal_word")
                if signal == "Danger":
                    danger_count += 1
                    max_severity = "Danger"
                elif signal == "Warning":
                    warning_count += 1
                    if max_severity != "Danger":
                        max_severity = "Warning"

                if haz.get("reproductive_hazard"):
                    repro_count += 1
                if pd.notna(haz.get("carcinogenicity")):
                    carc_count += 1

        # Calculate hazard score
        score = 0.0
        score += danger_count * 50
        score += warning_count * 25
        score += repro_count * 15
        for _, ing in prod_ingredients.iterrows():
            casrn = ing.get("casrn")
            if pd.notna(casrn) and casrn in hazard_by_casrn:
                haz = hazard_by_casrn[casrn]
                carc = haz.get("carcinogenicity")
                if carc == "Confirmed":
                    score += 20
                elif carc == "Suspected":
                    score += 10

        mean_conf = sum(avg_confidence) / len(avg_confidence) if avg_confidence else 0
        if mean_conf >= 0.9:
            score -= 5
        if mean_conf < 0.5:
            score += 10
        score = min(max(score, 0), 100)

        # Determine hazard flag
        if mean_conf < 0.5 and num_hazardous == 0:
            flag = "NO_DATA"
        elif max_severity == "Danger" or repro_count > 0 or carc_count > 0:
            flag = "HIGH"
        elif max_severity == "Warning":
            flag = "MEDIUM"
        elif num_hazardous == 0 and mean_conf > 0.8:
            flag = "LOW"
        else:
            flag = "NO_DATA"

        records.append({
            "product_id": pid,
            "product_name": pname,
            "num_ingredients": num_ingredients,
            "num_hazardous_ingredients": num_hazardous,
            "max_hazard_severity": max_severity,
            "hazard_classes_present": "|".join(sorted(all_classes)) if all_classes else None,
            "reproductive_hazard_ingredient_count": repro_count,
            "carcinogen_count": carc_count,
            "hazard_flag": flag,
            "hazard_score": round(score, 1),
        })

    df = pd.DataFrame(records)
    logger.info(f"Built product_hazard_summary: {len(df)} products")
    return df


def generate_report(
    dim_hazard: pd.DataFrame,
    fact_ch: pd.DataFrame,
    prod_summary: pd.DataFrame,
):
    """Generate M1.2 hazard classification report."""
    report_path = REPORTS / "M1.2_hazard_classification_report.md"
    today = date.today().isoformat()

    with open(report_path, "w") as f:
        f.write("# Hair Glue Project — M1.2 Hazard Classification Report\n\n")
        f.write(f"**Generated:** {today}\n\n")

        # Summary
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total products analyzed:** {len(prod_summary)}\n")
        for flag in ["HIGH", "MEDIUM", "LOW", "NO_DATA"]:
            cnt = len(prod_summary[prod_summary["hazard_flag"] == flag])
            pct = cnt / len(prod_summary) * 100
            f.write(f"- **{flag}:** {cnt} products ({pct:.1f}%)\n")
        f.write(f"- **Average hazard score:** {prod_summary['hazard_score'].mean():.1f}\n")
        f.write(f"- **Max hazard score:** {prod_summary['hazard_score'].max():.1f}\n\n")

        # Hazard flag distribution
        f.write("## Hazard Flag Distribution\n\n")
        f.write("| Flag | Count | % | Avg Score |\n")
        f.write("|------|-------|---|----------|\n")
        for flag in ["HIGH", "MEDIUM", "LOW", "NO_DATA"]:
            subset = prod_summary[prod_summary["hazard_flag"] == flag]
            cnt = len(subset)
            pct = cnt / len(prod_summary) * 100
            avg_score = subset["hazard_score"].mean() if cnt > 0 else 0
            f.write(f"| {flag} | {cnt} | {pct:.1f}% | {avg_score:.1f} |\n")
        f.write("\n")

        # GHS hazard class distribution
        f.write("## GHS Hazard Classes Found\n\n")
        f.write("| Hazard Class | Signal Word | Category | Definition |\n")
        f.write("|-------------|-------------|----------|------------|\n")
        for _, row in dim_hazard.iterrows():
            f.write(f"| {row['hazard_class']} | {row['signal_word']} | {row['hazard_category']} | {row['definition'][:60]}... |\n")
        f.write("\n")

        # Top 10 highest-risk products
        f.write("## Top 10 Highest-Risk Products\n\n")
        f.write("| Rank | Product | Score | Flag | Hazard Classes | Repro | Carc |\n")
        f.write("|------|---------|-------|------|---------------|-------|------|\n")
        top10 = prod_summary.nlargest(10, "hazard_score")
        for rank, (_, row) in enumerate(top10.iterrows(), 1):
            name = str(row["product_name"])[:40]
            classes = str(row["hazard_classes_present"] or "—")[:30]
            f.write(f"| {rank} | {name} | {row['hazard_score']:.0f} | {row['hazard_flag']} | {classes} | {row['reproductive_hazard_ingredient_count']} | {row['carcinogen_count']} |\n")
        f.write("\n")

        # Products with reproductive hazards
        repro_products = prod_summary[prod_summary["reproductive_hazard_ingredient_count"] > 0]
        f.write(f"## Reproductive Hazard Products ({len(repro_products)})\n\n")
        if len(repro_products) > 0:
            f.write("| Product | # Repro Ingredients | Score |\n")
            f.write("|---------|-------------------|-------|\n")
            for _, row in repro_products.iterrows():
                f.write(f"| {str(row['product_name'])[:50]} | {row['reproductive_hazard_ingredient_count']} | {row['hazard_score']:.0f} |\n")
        f.write("\n")

        # Carcinogen products
        carc_products = prod_summary[prod_summary["carcinogen_count"] > 0]
        f.write(f"## Products Containing Carcinogens ({len(carc_products)})\n\n")
        if len(carc_products) > 0:
            f.write("| Product | # Carcinogenic Ingredients | Score |\n")
            f.write("|---------|--------------------------|-------|\n")
            for _, row in carc_products.iterrows():
                f.write(f"| {str(row['product_name'])[:50]} | {row['carcinogen_count']} | {row['hazard_score']:.0f} |\n")
        f.write("\n")

        # Score distribution
        f.write("## Hazard Score Distribution\n\n")
        bins = [(0, 25, "Low (0-25)"), (25, 50, "Moderate (25-50)"), (50, 75, "High (50-75)"), (75, 101, "Very High (75-100)")]
        f.write("| Range | Count | % |\n")
        f.write("|-------|-------|---|\n")
        for lo, hi, label in bins:
            cnt = len(prod_summary[(prod_summary["hazard_score"] >= lo) & (prod_summary["hazard_score"] < hi)])
            pct = cnt / len(prod_summary) * 100
            f.write(f"| {label} | {cnt} | {pct:.1f}% |\n")
        f.write("\n")

    logger.info(f"Report: {report_path}")


def main():
    logger.info("=" * 80)
    logger.info("M1.2 Hazard Classification & Risk Scoring")
    logger.info("=" * 80)

    WAREHOUSE.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)

    # Load inputs
    hazard_df = pd.read_parquet(WAREHOUSE / "ref_chemicals_hazard.parquet")
    dim_products = pd.read_parquet(WAREHOUSE / "dim_products.parquet")
    fact_pi = pd.read_parquet(WAREHOUSE / "fact_product_ingredients.parquet")
    logger.info(f"Loaded: {len(hazard_df)} chemicals, {len(dim_products)} products, {len(fact_pi)} fact rows")

    # Build dimension tables
    dim_hazard = build_dim_hazard_classes(hazard_df)
    dim_hazard.to_parquet(WAREHOUSE / "dim_hazard_classes.parquet", index=False)
    logger.info(f"Saved: dim_hazard_classes.parquet ({len(dim_hazard)} rows)")

    # Build bridge table
    fact_ch = build_fact_chemical_hazards(hazard_df, dim_hazard)
    fact_ch.to_parquet(WAREHOUSE / "fact_chemical_hazards.parquet", index=False)
    logger.info(f"Saved: fact_chemical_hazards.parquet ({len(fact_ch)} rows)")

    # Build product hazard summary
    prod_summary = build_product_hazard_summary(dim_products, fact_pi, hazard_df)
    prod_summary.to_parquet(WAREHOUSE / "product_hazard_summary.parquet", index=False)
    logger.info(f"Saved: product_hazard_summary.parquet ({len(prod_summary)} rows)")

    # Generate report
    generate_report(dim_hazard, fact_ch, prod_summary)

    # Log summary
    for flag in ["HIGH", "MEDIUM", "LOW", "NO_DATA"]:
        cnt = len(prod_summary[prod_summary["hazard_flag"] == flag])
        logger.info(f"  {flag}: {cnt} products")

    logger.info("=" * 80)
    logger.info("M1.2 COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
