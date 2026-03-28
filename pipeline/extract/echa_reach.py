"""
ECHA REACH Registered Substances — Bulk File Loader

Reads the ECHA Registered Substances export (Excel or CSV) and extracts
tonnage band, registration type, and registrant count for a given set of
CAS numbers.

How to obtain the source file
------------------------------
1. Go to ECHA Information on Chemicals:
   https://echa.europa.eu/en/information-on-chemicals/registered-substances
2. Click "Export" (top-right of the table) → download Excel (.xlsx)
3. Save to:  data/raw/echa_registered_substances.xlsx

ECHA updates this export periodically. Re-download to refresh the data.

Column names in the export (as of early 2024):
  - "EC Number"
  - "CAS Number"
  - "Substance Name"
  - "Registration type"        (Full / Intermediate / PPORD)
  - "Tonnage band"             (e.g. "1 - 10 t", "100 - 1 000 t")
  - "Number of registrations"  (integer)
  - "Last updated"
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Column-name aliases — ECHA has changed column names across export versions
# ---------------------------------------------------------------------------

_CAS_ALIASES = ["CAS Number", "CAS No.", "CAS no", "casrn", "CAS"]
_EC_ALIASES = ["EC Number", "EC No.", "EC no", "ecnumber"]
_NAME_ALIASES = ["Substance Name", "Substance name", "Name", "name"]
_TYPE_ALIASES = ["Registration type", "Registration Type", "Reg. type"]
_TONNAGE_ALIASES = [
    "Tonnage band", "Tonnage Band", "Tonnage", "tonnage_band",
]
_COUNT_ALIASES = [
    "Number of registrations",
    "No. of registrations",
    "Registrations",
    "registrant_count",
]
_UPDATED_ALIASES = ["Last updated", "Last Updated", "Update date"]

_ECHA_DOWNLOAD_URL = (
    "https://echa.europa.eu/en/information-on-chemicals/registered-substances"
)


def _pick_col(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    """Return the first alias that exists as a column, or None."""
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_echa_registered_substances(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Load the ECHA registered substances export; return normalised DataFrame.

    Output columns:
        casrn, ec_number, substance_name, registration_type,
        tonnage_band, registrant_count, last_updated, data_source

    Parameters
    ----------
    file_path : str or Path
        Path to the ECHA export file (.xlsx or .csv).

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If required columns cannot be identified or format unsupported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"ECHA registered substances file not found: {path}\n\n"
            f"Download it from:\n  {_ECHA_DOWNLOAD_URL}\n"
            "and save it to data/raw/echa_registered_substances.xlsx"
        )

    if path.suffix in (".xlsx", ".xls"):
        raw = pd.read_excel(path, dtype=str)
    elif path.suffix == ".csv":
        raw = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. Expected .xlsx or .csv"
        )

    raw.columns = [str(c).strip() for c in raw.columns]

    cas_col = _pick_col(raw, _CAS_ALIASES)
    ec_col = _pick_col(raw, _EC_ALIASES)
    name_col = _pick_col(raw, _NAME_ALIASES)
    type_col = _pick_col(raw, _TYPE_ALIASES)
    tonnage_col = _pick_col(raw, _TONNAGE_ALIASES)
    count_col = _pick_col(raw, _COUNT_ALIASES)
    updated_col = _pick_col(raw, _UPDATED_ALIASES)

    if cas_col is None:
        raise ValueError(
            "Cannot find CAS Number column. "
            f"Found columns: {list(raw.columns)}"
        )

    out = pd.DataFrame()
    out["casrn"] = raw[cas_col].str.strip()
    out["ec_number"] = raw[ec_col].str.strip() if ec_col else None
    out["substance_name"] = raw[name_col].str.strip() if name_col else None
    out["registration_type"] = (
        raw[type_col].str.strip() if type_col else None
    )
    out["tonnage_band"] = (
        raw[tonnage_col].str.strip() if tonnage_col else None
    )
    out["registrant_count"] = (
        pd.to_numeric(raw[count_col], errors="coerce").astype("Int64")
        if count_col else None
    )
    out["last_updated"] = (
        raw[updated_col].str.strip() if updated_col else None
    )
    out["data_source"] = "ECHA_registered_substances"

    out = out[out["casrn"].notna() & (out["casrn"] != "")]
    return out.reset_index(drop=True)


def filter_by_casrns(
    echa_df: pd.DataFrame,
    casrns: list[str],
) -> pd.DataFrame:
    """
    Filter the full ECHA table to only the CAS numbers we care about.

    Returns one row per input CAS number. Unmatched CAS numbers get a row
    with reach_registered=False and all ECHA fields set to None.

    Parameters
    ----------
    echa_df : DataFrame
        Output of load_echa_registered_substances().
    casrns : list[str]
        CAS numbers to keep.
    """
    target = {c.strip() for c in casrns if c}
    matched = echa_df[echa_df["casrn"].isin(target)].copy()

    # Multiple registrations per CAS: keep the row with the highest count
    # (typically the "Full" registration entry).
    matched = (
        matched
        .sort_values(
            "registrant_count", ascending=False, na_position="last",
        )
        .drop_duplicates(subset="casrn", keep="first")
    )

    matched_cas = set(matched["casrn"].tolist())
    missing = [c for c in target if c not in matched_cas]

    if missing:
        no_match = pd.DataFrame({
            "casrn": missing,
            "ec_number": None,
            "substance_name": None,
            "registration_type": None,
            "tonnage_band": None,
            "registrant_count": None,
            "last_updated": None,
            "data_source": "ECHA_registered_substances",
            "reach_registered": False,
        })
        matched["reach_registered"] = True
        matched = pd.concat([matched, no_match], ignore_index=True)
    else:
        matched["reach_registered"] = True

    return matched.reset_index(drop=True)
