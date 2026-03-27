"""
Parquet Writing Module

Utilities for writing DataFrames to Parquet format.
"""

import pandas as pd
from pathlib import Path


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to Parquet file."""
    df.to_parquet(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")