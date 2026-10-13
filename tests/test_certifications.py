"""Tests for the certification screening rules (certifications.py)."""

import pandas as pd
import pytest

import certifications as certs


def _data(identity_rows, hazard_rows=(), regulatory_rows=(), product_rows=None):
    """Build the small subset of the warehouse dict the screener reads."""
    identity = pd.DataFrame(identity_rows)
    if product_rows is None:
        product_rows = [
            {
                "product_id": pid,
                "product_name": f"Product {pid}",
                "brand": "Test Brand",
                "category_raw": "Hair Care Products (non-coloring)",
            }
            for pid in sorted(identity["product_id"].unique())
        ]
    return {
        "products": pd.DataFrame(product_rows),
        "identity": identity,
        "hazard_ref": pd.DataFrame(list(hazard_rows)),
        "regulatory": pd.DataFrame(list(regulatory_rows)),
    }


# ── Flagging one chemical ────────────────────────────────────────────────────

def test_ghs_carcinogen_and_reprotox_flags():
    flags = certs.chemical_flags({
        "ingredient_raw": "Formaldehyde (gas)",
        "canonical_name": "formaldehyde",
        "casrn": "50-00-0",
        "ghs_hazard_class": "Acute Tox|Carc|Muta|Skin Corr|Skin Sens",
        "carcinogenicity": "Confirmed",
        "reproductive_hazard": True,
        "prop65_listed": True,
        "reach_restricted": True,
    })
    assert set(flags) >= {
        "carcinogen", "mutagen", "reprotox", "prop65",
        "reach_restricted", "formaldehyde", "sensitizer",
    }
    assert "disclosure_gap" not in flags


def test_iarc_group_drives_carcinogen_flag():
    flags = certs.chemical_flags({
        "ingredient_raw": "Titanium dioxide",
        "canonical_name": "diketotitanium",
        "casrn": "13463-67-7",
        "iarc_classification": "Group 2B: Possibly carcinogenic to humans",
    })
    assert "carcinogen" in flags
    assert "Group 2B" in flags["carcinogen"]


def test_iarc_group_3_is_not_a_carcinogen_flag():
    flags = certs.chemical_flags({
        "ingredient_raw": "Triethanolamine",
        "canonical_name": "2-[bis(2-hydroxyethyl)amino]ethanol",
        "casrn": "102-71-6",
        "iarc_classification": "Group 3: Not classifiable as to its carcinogenicity to humans",
        "ghs_hazard_class": "Eye Irrit",
    })
    assert "carcinogen" not in flags
    assert "ethanolamine" in flags


def test_missing_cas_is_a_disclosure_gap():
    flags = certs.chemical_flags({
        "ingredient_raw": "Mineral oils, untreated and mildly treated",
        "canonical_name": "Mineral oil (untreated/mildly treated)",
        "casrn": None,
    })
    assert "disclosure_gap" in flags
    # Name-based fallback still catches the IARC Group 1 classification.
    assert "carcinogen" in flags


@pytest.mark.parametrize("name,expected_flag", [
    ("Cocamide diethanolamine", "ethanolamine"),
    ("Dibutyl phthalate", "phthalate"),
    ("Perfluorooctanoic acid", "pfas"),
    ("Propylparaben", "restricted_paraben"),
    ("Lead acetate", "heavy_metal"),
    ("Nonylphenol ethoxylate", "alkylphenol"),
    ("DMDM hydantoin", "formaldehyde"),
])
def test_named_chemical_classes(name, expected_flag):
    flags = certs.chemical_flags({
        "ingredient_raw": name, "canonical_name": name, "casrn": "1-1-1",
    })
    assert expected_flag in flags


def test_mica_does_not_false_positive_as_pfas():
    """Mica's canonical name contains 'difluoride' — that is not a PFAS."""
    flags = certs.chemical_flags({
        "ingredient_raw": "Mica",
        "canonical_name": (
            "hexaaluminum;dipotassium;hexakis(diketosilane);"
            "nonakis(oxygen(2-));difluoride;hydrate"
        ),
        "casrn": "12001-26-2",
        "ghs_hazard_class": "Eye Irrit|Resp Irrit|STOT-RE",
    })
    assert "pfas" not in flags
    assert "carcinogen" not in flags


# ── Rule wiring ──────────────────────────────────────────────────────────────

def test_every_rule_covers_every_standard():
    for rule in certs.RULES:
        assert set(rule.applies) == set(certs.STANDARD_KEYS), rule.rule_id
        for severity, basis in rule.applies.values():
            assert severity in (certs.SEVERITY_BLOCKING, certs.SEVERITY_REVIEW)
            assert basis.strip()


def test_standards_metadata_is_complete():
    assert set(certs.STANDARD_KEYS) == {
        "ewg_verified", "cradle_to_cradle", "living_product",
    }
    for std in certs.STANDARDS.values():
        assert std.summary and std.url.startswith("https://")
        assert std.covers and std.beyond_ingredients


# ── Product screening ────────────────────────────────────────────────────────

def test_carcinogen_blocks_ewg_and_c2c_but_only_reviews_lpc():
    data = _data(
        identity_rows=[{
            "product_id": 1, "ingredient_raw": "Styrene",
            "casrn": "100-42-5", "canonical_name": "styrene",
        }],
        hazard_rows=[{
            "casrn": "100-42-5", "canonical_name": "styrene",
            "ghs_hazard_class": "Repr/Dev|STOT-RE", "reproductive_hazard": True,
        }],
    )
    screen = certs.screen_products(data)
    status = dict(zip(screen["standard_key"], screen["status"]))
    assert status["ewg_verified"] == certs.STATUS_BLOCKED
    assert status["cradle_to_cradle"] == certs.STATUS_BLOCKED
    assert status["living_product"] == certs.STATUS_REVIEW


def test_formaldehyde_blocks_all_three():
    data = _data(
        identity_rows=[{
            "product_id": 1, "ingredient_raw": "Formaldehyde (gas)",
            "casrn": "50-00-0", "canonical_name": "formaldehyde",
        }],
        hazard_rows=[{
            "casrn": "50-00-0", "canonical_name": "formaldehyde",
            "ghs_hazard_class": "Carc|Muta", "carcinogenicity": "Confirmed",
        }],
    )
    screen = certs.screen_products(data)
    assert set(screen["status"]) == {certs.STATUS_BLOCKED}


def test_clean_ingredient_has_no_blockers():
    data = _data(
        identity_rows=[{
            "product_id": 1, "ingredient_raw": "Water",
            "casrn": "7732-18-5", "canonical_name": "water",
        }],
        hazard_rows=[{"casrn": "7732-18-5", "canonical_name": "water"}],
    )
    screen = certs.screen_products(data)
    assert set(screen["status"]) == {certs.STATUS_CLEAR}
    assert set(screen["blocking_count"]) == {0}


def test_product_with_no_ingredients_reports_no_data():
    data = _data(
        identity_rows=[{
            "product_id": 1, "ingredient_raw": "Water",
            "casrn": "7732-18-5", "canonical_name": "water",
        }],
        hazard_rows=[{"casrn": "7732-18-5", "canonical_name": "water"}],
        product_rows=[
            {"product_id": 1, "product_name": "A", "brand": "B", "category_raw": "C"},
            {"product_id": 2, "product_name": "Empty", "brand": "B", "category_raw": "C"},
        ],
    )
    screen = certs.screen_products(data)
    empty = screen[screen["product_id"] == 2]
    assert set(empty["status"]) == {certs.STATUS_NO_DATA}


def test_hazard_record_matched_by_name_when_cas_is_missing():
    """Manual mappings carry no CAS — they join to hazard data by label name."""
    data = _data(
        identity_rows=[{
            "product_id": 1,
            "ingredient_raw": "Talc (powder)",
            "casrn": None,
            "canonical_name": "Talc",
        }],
        hazard_rows=[{
            "casrn": None, "canonical_name": "Talc (powder)",
            "ghs_hazard_class": "Carc",
        }],
    )
    findings = certs.screen_chemicals(data)
    rules_hit = set(findings["rule_id"])
    assert "cmr" in rules_hit
    assert "disclosure_gap" in rules_hit


def test_rollup_and_impact_shapes():
    data = _data(
        identity_rows=[
            {"product_id": 1, "ingredient_raw": "Formaldehyde (gas)",
             "casrn": "50-00-0", "canonical_name": "formaldehyde"},
            {"product_id": 2, "ingredient_raw": "Formaldehyde (gas)",
             "casrn": "50-00-0", "canonical_name": "formaldehyde"},
        ],
        hazard_rows=[{
            "casrn": "50-00-0", "canonical_name": "formaldehyde",
            "ghs_hazard_class": "Carc", "carcinogenicity": "Confirmed",
        }],
    )
    screen = certs.screen_products(data)
    rollup = certs.standard_rollup(screen)
    assert set(rollup["standard"]) == {
        certs.STANDARDS[k].name for k in certs.STANDARD_KEYS
    }
    assert rollup["products"].sum() == len(screen)

    impact = certs.ingredient_impact(data)
    row = impact.iloc[0]
    assert row["ingredient_raw"] == "Formaldehyde (gas)"
    assert row["products_affected"] == 2
    assert row["blocked_standard_count"] == 3


def test_empty_inputs_do_not_raise():
    empty = {
        "products": pd.DataFrame(), "identity": pd.DataFrame(),
        "hazard_ref": pd.DataFrame(), "regulatory": pd.DataFrame(),
    }
    assert len(certs.screen_products(empty)) == 0
    assert len(certs.screen_chemicals(empty)) == 0
    assert len(certs.standard_rollup(certs.screen_products(empty))) == 0
