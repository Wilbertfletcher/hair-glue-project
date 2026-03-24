from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# --------- CONFIG ---------
CSV_PATH = Path("data/raw/cscp_chemicals_in_cosmetics.csv")  # change if your filename differs
FIG_DIR = Path("figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY_KWS = [
    "glue", "adhesive", "bond", "bonding",
    "wig", "lace", "weave", "closure", "frontal"
]

TOP_N_ING = 25
TOP_N_BRANDS = 20


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    return df


def _pick(df: pd.DataFrame, *candidates: str) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_cscp(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)
    df = norm_cols(df)

    col_product = _pick(df, "productname", "labelname", "product")
    col_brand = _pick(df, "brandname", "brand")
    col_company = _pick(df, "companyname", "manufacturer", "company")
    col_category = _pick(df, "primarycategory", "subcategory", "category", "producttype")
    col_ingredient = _pick(df, "chemicalname", "ingredientname", "chemical", "ingredient")
    col_cas = _pick(df, "casnumber", "cas", "casrn", "cas#")

    out = pd.DataFrame({
        "product_name": df[col_product] if col_product else pd.NA,
        "brand": df[col_brand] if col_brand else pd.NA,
        "company": df[col_company] if col_company else pd.NA,
        "category_raw": df[col_category] if col_category else pd.NA,
        "ingredient_raw": df[col_ingredient] if col_ingredient else pd.NA,
        "casrn": df[col_cas] if col_cas else pd.NA,
    })

    out = out.dropna(subset=["product_name", "ingredient_raw"])
    return out


def keyword_filter(df: pd.DataFrame) -> pd.DataFrame:
    txt = (
        df["category_raw"].astype("string").fillna("") + " " +
        df["product_name"].astype("string").fillna("")
    ).str.lower()

    hit = txt.apply(lambda s: any(k in s for k in PRIMARY_KWS))
    filtered = df[hit].copy()
    filtered["filter_rule"] = "primary_keywords"
    return filtered


def plot_bar(series: pd.Series, title: str, xlabel: str, outfile: Path, top_n: int = 20):
    counts = series.value_counts(dropna=True).head(top_n)
    plt.figure(figsize=(10, 6))
    counts.sort_values().plot(kind="barh")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(outfile, dpi=200)
    plt.close()


def main():
    df = load_cscp(CSV_PATH)
    print(f"Loaded rows: {len(df):,}")

    glue_df = keyword_filter(df)
    print(f"Hair-glue subset rows: {len(glue_df):,}")
    print("Example categories:", glue_df["category_raw"].dropna().unique()[:10])

    # Plot 1: Top categories
    plot_bar(
        glue_df["category_raw"].astype("string"),
        title="Top CSCP Categories (Hair Glue / Weave Adhesives Subset)",
        xlabel="Count of rows (product-ingredient records)",
        outfile=FIG_DIR / "explore_1_top_categories_hair_glue.png",
        top_n=25,
    )

    # Plot 2: Top ingredients
    plot_bar(
        glue_df["ingredient_raw"].astype("string"),
        title=f"Top Ingredients (Hair Glue Subset) — Top {TOP_N_ING}",
        xlabel="Count of occurrences",
        outfile=FIG_DIR / "explore_2_top_ingredients_hair_glue.png",
        top_n=TOP_N_ING,
    )

    # Plot 3: CAS missingness by category
    cas_missing = glue_df.assign(
        cas_missing=glue_df["casrn"].isna() | (glue_df["casrn"].astype("string").str.strip() == "")
    )
    miss_by_cat = (
        cas_missing.groupby("category_raw", dropna=True)["cas_missing"]
        .mean()
        .sort_values(ascending=False)
        .head(25)
    )
    plt.figure(figsize=(10, 6))
    miss_by_cat.sort_values().plot(kind="barh")
    plt.title("CASRN Missingness Rate by Category (Hair Glue Subset)")
    plt.xlabel("Fraction missing CASRN")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "explore_3_cas_missingness_by_category.png", dpi=200)
    plt.close()

    # Plot 4: Top brands (extra)
    plot_bar(
        glue_df["brand"].astype("string"),
        title=f"Top Brands (Hair Glue Subset) — Top {TOP_N_BRANDS}",
        xlabel="Count of rows (product-ingredient records)",
        outfile=FIG_DIR / "explore_4_top_brands_hair_glue.png",
        top_n=TOP_N_BRANDS,
    )

    # Save summary for notes
    summary = {
        "total_rows": len(df),
        "hair_glue_rows": len(glue_df),
        "hair_glue_unique_products": glue_df["product_name"].nunique(),
        "hair_glue_unique_ingredients": glue_df["ingredient_raw"].nunique(),
        "hair_glue_cas_present_rate": float(
            (~(glue_df["casrn"].isna() | (glue_df["casrn"].astype("string").str.strip() == ""))).mean()
        ),
        "filter_rule": glue_df["filter_rule"].iloc[0] if len(glue_df) else "n/a",
        "primary_keywords": ", ".join(PRIMARY_KWS),
    }
    pd.Series(summary).to_csv("exploration/exploration_summary.csv", header=False)
    print("Done. Check the figures/ folder and exploration/exploration_summary.csv")


if __name__ == "__main__":
    main()