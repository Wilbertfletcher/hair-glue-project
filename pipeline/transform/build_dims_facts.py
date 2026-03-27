"""
Dimension and Fact Table Building Module

Builds canonical dimension tables and bridge tables from CSCP data.
"""

import uuid
import pandas as pd


def build_dim_product(cscp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build dim_product dimension table.

    Deduplicates products by (product_name, brand, company, category_raw).
    """
    # Group by product attributes to deduplicate
    product_cols = ["product_name", "brand", "company", "category_raw"]
    dim_product = (
        cscp_df[product_cols]
        .drop_duplicates()
        .reset_index(drop=True)
        .assign(product_id=lambda df: range(1, len(df) + 1))
    )

    return dim_product[["product_id"] + product_cols]


def build_dim_chemical(cscp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build dim_chemical dimension table with hazard-ready schema.

    Deduplicates by (casrn if present else ingredient_normalized + preferred_name).
    All hazard fields are NULL by design (deferred to M2).
    """
    # Create base chemical records
    chemical_base = cscp_df[["ingredient_raw", "ingredient_normalized", "casrn"]].copy()

    # Deduplicate by casrn if present, else by normalized ingredient + raw name
    chemical_base["dedupe_key"] = chemical_base.apply(
        lambda row: row["casrn"] if pd.notna(row["casrn"]) and row["casrn"].strip()
        else f"{row['ingredient_normalized']}|{row['ingredient_raw']}",
        axis=1
    )

    dim_chemical = (
        chemical_base
        .drop_duplicates(subset=["dedupe_key"])
        .reset_index(drop=True)
        .assign(
            chemical_id=lambda df: [str(uuid.uuid4()) for _ in range(len(df))],
            preferred_name=lambda df: df["ingredient_raw"],  # placeholder
            inchikey=None,
            smiles=None,
            pubchem_cid=None,
            dtxsid=None,
            dtxcid=None,
            source_priority="UNRESOLVED_M1",
            hazard_status="PENDING_SOURCE",
            hazard_source=None,
            hazard_last_updated=None,
            ghs_classes=None,
            signal_word=None,
            hazard_statements=None,
            precautionary_statements=None,
        )
    )

    return dim_chemical[[
        "chemical_id", "preferred_name", "ingredient_normalized", "casrn", "dedupe_key",
        "inchikey", "smiles", "pubchem_cid", "dtxsid", "dtxcid",
        "source_priority", "hazard_status", "hazard_source", "hazard_last_updated",
        "ghs_classes", "signal_word", "hazard_statements", "precautionary_statements"
    ]]


def build_bridge_product_chemical(
    cscp_df: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_chemical: pd.DataFrame
) -> pd.DataFrame:
    """
    Build bridge_product_chemical fact table.

    Links products to chemicals with mapping metadata.
    """
    # Merge CSCP with dim_product to get product_id
    bridge = cscp_df.merge(
        dim_product,
        on=["product_name", "brand", "company", "category_raw"],
        how="left"
    )

    # Create dedupe key for chemical matching
    bridge["chemical_dedupe_key"] = bridge.apply(
        lambda row: row["casrn"] if pd.notna(row["casrn"]) and row["casrn"].strip()
        else f"{row['ingredient_normalized']}|{row['ingredient_raw']}",
        axis=1
    )

    # Merge with dim_chemical to get chemical_id
    chemical_map = dim_chemical.set_index("dedupe_key")["chemical_id"]
    bridge["chemical_id"] = bridge["chemical_dedupe_key"].map(chemical_map)

    # Add mapping metadata
    bridge["mapping_method"] = "seed_link_m1"
    bridge["confidence"] = 0.2  # placeholder since identity not validated
    bridge["evidence_source"] = "CSCP"

    return bridge[[
        "product_id", "chemical_id", "casrn", "ingredient_raw",
        "mapping_method", "confidence", "evidence_source"
    ]]