from __future__ import annotations

from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Tuple

# --------- CONFIG ---------
CSV_PATH = Path("data/raw/cscp_chemicals_in_cosmetics.csv")
WAREHOUSE_DIR = Path("warehouse")
LOGS_DIR = Path("logs")
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY_KWS = [
    "glue", "adhesive", "bond", "bonding",
    "wig", "lace", "weave", "closure", "frontal"
]


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


def build_dimensions(glue_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Build the three dimension tables from filtered CSCP data.

    Returns:
        dim_products, dim_ingredients, fact_product_ingredients
    """

    # 1. Build dim_products
    # Group by (product_name, brand, company, category_raw) to deduplicate
    product_groups = glue_df.groupby(["product_name", "brand", "company", "category_raw"], dropna=False)
    dim_products = product_groups.size().reset_index(name="row_count")
    dim_products["product_id"] = range(1, len(dim_products) + 1)
    dim_products = dim_products[["product_id", "product_name", "brand", "company", "category_raw", "row_count"]]

    # 2. Build dim_ingredients
    # Group by ingredient_raw
    ingredient_groups = glue_df.groupby("ingredient_raw", dropna=False)
    dim_ingredients = ingredient_groups.agg(
        row_count=("ingredient_raw", "size"),
        cas_available=("casrn", lambda x: (~x.isna() & (x.astype(str).str.strip() != "")).any())
    ).reset_index()
    dim_ingredients["ingredient_id"] = range(1, len(dim_ingredients) + 1)
    dim_ingredients = dim_ingredients[["ingredient_id", "ingredient_raw", "cas_available", "row_count"]]

    # 3. Build fact table
    # First, add product_id and ingredient_id to the original data
    fact_df = glue_df.copy()

    # Create product key for joining
    product_key_cols = ["product_name", "brand", "company", "category_raw"]
    product_keys = dim_products[product_key_cols + ["product_id"]].set_index(product_key_cols)
    fact_df = fact_df.join(product_keys, on=product_key_cols, how="left")

    # Create ingredient key for joining
    ingredient_keys = dim_ingredients[["ingredient_raw", "ingredient_id"]].set_index("ingredient_raw")
    fact_df = fact_df.join(ingredient_keys, on="ingredient_raw", how="left")

    # Group by (product_id, ingredient_id, casrn) to handle duplicates
    fact_groups = fact_df.groupby(["product_id", "ingredient_id", "casrn"], dropna=False)
    fact_product_ingredients = fact_groups.size().reset_index(name="source_row_count")

    # Handle CASRN conflicts: if same (product_id, ingredient_id) has multiple CASRN, keep the most common
    conflicts = fact_product_ingredients.groupby(["product_id", "ingredient_id"]).filter(lambda x: len(x) > 1)
    if not conflicts.empty:
        # For each conflicting group, keep the CASRN with highest source_row_count
        resolved = fact_product_ingredients.groupby(["product_id", "ingredient_id"], group_keys=False).apply(
            lambda x: x.nlargest(1, "source_row_count")
        )
        fact_product_ingredients = resolved

    return dim_products, dim_ingredients, fact_product_ingredients


def write_parquet_with_schema(df: pd.DataFrame, path: Path, name: str) -> None:
    """Write DataFrame to Parquet with explicit schema for consistency."""
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path)
    print(f"✓ Wrote {name}: {len(df)} rows, {len(df.columns)} columns")


def validate_foreign_keys(dim_products: pd.DataFrame, dim_ingredients: pd.DataFrame,
                         fact_table: pd.DataFrame) -> bool:
    """Validate that all foreign keys in fact table exist in dimension tables."""
    product_ids_valid = fact_table["product_id"].isin(dim_products["product_id"]).all()
    ingredient_ids_valid = fact_table["ingredient_id"].isin(dim_ingredients["ingredient_id"]).all()

    if not product_ids_valid:
        missing_products = fact_table[~fact_table["product_id"].isin(dim_products["product_id"])]["product_id"].unique()
        print(f"❌ Foreign key error: Missing product_ids in dim_products: {missing_products}")

    if not ingredient_ids_valid:
        missing_ingredients = fact_table[~fact_table["ingredient_id"].isin(dim_ingredients["ingredient_id"])]["ingredient_id"].unique()
        print(f"❌ Foreign key error: Missing ingredient_ids in dim_ingredients: {missing_ingredients}")

    return product_ids_valid and ingredient_ids_valid


def main():
    print("🚀 M0.2: Building Product & Ingredient Dimension Tables")
    print("=" * 60)

    # Load and filter data
    print("📥 Loading CSCP data...")
    df = load_cscp(CSV_PATH)
    print(f"✓ Loaded {len(df):,} rows from CSCP")

    print("🔍 Applying hair-glue keyword filter...")
    glue_df = keyword_filter(df)
    print(f"✓ Filtered to {len(glue_df):,} hair-glue rows")

    # Build dimensions
    print("🏗️  Building dimension tables...")
    dim_products, dim_ingredients, fact_table = build_dimensions(glue_df)

    print(f"✓ dim_products: {len(dim_products)} unique products")
    print(f"✓ dim_ingredients: {len(dim_ingredients)} unique ingredients")
    print(f"✓ fact_product_ingredients: {len(fact_table)} rows")

    # Validate foreign keys
    print("🔍 Validating foreign key integrity...")
    if validate_foreign_keys(dim_products, dim_ingredients, fact_table):
        print("✓ All foreign keys valid")
    else:
        print("❌ Foreign key validation failed!")
        return

    # Write Parquet files
    print("💾 Writing Parquet files...")
    write_parquet_with_schema(dim_products, WAREHOUSE_DIR / "dim_products.parquet", "dim_products")
    write_parquet_with_schema(dim_ingredients, WAREHOUSE_DIR / "dim_ingredients.parquet", "dim_ingredients")
    write_parquet_with_schema(fact_table, WAREHOUSE_DIR / "fact_product_ingredients.parquet", "fact_product_ingredients")

    # Calculate CASRN coverage stats
    casrn_coverage = (~fact_table["casrn"].isna() & (fact_table["casrn"].astype(str).str.strip() != "")).sum()
    casrn_total = len(fact_table)
    casrn_pct = casrn_coverage / casrn_total * 100 if casrn_total > 0 else 0

    # Check for conflicts resolved
    conflicts_resolved = len(glue_df) - len(fact_table)  # Original rows minus deduplicated rows

    # Write log
    log_path = LOGS_DIR / "M0.2_dimension_build.log"
    with open(log_path, "w") as f:
        f.write(f"[2026-03-25] M0.2 Dimension Build\n")
        f.write(f"- Rows in filtered CSCP: {len(glue_df)}\n")
        f.write(f"- Unique products: {len(dim_products)}\n")
        f.write(f"- Unique ingredients: {len(dim_ingredients)}\n")
        f.write(f"- fact table rows: {len(fact_table)}\n")
        f.write(f"- CASRN coverage: {casrn_pct:.1f}% ({casrn_coverage} not NULL)\n")
        f.write(f"- Conflicts resolved: {conflicts_resolved} (CASRN duplicates deduplicated)\n")

    print(f"📝 Log written to {log_path}")

    # Final verification
    print("🔍 Final verification...")
    for file in ["dim_products.parquet", "dim_ingredients.parquet", "fact_product_ingredients.parquet"]:
        path = WAREHOUSE_DIR / file
        if path.exists():
            table = pq.read_table(path)
            print(f"✓ {file}: {table.num_rows} rows, {table.num_columns} columns")
        else:
            print(f"❌ {file}: File not found!")

    print("\n🎉 M0.2 Complete! Dimension tables built successfully.")


if __name__ == "__main__":
    main()