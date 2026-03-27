"""
CSCP CSV Extraction Module

Parses the CSCP chemicals in cosmetics CSV into a standardized DataFrame.
"""

import pandas as pd
from pathlib import Path


PRIMARY_KWS = [
    "glue", "adhesive", "bond", "bonding",
    "wig", "lace", "weave", "closure", "frontal"
]


def parse_cscp_csv(csv_path: str) -> pd.DataFrame:
    """
    Parse CSCP CSV into standardized columns, filtered for hair glue products.

    Returns DataFrame with columns:
    - product_name
    - brand
    - company
    - category_raw
    - ingredient_raw
    - casrn
    - upc_gtin
    - ingredient_normalized
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSCP CSV not found: {csv_path}")

    # Read CSV - adjust dtypes and parsing as needed
    df = pd.read_csv(path, dtype=str, low_memory=False)

    # Standardize column names
    column_mapping = {
        "ProductName": "product_name",
        "BrandName": "brand",
        "CompanyName": "company",
        "PrimaryCategory": "category_raw",
        "ChemicalName": "ingredient_raw",
        "CasNumber": "casrn",
    }

    df = df.rename(columns=column_mapping)

    # Ensure required columns exist
    required_cols = ["product_name", "brand", "company", "category_raw",
                     "ingredient_raw", "casrn"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in CSCP CSV: {missing_cols}")

    # Add upc_gtin as None since not in CSV
    df["upc_gtin"] = None

    # Add ingredient_normalized
    df["ingredient_normalized"] = df["ingredient_raw"].str.lower().str.strip()

    # Filter for hair glue products
    df = keyword_filter(df)

    return df[required_cols + ["upc_gtin", "ingredient_normalized"]]


def keyword_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame for hair glue products using primary keywords.
    """
    txt = (
        df["category_raw"].astype("string").fillna("") + " " +
        df["product_name"].astype("string").fillna("")
    ).str.lower()

    hit = txt.apply(lambda s: any(k in s for k in PRIMARY_KWS))
    filtered = df[hit].copy()
    return filtered