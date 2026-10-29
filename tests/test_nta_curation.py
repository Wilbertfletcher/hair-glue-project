import pandas as pd

from pipeline.extract.nta_curation import (
    normalise_results,
    parse_identifiers,
    tag_adhesive,
    tag_personal_care,
)
from warehouse.source_nta_data import build_chemical_crossref, build_suspect_list


def _raw(rows):
    cols = [
        "feature_id", "reference_id", "pub_doi", "pub_chromatography",
        "reported_product", "cpdat_category", "reported_identifiers",
        "priority_identifier", "priority_identifier_type", "mapped_id",
        "mapped_id_type", "mapped_id_source", "classyfire_superclass",
        "cpdat_yn", "expocast_yn", "nhanes_yn", "toxvaldb_yn", "toxcast_yn",
    ]
    return pd.DataFrame(rows, columns=cols)


RAW = _raw([
    (1, 1, "10.1/a", "GC", "Shampoo; Baby Soap", 137,
     "DTXSID9021392; 102-71-6; Triethanolamine", "DTXSID9021392", "dtxsid",
     "DTXSID9021392", "DTXSID", "Extracted from source",
     "Organic nitrogen compounds", "Y", "Y", None, "Y", "Y"),
    (2, 2, "10.1/b", "LC", "plastic food contact material; reported use: adhesive",
     312, "78-70-6; Linalool", "78-70-6", "cas", "DTXSID7025502", "DTXSID",
     "CTX API", "Lipids and lipid-like molecules", "Y", "Y", None, None, None),
    (3, 3, "10.1/c", "GC", "lipstick", 137, "mystery peak", "mystery peak",
     "general_name", None, "unmapped", None, None, None, None, None, None, None),
    (4, 3, "10.1/c", "GC", "consumer and household products: 'Adhesive'", 72,
     "78-70-6; Linalool", "78-70-6", "cas", "DTXSID7025502", "DTXSID",
     "CTX API", "Lipids and lipid-like molecules", "Y", "Y", None, None, None),
])


def test_parse_identifiers():
    assert parse_identifiers("DTXSID1041269; 77-53-2; (+)-Cedrol") == ("77-53-2", "(+)-Cedrol")
    assert parse_identifiers("106-65-0; Dimethyl succinate") == ("106-65-0", "Dimethyl succinate")
    assert parse_identifiers(None) == (None, None)


def test_product_tagging():
    assert tag_personal_care("Baby Soap; Shampoo")
    assert not tag_personal_care("Recycled Tire Products")
    assert not tag_personal_care("surface coating")  # 'face' must not match inside 'surface'
    assert tag_adhesive("consumer and household products: 'Adhesive'; 'Coating'")
    # 'adhesive' as a reported *use* of a chemical in food packaging is not an adhesive product
    assert not tag_adhesive("plastic food contact material; reported use: adhesive")


def test_normalise_flags_and_unmapped():
    df = normalise_results(RAW)
    assert df["toxcast_yn"].tolist() == [True, False, False, False]
    assert pd.isna(df.loc[2, "mapped_id"])
    assert df["is_personal_care"].tolist() == [True, False, True, False]
    assert df["is_adhesive_product"].tolist() == [False, False, False, True]


def test_crossref_and_suspects():
    nta = normalise_results(RAW)
    chems = pd.DataFrame({
        "casrn": ["102-71-6", "50-00-0"],
        "canonical_name": ["triethanolamine", "formaldehyde"],
        "dtxsid": ["DTXSID9021392", "DTXSID7020637"],
        "pubchem_cid": [7618.0, 712.0],
        "preferred_name": ["Triethanolamine", "Formaldehyde"],
    })
    chems["display_name"] = chems["preferred_name"]
    xref = build_chemical_crossref(nta, chems).set_index("casrn")
    assert xref.loc["102-71-6", "nta_detected"]
    assert xref.loc["102-71-6", "nta_detected_in_personal_care"]
    assert not xref.loc["50-00-0", "nta_detected"]
    assert "derivatisation" in xref.loc["50-00-0", "nta_blind_spot_note"]

    sus = build_suspect_list(nta, {"DTXSID9021392"}).set_index("mapped_id")
    assert set(sus.index) == {"DTXSID9021392", "DTXSID7025502"}
    assert sus.loc["DTXSID7025502", "eu_fragrance_allergen"]  # linalool
    assert sus.loc["DTXSID7025502", "tox_evidence_gap"]
    assert sus.loc["DTXSID9021392", "in_hair_glue_warehouse"]


def test_gcms_suspect_list_tiers():
    from warehouse.build_gcms_suspect_list import COLUMNS, build_gcms_suspect_list
    from warehouse.source_nta_data import EU_FRAGRANCE_ALLERGENS_26

    def row(dtxsid, name, cas, n, gc, lc, allergen=False, phth=False, adhesive=False):
        return {
            "mapped_id": dtxsid, "chemical_name": name, "casrn": cas, "study_count": n,
            "detected_by_gc": gc, "detected_by_lc": lc, "eu_fragrance_allergen": allergen,
            "is_phthalate": phth, "in_adhesive_product": adhesive, "tox_evidence_gap": True,
        }

    suspects = pd.DataFrame([
        row("D1", "Linalool", "78-70-6", 2, True, False, allergen=True),
        row("D2", "Diethyl phthalate", "84-66-2", 4, True, False, phth=True),
        row("D3", "Common GC thing", "1-1-1", 3, True, False),
        row("D4", "Rare GC thing", "2-2-2", 1, True, False),
        row("D5", "LC-only adhesive PFAS", None, 1, False, True, adhesive=True),
        row("D6", "Myrcene", "123-35-3", 3, True, True),
    ])
    crossref = pd.DataFrame([
        {"dtxsid": "D6", "casrn": "123-35-3", "chemical_name": "Myrcene", "nta_detected": True,
         "nta_study_count": 7, "nta_chromatography": "GC", "nta_toxcast_yn": True,
         "nta_toxvaldb_yn": True},
        {"dtxsid": "D7", "casrn": "100-42-5", "chemical_name": "Styrene", "nta_detected": True,
         "nta_study_count": 7, "nta_chromatography": "GC | LC", "nta_toxcast_yn": True,
         "nta_toxvaldb_yn": True},
        {"dtxsid": "D8", "casrn": "50-00-0", "chemical_name": "Formaldehyde", "nta_detected": False,
         "nta_study_count": 0, "nta_chromatography": "", "nta_toxcast_yn": True,
         "nta_toxvaldb_yn": True},
    ])

    out = build_gcms_suspect_list(suspects, crossref)
    tier = dict(zip(out["chemical_name"], out["tier"]))

    assert list(out.columns) == COLUMNS
    assert tier["Linalool"] == 1 and tier["Diethyl phthalate"] == 1
    assert tier["Myrcene"] == 1 and tier["Styrene"] == 1   # declared, GC-detected
    assert "Formaldehyde" not in tier                      # declared but never GC-detected
    assert tier["Common GC thing"] == 2 and tier["Rare GC thing"] == 3
    assert "LC-only adhesive PFAS" not in tier             # not screenable by GC
    # All 26 allergens are on the panel, seen by NTA or not
    allergen_cas = set(out.loc[out["eu_fragrance_allergen"].astype(bool), "casrn"])
    assert allergen_cas == set(EU_FRAGRANCE_ALLERGENS_26)
    assert out["retention_index"].isna().all()
