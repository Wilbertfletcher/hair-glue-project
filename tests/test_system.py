"""
System integration tests — Hair Glue Project

Two test groups:
  1. Warehouse integrity  — all parquet files exist, required columns present,
                            no completely empty datasets.
  2. Chemical identifier  — CAS #, DTXSID, preferred name, and SMILES are
                            internally consistent and chemically valid where
                            possible (RDKit validation on SMILES).

Run:
    pytest tests/test_system.py -v
"""

import re
from pathlib import Path

import pandas as pd
import pytest

WAREHOUSE = Path("warehouse")

# ── Expected parquet files and their required columns ─────────────────────────

REQUIRED_FILES: dict[str, list[str]] = {
    "dim_products.parquet": ["product_id", "product_name"],
    "dim_ingredients.parquet": [],
    "ref_chemicals.parquet": ["casrn"],
    "ref_chemicals_regulatory.parquet": ["casrn", "dtxsid"],
    "ref_chemicals_comptox.parquet": [
        "casrn", "dtxsid", "preferred_name",
    ],
    "ref_chemicals_toxcast.parquet": [
        "casrn", "dtxsid", "assays_tested", "assays_active",
    ],
    "ref_chemicals_chemexpo.parquet": [
        "casrn", "dtxsid", "national_product_count",
    ],
    "ref_chemicals_hazard.parquet": ["casrn"],
    "ref_chemicals_regulatory.parquet": ["casrn", "dtxsid"],
    "product_hazard_summary.parquet": [],
}

# CAS# format: digits-digits-digit  (e.g. 50-00-0)
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")

# DTXSID format: DTXSID + optional digits
DTXSID_RE = re.compile(r"^DTXSID\d+$")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def comptox() -> pd.DataFrame:
    return pd.read_parquet(WAREHOUSE / "ref_chemicals_comptox.parquet")


@pytest.fixture(scope="module")
def toxcast() -> pd.DataFrame:
    return pd.read_parquet(WAREHOUSE / "ref_chemicals_toxcast.parquet")


@pytest.fixture(scope="module")
def chemexpo() -> pd.DataFrame:
    return pd.read_parquet(WAREHOUSE / "ref_chemicals_chemexpo.parquet")


@pytest.fixture(scope="module")
def regulatory() -> pd.DataFrame:
    return pd.read_parquet(WAREHOUSE / "ref_chemicals_regulatory.parquet")


@pytest.fixture(scope="module")
def ref_chemicals() -> pd.DataFrame:
    return pd.read_parquet(WAREHOUSE / "ref_chemicals.parquet")


# ── Group 1: Warehouse file integrity ─────────────────────────────────────────

class TestWarehouseFiles:

    @pytest.mark.parametrize("filename,required_cols", REQUIRED_FILES.items())
    def test_file_exists(self, filename, required_cols):
        path = WAREHOUSE / filename
        assert path.exists(), (
            f"Warehouse file missing: {filename}\n"
            f"Run the appropriate pipeline step to generate it."
        )

    @pytest.mark.parametrize("filename,required_cols", REQUIRED_FILES.items())
    def test_required_columns_present(self, filename, required_cols):
        path = WAREHOUSE / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist")
        if not required_cols:
            return
        df = pd.read_parquet(path)
        missing = [c for c in required_cols if c not in df.columns]
        assert not missing, (
            f"{filename} is missing columns: {missing}\n"
            f"Found: {list(df.columns)}"
        )

    def test_products_not_empty(self):
        df = pd.read_parquet(WAREHOUSE / "dim_products.parquet")
        assert len(df) > 0, "dim_products.parquet is empty"

    def test_comptox_has_data(self, comptox):
        assert len(comptox) > 0, "ref_chemicals_comptox.parquet is empty"
        named = comptox["preferred_name"].notna().sum()
        assert named > 0, "No preferred_name values in CompTox data"

    def test_toxcast_has_data(self, toxcast):
        assert len(toxcast) > 0, "ref_chemicals_toxcast.parquet is empty"
        with_studies = (toxcast["assays_tested"] > 0).sum()
        assert with_studies > 0, (
            "No chemicals have any ToxValDB study records. "
            "Re-run warehouse/source_epa_data.py."
        )

    def test_chemexpo_has_data(self, chemexpo):
        assert len(chemexpo) > 0, "ref_chemicals_chemexpo.parquet is empty"
        found = (chemexpo["national_product_count"] > 0).sum()
        assert found > 0, (
            "No chemicals found in ChemExpo national product database. "
            "Re-run warehouse/source_epa_data.py."
        )

    def test_all_three_epa_tables_cover_same_chemicals(
        self, comptox, toxcast, chemexpo
    ):
        """CompTox, ToxValDB, and ChemExpo tables should cover the same set."""
        ctx_ids = set(comptox["casrn"].dropna())
        tox_ids = set(toxcast["casrn"].dropna())
        exp_ids = set(chemexpo["casrn"].dropna())

        only_comptox = ctx_ids - tox_ids - exp_ids
        assert len(ctx_ids) > 0, "CompTox CASRN set is empty"
        # All three should have the same chemicals (allow minor gaps)
        overlap = ctx_ids & tox_ids & exp_ids
        assert len(overlap) / len(ctx_ids) >= 0.8, (
            f"Less than 80% overlap across EPA tables. "
            f"CompTox={len(ctx_ids)}, ToxValDB={len(tox_ids)}, "
            f"ChemExpo={len(exp_ids)}, overlap={len(overlap)}"
        )


# ── Group 2: Chemical identifier correctness ──────────────────────────────────

class TestChemicalIdentifiers:

    def test_casrn_format(self, comptox):
        """All non-null CAS#s must match the standard format XX-XX-X."""
        bad = [
            cas for cas in comptox["casrn"].dropna()
            if not CAS_RE.match(str(cas))
        ]
        assert not bad, (
            f"{len(bad)} CAS# values have invalid format: {bad[:10]}"
        )

    def test_dtxsid_format(self, comptox):
        """All non-null DTXSIDs must start with DTXSID followed by digits."""
        bad = [
            sid for sid in comptox["dtxsid"].dropna()
            if not DTXSID_RE.match(str(sid))
        ]
        assert not bad, (
            f"{len(bad)} DTXSID values have invalid format: {bad[:10]}"
        )

    def test_casrn_dtxsid_no_duplicates(self, comptox):
        """Each CAS# should map to exactly one DTXSID (no many-to-one)."""
        dupes = (
            comptox.dropna(subset=["casrn", "dtxsid"])
            .groupby("casrn")["dtxsid"]
            .nunique()
        )
        multi = dupes[dupes > 1]
        assert len(multi) == 0, (
            f"These CAS#s map to multiple DTXSIDs:\n{multi}"
        )

    def test_dtxsid_casrn_no_duplicates(self, comptox):
        """Each DTXSID should map to exactly one CAS#."""
        dupes = (
            comptox.dropna(subset=["casrn", "dtxsid"])
            .groupby("dtxsid")["casrn"]
            .nunique()
        )
        multi = dupes[dupes > 1]
        assert len(multi) == 0, (
            f"These DTXSIDs map to multiple CAS#s:\n{multi}"
        )

    def test_preferred_name_not_all_null(self, comptox):
        """At least 50% of CompTox rows must have a preferred_name."""
        pct = comptox["preferred_name"].notna().mean()
        assert pct >= 0.5, (
            f"Only {pct:.0%} of CompTox rows have a preferred_name. "
            f"Check the API fetch."
        )

    def test_regulatory_dtxsid_matches_comptox(self, regulatory, comptox):
        """DTXSIDs in regulatory table must also appear in CompTox table."""
        reg_ids = set(regulatory["dtxsid"].dropna())
        ctx_ids = set(comptox["dtxsid"].dropna())
        missing = reg_ids - ctx_ids
        assert not missing, (
            f"{len(missing)} DTXSIDs in regulatory data are absent from "
            f"CompTox table — possible stale data: {list(missing)[:10]}"
        )

    def test_known_chemicals_present(self, comptox):
        """
        Key chemicals known to be in hair-glue products must be present
        with correct CAS# → DTXSID mappings.
        """
        known = {
            "50-00-0":   "DTXSID7020637",   # Formaldehyde
            "872-50-4":  "DTXSID6020856",   # N-Methyl-2-pyrrolidone
            "100-42-5":  "DTXSID2021284",   # Styrene
            "102-71-6":  "DTXSID9021392",   # Triethanolamine
            "111-42-2":  "DTXSID3021932",   # Diethanolamine
        }
        lookup = dict(
            zip(comptox["casrn"].astype(str), comptox["dtxsid"].astype(str))
        )
        for cas, expected_dtxsid in known.items():
            assert cas in lookup, (
                f"CAS# {cas} not found in CompTox table"
            )
            assert lookup[cas] == expected_dtxsid, (
                f"CAS# {cas}: expected DTXSID {expected_dtxsid}, "
                f"got {lookup[cas]}"
            )

    def test_smiles_parseable_by_rdkit(self, comptox):
        """All non-null SMILES strings must parse without error in RDKit."""
        try:
            from rdkit import Chem
        except ImportError:
            pytest.skip("RDKit not installed")

        failures = []
        for _, row in comptox.dropna(subset=["smiles"]).iterrows():
            smiles = str(row["smiles"]).strip()
            if not smiles or smiles in ("nan", "None"):
                continue
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                failures.append(
                    f"{row.get('preferred_name', row['casrn'])}: {smiles[:60]}"
                )

        # Allow up to 2 failures (some EPA SMILES use extended notation)
        assert len(failures) <= 2, (
            f"{len(failures)} SMILES strings failed RDKit parsing:\n"
            + "\n".join(failures)
        )

    def test_formaldehyde_smiles(self, comptox):
        """Formaldehyde (50-00-0) must have the correct SMILES C=O."""
        row = comptox[comptox["casrn"] == "50-00-0"]
        assert len(row) > 0, "Formaldehyde (50-00-0) not in CompTox table"
        smiles = row.iloc[0].get("smiles")
        assert smiles is not None and str(smiles).strip() == "C=O", (
            f"Formaldehyde SMILES should be 'C=O', got '{smiles}'"
        )

    def test_activity_scores_in_range(self, toxcast):
        """ToxValDB activity scores must be between 0 and 1."""
        scores = toxcast["activity_score"].dropna()
        assert (scores >= 0).all() and (scores <= 1).all(), (
            "activity_score values outside [0, 1] detected"
        )

    def test_chemexpo_product_counts_positive(self, chemexpo):
        """national_product_count must be non-negative."""
        counts = chemexpo["national_product_count"].fillna(0)
        assert (counts >= 0).all(), (
            "Negative national_product_count values detected"
        )

    def test_no_duplicate_casrn_across_epa_tables(
        self, comptox, toxcast, chemexpo
    ):
        """Each table should have at most one row per CAS#."""
        for df, name in [
            (comptox, "ref_chemicals_comptox"),
            (toxcast, "ref_chemicals_toxcast"),
            (chemexpo, "ref_chemicals_chemexpo"),
        ]:
            dupes = df[df.duplicated(subset=["casrn"], keep=False)]
            assert len(dupes) == 0, (
                f"{name} has {len(dupes)} duplicate CAS# rows:\n"
                f"{dupes['casrn'].tolist()}"
            )


# ── Group 3: API client smoke test (offline-safe) ─────────────────────────────

class TestAPIClient:

    def test_ccte_api_imports(self):
        """ccte_api module must import without errors."""
        from pipeline.extract import ccte_api  # noqa: F401

    def test_ctxpy_imports(self):
        """ctxpy must be installed and importable."""
        import ctxpy as ctx  # noqa: F401
        assert hasattr(ctx, "Chemical")
        assert hasattr(ctx, "Exposure")
        assert hasattr(ctx, "Hazard")

    def test_api_key_loaded(self):
        """CTX_API_KEY must be present in the environment."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("CTX_API_KEY", "")
        assert key, (
            "CTX_API_KEY is not set in .env — "
            "EPA API calls will fail without it."
        )

    def test_rdkit_available(self):
        """RDKit must be installed for structure rendering."""
        from rdkit import Chem  # noqa: F401
        from rdkit.Chem.Draw import rdMolDraw2D  # noqa: F401

    def test_cache_directory_exists(self):
        """Cache directory must exist so the API client can write to it."""
        cache = Path("data/raw/ccte_cache")
        assert cache.exists() and cache.is_dir(), (
            "Cache directory data/raw/ccte_cache/ is missing"
        )

    def test_draw_smiles_svg_formaldehyde(self):
        """draw_smiles_svg must return non-empty SVG for a valid SMILES."""
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D

        smiles = "C=O"
        mol = Chem.MolFromSmiles(smiles)
        assert mol is not None, "RDKit could not parse C=O"
        drawer = rdMolDraw2D.MolDraw2DSVG(300, 200)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        assert svg.startswith("<?xml"), "SVG output malformed"
        assert len(svg) > 500, "SVG suspiciously short"
