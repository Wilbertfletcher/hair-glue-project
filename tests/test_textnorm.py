
import pandas as pd
from pathlib import Path
from pipeline.extract.cscp import parse_cscp_csv


def test_parse_cscp_csv_basic():
    """Test basic CSCP CSV parsing."""
    # Create a minimal test CSV with hair glue keywords
    test_csv = Path("test_cscp.csv")
    test_data = pd.DataFrame({
        "ProductName": ["Test Glue Product"],  # Include "glue" keyword
        "BrandName": ["Test Brand"],
        "CompanyName": ["Test Company"],
        "PrimaryCategory": ["Test Category"],
        "ChemicalName": ["Test Chemical"],
        "CasNumber": ["123-45-6"]
    })
    test_data.to_csv(test_csv, index=False)

    try:
        df = parse_cscp_csv(str(test_csv))
        assert len(df) == 1
        assert "product_name" in df.columns
        assert df["product_name"].iloc[0] == "Test Glue Product"
        assert df["ingredient_normalized"].iloc[0] == "test chemical"
    finally:
        test_csv.unlink()


def test_ingredient_normalization():
    """Test ingredient text normalization."""
    assert "water" == "Water".lower().strip()
    assert "test chemical" == "Test Chemical".lower().strip()
