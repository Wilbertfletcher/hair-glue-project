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
