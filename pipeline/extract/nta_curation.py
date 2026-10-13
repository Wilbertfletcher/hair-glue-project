"""
Loader for the UL Research Institutes (Chemical Insights) curated NTA dataset.

Source:
    Boatman, A. K.; Ferland, T. M.; Whitehead, H. D. Curated Chemicals
    Reported in Consumer Products Using Non-Targeted Analyses (NTA).
    UL Research Institutes, Chemical Insights, 2026. Dataset release
    2026-05-15 (NTA_consumer_products_curation_results_20260515.xlsx).

The workbook has three tabs: readme, definitions, results. Only `results`
holds data: one row per chemical reported in one of 81 peer-reviewed
non-targeted analysis (NTA) studies of consumer products (11,952 rows,
6,978 unique mapped chemicals).

This module is offline-only: it reads the local workbook and returns
tidy DataFrames. No network access is required.
"""

import re
from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path(
    "data/raw/nta/NTA_consumer_products_curation_results_20260515.xlsx"
)
DATASET_VERSION = "2026-05-15"

# Evidence-availability flags in the source ('Y' or null)
FLAG_COLUMNS = [
    "cpdat_yn",
    "expocast_yn",
    "nhanes_yn",
    "toxvaldb_yn",
    "toxcast_yn",
]

# Word-boundary patterns used to tag reported_product strings.
# Kept deliberately conservative: false positives here would inflate the
# personal-care suspect list used for GC-MS screening.
PERSONAL_CARE_TERMS = [
    "cosmetic", "cosmetics", "shampoo", "shampoos", "conditioner",
    "lotion", "lotions", "cream", "creams", "lipstick", "lipsticks",
    "lip balm", "lip gloss", "hair", "perfume", "perfumes", "fragrance",
    "fragrances", "personal care", "makeup", "make-up", "deodorant",
    "deodorants", "antiperspirant", "sunscreen", "sunscreens", "soap",
    "body wash", "body washes", "body washer", "nail polish", "face cleanser",
    "facial cleanser", "face cleansers", "face cleaner", "mascara",
    "eyeliner", "eye shadow", "foundation", "baby soap", "moisturizer",
    "toothpaste", "mouthwash",
]
ADHESIVE_TERMS = [
    "adhesive", "adhesives", "glue", "glues", "bonding",
]

_PC_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in PERSONAL_CARE_TERMS) + r")\b",
    re.IGNORECASE,
)
_ADH_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in ADHESIVE_TERMS) + r")\b",
    re.IGNORECASE,
)
# Studies of food-contact plastics list "adhesive" as a *reported use* of a
# chemical, not the product analysed; those rows are not adhesive products.
_REPORTED_USE_RE = re.compile(r"reported use:", re.IGNORECASE)

_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
_DTXSID_RE = re.compile(r"^DTXSID\d+$", re.IGNORECASE)
_INCHIKEY_RE = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")


def load_nta_results(path: Path | str = DEFAULT_PATH) -> pd.DataFrame:
    """Read the `results` tab and normalise types.

    Returns one row per reported chemical feature with:
      - flag columns converted to bool
      - reference_id / cpdat_category as strings
      - is_personal_care / is_adhesive_product tags
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"NTA workbook not found at {path}. Place the UL Chemical "
            "Insights release in data/raw/nta/."
        )
    df = pd.read_excel(path, sheet_name="results", dtype={"reference_id": str})
    return normalise_results(df)


def normalise_results(df: pd.DataFrame) -> pd.DataFrame:
    """Type-normalise a raw `results` frame (split out for testing)."""
    df = df.copy()
    df["reference_id"] = df["reference_id"].astype(str)
    df["cpdat_category"] = df["cpdat_category"].astype("string")
    df["reported_product"] = df["reported_product"].fillna("").astype(str)
    for col in FLAG_COLUMNS:
        df[col] = df[col].astype(str).str.upper().eq("Y")
    df["mapped_id"] = df["mapped_id"].where(
        df["mapped_id_type"].str.lower() != "unmapped"
    )
    parsed = df["reported_identifiers"].map(parse_identifiers)
    df["reported_casrn"] = parsed.map(lambda t: t[0])
    df["reported_name"] = parsed.map(lambda t: t[1])
    df["is_personal_care"] = df["reported_product"].map(tag_personal_care)
    df["is_adhesive_product"] = df["reported_product"].map(tag_adhesive)
    return df


def parse_identifiers(raw) -> tuple:
    """Split a `reported_identifiers` string into (casrn, name).

    Example: 'DTXSID1041269; 77-53-2; (+)-Cedrol' -> ('77-53-2', '(+)-Cedrol').
    Tokens that are DTXSIDs, InChIKeys, InChI strings or SMILES-like are
    skipped; the last remaining token is taken as the name.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return (None, None)
    casrn, names = None, []
    for tok in (t.strip() for t in str(raw).split(";")):
        if not tok:
            continue
        if _CAS_RE.match(tok):
            casrn = casrn or tok
        elif _DTXSID_RE.match(tok) or _INCHIKEY_RE.match(tok) or tok.startswith("InChI="):
            continue
        else:
            names.append(tok)
    return (casrn, names[-1] if names else None)


def tag_personal_care(product: str) -> bool:
    return bool(_PC_RE.search(product or ""))


def tag_adhesive(product: str) -> bool:
    """True when an adhesive was the analysed product, not a reported use."""
    if not product:
        return False
    if _REPORTED_USE_RE.search(product):
        product = _REPORTED_USE_RE.split(product)[0]
    return bool(_ADH_RE.search(product))
