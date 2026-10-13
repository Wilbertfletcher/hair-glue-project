#!/usr/bin/env python3
"""
Hair Glue Project — Third-Party Certification Screening

Encodes three voluntary certification programs that apply to hair care and
other personal care products, and pre-screens the warehouse ingredient data
against the publicly published restricted-substance criteria of each one:

  * EWG VERIFIED               — Environmental Working Group
  * Cradle to Cradle Certified — Cradle to Cradle Products Innovation Institute
  * The Living Product Challenge — International Living Future Institute

IMPORTANT — SCOPE AND LIMITS
    This module produces an *unofficial pre-screen*, not a certification
    decision. Three limits matter:

    1. Our ingredient data comes from the California Safe Cosmetics Program
       (CSCP), which only collects the *reportable hazardous* ingredients of a
       product — not its full formulation. A "no blockers found" result
       therefore means "nothing disqualifying in the chemicals we can see,"
       never "this product would be certified."
    2. Every one of these programs also audits things that no ingredient table
       can show: manufacturing sites, supply-chain disclosure, water and
       energy use, packaging, and social fairness.
    3. Criteria are revised by the certifying bodies over time. The rules here
       reflect the publicly documented criteria as reviewed on the date in
       CRITERIA_REVIEWED, and each rule records the published basis it came
       from. Confirm against the official criteria before relying on it.

Used by app.py (the "Certifications" page) and covered by
tests/test_certifications.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

# Date the published criteria behind RULES were last reviewed by a human.
CRITERIA_REVIEWED = "2026-08"

# Product-level screening outcomes.
STATUS_BLOCKED = "Would not qualify"
STATUS_REVIEW = "Needs review"
STATUS_CLEAR = "No blockers found"
STATUS_NO_DATA = "No ingredient data"

STATUS_ICONS = {
    STATUS_BLOCKED: "🔴",
    STATUS_REVIEW: "🟠",
    STATUS_CLEAR: "🟢",
    STATUS_NO_DATA: "⚫",
}

STATUS_ORDER = [STATUS_BLOCKED, STATUS_REVIEW, STATUS_CLEAR, STATUS_NO_DATA]

SEVERITY_BLOCKING = "blocking"
SEVERITY_REVIEW = "review"


# ── The three certification programs ─────────────────────────────────────────

@dataclass(frozen=True)
class Standard:
    """One voluntary certification program."""

    key: str
    name: str
    issuer: str
    tagline: str
    summary: str
    covers: tuple = field(default=())
    ingredient_basis: str = ""
    disclosure_rule: str = ""
    beyond_ingredients: tuple = field(default=())
    hair_care_note: str = ""
    url: str = ""


STANDARDS: dict = {
    "ewg_verified": Standard(
        key="ewg_verified",
        name="EWG VERIFIED",
        issuer="Environmental Working Group (EWG)",
        tagline="Full ingredient disclosure and no chemicals of concern.",
        summary=(
            "Run by the Environmental Working Group, this label requires full "
            "ingredient disclosure, avoidance of chemicals of concern, and "
            "strict transparency to verify that personal and hair care "
            "products are truly non-toxic."
        ),
        covers=(
            "Every ingredient must be disclosed on the label — including what "
            "is hiding inside the word 'fragrance'.",
            "The product must avoid ingredients on EWG's Unacceptable List "
            "(chemicals of concern for human health).",
            "Ingredients flagged as Restricted must meet EWG's use limits.",
            "Labeling must be honest, and the maker must follow good "
            "manufacturing practices.",
        ),
        ingredient_basis=(
            "EWG's Unacceptable and Restricted ingredient criteria, which draw "
            "on EWG's Skin Deep hazard scoring and authoritative government "
            "lists (for example California Proposition 65, the EU cosmetics "
            "restrictions, and IARC cancer classifications)."
        ),
        disclosure_rule=(
            "Full disclosure of all ingredients, including the components of "
            "fragrance blends."
        ),
        beyond_ingredients=(
            "Label and marketing claim review",
            "Good manufacturing practice documentation",
            "Annual re-verification of the formula",
        ),
        hair_care_note=(
            "The most common of the three on a shampoo or styling-product "
            "shelf — it is written for personal care, so hair glues, gels and "
            "adhesives fall squarely inside its scope."
        ),
        url="https://www.ewg.org/ewgverified/",
    ),
    "cradle_to_cradle": Standard(
        key="cradle_to_cradle",
        name="Cradle to Cradle Certified",
        issuer="Cradle to Cradle Products Innovation Institute",
        tagline="Material health plus circularity, down to the chemical.",
        summary=(
            "Evaluates hair care products and shampoos on material health, "
            "product circularity, and environmental stewardship down to "
            "specific chemical safety thresholds."
        ),
        covers=(
            "Material health: every chemical present above 100 parts per "
            "million is inventoried and assessed against toxicity endpoints.",
            "Product circularity: what the product and its packaging are made "
            "of and what happens to them afterwards.",
            "Clean air and climate protection, water and soil stewardship, "
            "and social fairness are scored as separate categories.",
            "Certification is awarded at levels — Bronze through Platinum — so "
            "a product can be certified while still improving.",
        ),
        ingredient_basis=(
            "The Cradle to Cradle Certified Restricted Substances List / Banned "
            "List of Chemicals, which excludes CMR substances (carcinogens, "
            "mutagens and reproductive toxicants), added formaldehyde, PFAS, "
            "phthalates, toxic heavy metals and other listed classes above "
            "defined concentration thresholds."
        ),
        disclosure_rule=(
            "A full chemical inventory down to 100 ppm (0.01%), supplied by "
            "the maker and its suppliers to an accredited assessor."
        ),
        beyond_ingredients=(
            "Recycled/renewable material content and end-of-life pathway",
            "Renewable energy and carbon accounting at the factory",
            "Water stewardship and effluent quality",
            "Social fairness auditing of the supply chain",
        ),
        hair_care_note=(
            "Applies to shampoos, conditioners and other rinse-off hair care, "
            "where the bottle and the down-the-drain fate of the formula both "
            "count toward the score."
        ),
        url="https://c2ccertified.org/the-standard",
    ),
    "living_product": Standard(
        key="living_product",
        name="The Living Product Challenge",
        issuer="International Living Future Institute (ILFI)",
        tagline="Net-positive products with fully transparent materials.",
        summary=(
            "Also created by the International Living Future Institute, this "
            "broader standard applies to consumer goods and personal care "
            "items to evaluate complete material health transparency, though "
            "it is less common for hair care than building materials."
        ),
        covers=(
            "Materials petal: no ingredients from ILFI's Red List, and public "
            "disclosure of what is in the product.",
            "Water and Energy petals: the making of the product should give "
            "back more than it takes ('net positive', or handprinting).",
            "Place, Equity and Beauty petals cover the site, the workforce and "
            "honest design.",
            "A lighter 'Petal Certification' path exists for makers who meet "
            "some petals but not all.",
        ),
        ingredient_basis=(
            "The ILFI Red List, which names classes such as added "
            "formaldehyde, phthalates, PFAS, alkylphenols, bisphenols, "
            "halogenated flame retardants and toxic heavy metals, together "
            "with the Declare-label disclosure requirement down to 100 ppm."
        ),
        disclosure_rule=(
            "A public Declare label listing every ingredient at or above "
            "100 ppm, with its source and end-of-life."
        ),
        beyond_ingredients=(
            "Net-positive water and energy accounting for the factory",
            "Handprinting — measured benefit created beyond the factory gate",
            "Responsible sourcing, equity and beauty requirements",
            "A 12-month performance period before final certification",
        ),
        hair_care_note=(
            "Built for building products first, so hair care certifications "
            "are rare — but its Red List and Declare disclosure translate "
            "directly to a shampoo or an adhesive."
        ),
        url="https://living-future.org/lpc/",
    ),
}

STANDARD_KEYS = tuple(STANDARDS.keys())


# ── Hazard flags read off the warehouse tables ───────────────────────────────

# Substances whose cancer classification is not carried in our hazard table
# (they arrive from CSCP as grouped label entries with no CAS number), keyed by
# a lowercase fragment of the label text.
NAME_CARCINOGENS = {
    "silica, crystalline": "IARC Group 1 carcinogen (respirable crystalline silica)",
    "mineral oils, untreated": "IARC Group 1 carcinogen (untreated/mildly treated mineral oils)",
    "talc": "IARC Group 2A — probably carcinogenic to humans",
    "carbon black": "IARC Group 2B — possibly carcinogenic to humans",
}

FORMALDEHYDE_CASRNS = {"50-00-0"}
FORMALDEHYDE_PATTERN = re.compile(
    r"formaldehyde|formalin|\bmethanal\b|quaternium-15|dmdm\s+hydantoin|"
    r"imidazolidinyl\s+urea|diazolidinyl\s+urea|bronopol|methenamine|"
    r"sodium\s+hydroxymethylglycinate",
    re.I,
)
ETHANOLAMINE_PATTERN = re.compile(
    r"(di|tri|mono)ethanolamine|"
    r"\b(cocamide|lauramide|oleamide|linoleamide|myristamide)\s+dea\b|"
    r"\b(dea|tea|mea)-\w+",
    re.I,
)
PFAS_PATTERN = re.compile(
    r"perfluoro|polyfluoro|fluorotelomer|\bptfe\b|\bpfoa\b|\bpfos\b|"
    r"polytetrafluoroethylene",
    re.I,
)
PHTHALATE_PATTERN = re.compile(r"phthalate", re.I)
RESTRICTED_PARABEN_PATTERN = re.compile(
    r"\b(iso)?(propyl|butyl)\s*paraben\b|\b(iso)?(propyl|butyl)paraben\b", re.I
)
HEAVY_METAL_PATTERN = re.compile(
    r"\blead\b|\bmercury\b|\bcadmium\b|\barsenic\b|\bantimony\b|\bthallium\b|"
    r"hexavalent\s+chromium|chromium\s*\(?vi\)?",
    re.I,
)
ALKYLPHENOL_PATTERN = re.compile(r"alkylphenol|nonylphenol|octylphenol|bisphenol", re.I)


def _norm(value) -> str:
    """Lowercase, whitespace-trimmed text; '' for anything missing."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower()


def _is_true(value) -> bool:
    """Tolerant truthiness for the mixed bool/None/string warehouse columns."""
    return _norm(value) in {"true", "1", "yes", "y"}


def chemical_flags(row: Mapping) -> dict:
    """Return ``{flag: evidence}`` for one ingredient row.

    ``row`` is an ingredient joined to its GHS hazard record and its
    regulatory record. Every flag carries the plain-language evidence that
    produced it, so the dashboard can always show its work.
    """
    flags: dict = {}
    name = " ".join(
        part for part in (
            _norm(row.get("ingredient_raw")),
            _norm(row.get("canonical_name")),
        ) if part
    )
    ghs = _norm(row.get("ghs_hazard_class"))
    iarc = _norm(row.get("iarc_classification"))
    carc_field = _norm(row.get("carcinogenicity"))

    # Cancer
    carc_evidence = []
    if carc_field in {"confirmed", "suspected"}:
        carc_evidence.append(f"hazard data lists cancer risk as '{carc_field}'")
    if "carc" in ghs:
        carc_evidence.append("GHS classification includes Carc (carcinogen)")
    if iarc.startswith(("group 1", "group 2a", "group 2b")):
        carc_evidence.append(f"IARC {row.get('iarc_classification')}")
    for fragment, basis in NAME_CARCINOGENS.items():
        if fragment in name:
            carc_evidence.append(basis)
            break
    if carc_evidence:
        flags["carcinogen"] = "; ".join(carc_evidence)

    # Gene damage
    if "muta" in ghs:
        flags["mutagen"] = "GHS classification includes Muta (DNA-damaging)"

    # Reproductive / developmental harm
    repro_evidence = []
    if _is_true(row.get("reproductive_hazard")):
        repro_evidence.append("hazard data flags reproductive toxicity")
    if "repr" in ghs:
        repro_evidence.append("GHS classification includes Repr (reproductive/developmental)")
    if repro_evidence:
        flags["reprotox"] = "; ".join(repro_evidence)

    # Authoritative government listings
    if _is_true(row.get("prop65_listed")):
        types = row.get("prop65_types")
        detail = f" ({types})" if _norm(types) else ""
        flags["prop65"] = f"listed under California Proposition 65{detail}"
    if _is_true(row.get("reach_restricted")):
        flags["reach_restricted"] = "restricted under EU REACH"

    # Named chemical classes called out by the certification lists
    if _norm(row.get("casrn")) in FORMALDEHYDE_CASRNS or FORMALDEHYDE_PATTERN.search(name):
        flags["formaldehyde"] = "formaldehyde or a formaldehyde-releasing preservative"
    if ETHANOLAMINE_PATTERN.search(name):
        flags["ethanolamine"] = (
            "an ethanolamine compound (DEA/TEA/MEA), which can form "
            "cancer-linked nitrosamines"
        )
    if PFAS_PATTERN.search(name):
        flags["pfas"] = "a per- or polyfluoroalkyl substance (PFAS, a 'forever chemical')"
    if PHTHALATE_PATTERN.search(name):
        flags["phthalate"] = "a phthalate plasticizer"
    if RESTRICTED_PARABEN_PATTERN.search(name):
        flags["restricted_paraben"] = "a longer-chain paraben (propyl/butyl type)"
    if HEAVY_METAL_PATTERN.search(name):
        flags["heavy_metal"] = "a toxic heavy metal"
    if ALKYLPHENOL_PATTERN.search(name):
        flags["alkylphenol"] = "an alkylphenol or bisphenol compound"

    # Broader hazard endpoints
    if "sens" in ghs:
        flags["sensitizer"] = "GHS classification includes Sens (causes allergic reactions)"
    if "aquat" in ghs:
        flags["aquatic_tox"] = "GHS classification includes Aquatic (harmful to water life)"

    # Disclosure quality
    if not _norm(row.get("casrn")):
        flags["disclosure_gap"] = (
            "listed as a group or category with no CAS registry number, so the "
            "exact substance and its concentration cannot be verified"
        )
    elif not _norm(row.get("canonical_name")):
        flags["disclosure_gap"] = "could not be matched to an official chemical identity"

    return flags


# ── Screening rules ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    """One screening rule: which flags trip it, and what each program says."""

    rule_id: str
    title: str
    plain: str
    triggers: tuple
    applies: dict  # standard_key -> (severity, published basis)


RULES: tuple = (
    Rule(
        rule_id="cmr",
        title="Cancer, DNA damage, or reproductive harm",
        plain=(
            "The ingredient is linked to cancer, to damaged DNA, or to harm to "
            "fertility or an unborn baby. Certifiers call this group 'CMR'."
        ),
        triggers=("carcinogen", "mutagen", "reprotox"),
        applies={
            "ewg_verified": (
                SEVERITY_BLOCKING,
                "EWG's Unacceptable List rules out ingredients linked to cancer, "
                "gene damage, or reproductive and developmental harm.",
            ),
            "cradle_to_cradle": (
                SEVERITY_BLOCKING,
                "CMR substances are on the Cradle to Cradle Banned List and fail "
                "the Material Health assessment above the 100 ppm threshold.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Not every CMR substance is named on the ILFI Red List, but the "
                "Materials petal requires the maker to disclose and justify it.",
            ),
        },
    ),
    Rule(
        rule_id="formaldehyde",
        title="Formaldehyde or a formaldehyde releaser",
        plain=(
            "Formaldehyde — or a preservative that slowly gives off "
            "formaldehyde — is a known human carcinogen and a common trigger "
            "for scalp and lung irritation."
        ),
        triggers=("formaldehyde",),
        applies={
            "ewg_verified": (SEVERITY_BLOCKING, "Named on EWG's Unacceptable List."),
            "cradle_to_cradle": (
                SEVERITY_BLOCKING,
                "Added formaldehyde is on the Cradle to Cradle Banned List of Chemicals.",
            ),
            "living_product": (
                SEVERITY_BLOCKING,
                "Added formaldehyde is an ILFI Red List class.",
            ),
        },
    ),
    Rule(
        rule_id="pfas",
        title="PFAS 'forever chemicals'",
        plain=(
            "PFAS build up in people and in water and essentially never break "
            "down. All three programs exclude them outright."
        ),
        triggers=("pfas",),
        applies={
            "ewg_verified": (SEVERITY_BLOCKING, "Named on EWG's Unacceptable List."),
            "cradle_to_cradle": (SEVERITY_BLOCKING, "Named on the Banned List of Chemicals."),
            "living_product": (SEVERITY_BLOCKING, "Named on the ILFI Red List."),
        },
    ),
    Rule(
        rule_id="phthalate",
        title="Phthalates",
        plain=(
            "Phthalates keep products flexible and make fragrance last, and "
            "several are linked to hormone and reproductive effects."
        ),
        triggers=("phthalate",),
        applies={
            "ewg_verified": (SEVERITY_BLOCKING, "Named on EWG's Unacceptable List."),
            "cradle_to_cradle": (SEVERITY_BLOCKING, "Named on the Banned List of Chemicals."),
            "living_product": (SEVERITY_BLOCKING, "Named on the ILFI Red List."),
        },
    ),
    Rule(
        rule_id="heavy_metal",
        title="Toxic heavy metals",
        plain=(
            "Lead, mercury, cadmium, arsenic and hexavalent chromium are toxic "
            "at very low doses and are excluded by every program here."
        ),
        triggers=("heavy_metal",),
        applies={
            "ewg_verified": (SEVERITY_BLOCKING, "Named on EWG's Unacceptable List."),
            "cradle_to_cradle": (SEVERITY_BLOCKING, "Named on the Banned List of Chemicals."),
            "living_product": (SEVERITY_BLOCKING, "Toxic heavy metals are an ILFI Red List class."),
        },
    ),
    Rule(
        rule_id="alkylphenol",
        title="Alkylphenols and bisphenols",
        plain=(
            "These surfactant and plastic building blocks can act like hormones "
            "in the body and in rivers."
        ),
        triggers=("alkylphenol",),
        applies={
            "ewg_verified": (SEVERITY_BLOCKING, "Named on EWG's Unacceptable List."),
            "cradle_to_cradle": (SEVERITY_BLOCKING, "Named on the Banned List of Chemicals."),
            "living_product": (SEVERITY_BLOCKING, "Alkylphenols are an ILFI Red List class."),
        },
    ),
    Rule(
        rule_id="ethanolamine",
        title="Ethanolamines (DEA, TEA, MEA)",
        plain=(
            "These foam and pH ingredients can react with other ingredients to "
            "form nitrosamines, which are linked to cancer."
        ),
        triggers=("ethanolamine",),
        applies={
            "ewg_verified": (
                SEVERITY_BLOCKING,
                "Ethanolamine compounds are unacceptable under EWG's criteria "
                "because of nitrosamine contamination risk.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Assessed for nitrosamine formation and aquatic toxicity during "
                "Material Health review rather than banned outright.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Not a named Red List class, but it must be disclosed and "
                "justified under the Materials petal.",
            ),
        },
    ),
    Rule(
        rule_id="restricted_paraben",
        title="Longer-chain parabens",
        plain=(
            "Propyl- and butyl-type parabens are the preservatives most often "
            "tied to hormone effects; the shorter methyl and ethyl forms are "
            "generally allowed."
        ),
        triggers=("restricted_paraben",),
        applies={
            "ewg_verified": (
                SEVERITY_BLOCKING,
                "Propyl- and butyl-parabens are unacceptable under EWG's criteria.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Screened as a potential endocrine disruptor in Material Health assessment.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Must be disclosed on the Declare label and justified.",
            ),
        },
    ),
    Rule(
        rule_id="prop65",
        title="On California's Proposition 65 list",
        plain=(
            "California has formally listed this chemical as causing cancer, "
            "birth defects or other reproductive harm."
        ),
        triggers=("prop65",),
        applies={
            "ewg_verified": (
                SEVERITY_BLOCKING,
                "EWG excludes ingredients listed by an authoritative body such "
                "as California Proposition 65.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Prop 65 listings feed the Material Health toxicity endpoints and "
                "can cap the achievable level.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Triggers extra scrutiny and disclosure under the Materials petal.",
            ),
        },
    ),
    Rule(
        rule_id="reach_restricted",
        title="Restricted in the European Union (REACH)",
        plain=(
            "European regulators have limited or banned this chemical in "
            "consumer products."
        ),
        triggers=("reach_restricted",),
        applies={
            "ewg_verified": (
                SEVERITY_BLOCKING,
                "EWG excludes ingredients banned or restricted for cosmetic use "
                "by the EU.",
            ),
            "cradle_to_cradle": (
                SEVERITY_BLOCKING,
                "The Banned List is aligned with REACH restrictions and SVHC listings.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Not automatically Red List, but it must be disclosed and justified.",
            ),
        },
    ),
    Rule(
        rule_id="aquatic_tox",
        title="Harmful to water life",
        plain=(
            "Hair products rinse down the drain, so damage to fish and water "
            "life counts against the environmental scores."
        ),
        triggers=("aquatic_tox",),
        applies={
            "ewg_verified": (
                SEVERITY_REVIEW,
                "Environmental hazard raises the ingredient's Skin Deep score and "
                "may make it Restricted.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Aquatic toxicity is a scored Material Health endpoint and part of "
                "Water & Soil Stewardship.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Counts against the net-positive Water petal for a rinse-off product.",
            ),
        },
    ),
    Rule(
        rule_id="sensitizer",
        title="Causes skin or lung allergies",
        plain=(
            "Repeated contact can trigger allergic reactions on the scalp, on "
            "the hands of the stylist, or in the lungs."
        ),
        triggers=("sensitizer",),
        applies={
            "ewg_verified": (
                SEVERITY_REVIEW,
                "Known sensitizers are Restricted and allowed only within EWG's "
                "use limits.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Skin and respiratory sensitization are scored Material Health endpoints.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "Disclosed and reviewed under the Materials petal.",
            ),
        },
    ),
    Rule(
        rule_id="disclosure_gap",
        title="Ingredient is not fully disclosed",
        plain=(
            "The label names a group of chemicals rather than one specific "
            "substance, so nobody can check it against a banned list. All three "
            "programs are built on full disclosure."
        ),
        triggers=("disclosure_gap",),
        applies={
            "ewg_verified": (
                SEVERITY_REVIEW,
                "EWG VERIFIED requires full ingredient disclosure, including "
                "fragrance components.",
            ),
            "cradle_to_cradle": (
                SEVERITY_REVIEW,
                "Material Health requires a chemical inventory down to 100 ppm.",
            ),
            "living_product": (
                SEVERITY_REVIEW,
                "A Declare label must list every ingredient at or above 100 ppm.",
            ),
        },
    ),
)

RULES_BY_ID = {rule.rule_id: rule for rule in RULES}


# ── Screening ────────────────────────────────────────────────────────────────

def _unique_ingredients(identity: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct label ingredient."""
    cols = [c for c in ("ingredient_raw", "casrn", "canonical_name") if c in identity.columns]
    return identity[cols].drop_duplicates(subset=["ingredient_raw"]).reset_index(drop=True)


def build_chemical_profiles(data: Mapping) -> pd.DataFrame:
    """Join each label ingredient to its hazard and regulatory rows, then flag it.

    Ingredients that reached the warehouse without a CAS number (grouped label
    entries such as "Talc (powder)") are matched to their hazard record by
    name, which is how the manual mappings were recorded.
    """
    identity = data.get("identity", pd.DataFrame())
    if identity is None or len(identity) == 0:
        return pd.DataFrame(
            columns=["ingredient_raw", "casrn", "canonical_name", "flags"]
        )

    hazard = data.get("hazard_ref", pd.DataFrame())
    regulatory = data.get("regulatory", pd.DataFrame())
    chems = _unique_ingredients(identity)

    hazard_by_cas, hazard_by_name = {}, {}
    if hazard is not None and len(hazard) > 0:
        for rec in hazard.to_dict("records"):
            if _norm(rec.get("casrn")):
                hazard_by_cas.setdefault(_norm(rec["casrn"]), rec)
            if _norm(rec.get("canonical_name")):
                hazard_by_name.setdefault(_norm(rec["canonical_name"]), rec)

    reg_by_cas = {}
    if regulatory is not None and len(regulatory) > 0:
        for rec in regulatory.to_dict("records"):
            if _norm(rec.get("casrn")):
                reg_by_cas.setdefault(_norm(rec["casrn"]), rec)

    rows = []
    for chem in chems.to_dict("records"):
        cas = _norm(chem.get("casrn"))
        merged = dict(chem)
        haz = hazard_by_cas.get(cas) or hazard_by_name.get(_norm(chem.get("ingredient_raw")))
        if haz:
            merged.update({k: v for k, v in haz.items() if k not in ("casrn",)})
        reg = reg_by_cas.get(cas)
        if reg:
            merged.update({k: v for k, v in reg.items() if k not in ("casrn", "canonical_name")})
        # Keep the identity table's own naming, not the hazard table's.
        merged["ingredient_raw"] = chem.get("ingredient_raw")
        merged["canonical_name"] = chem.get("canonical_name")
        merged["casrn"] = chem.get("casrn")
        merged["flags"] = chemical_flags(merged)
        rows.append(merged)

    profiles = pd.DataFrame(rows)
    keep = ["ingredient_raw", "casrn", "canonical_name", "flags"]
    extra = [c for c in ("ghs_hazard_class", "iarc_classification") if c in profiles.columns]
    return profiles[keep + extra]


def screen_chemicals(data: Mapping) -> pd.DataFrame:
    """Tidy findings: one row per (ingredient, certification, rule) hit."""
    profiles = build_chemical_profiles(data)
    findings = []
    for prof in profiles.to_dict("records"):
        flags = prof.get("flags") or {}
        for rule in RULES:
            hit = [f for f in rule.triggers if f in flags]
            if not hit:
                continue
            evidence = "; ".join(flags[f] for f in hit)
            for standard_key, (severity, basis) in rule.applies.items():
                findings.append({
                    "ingredient_raw": prof["ingredient_raw"],
                    "casrn": prof.get("casrn"),
                    "canonical_name": prof.get("canonical_name"),
                    "standard_key": standard_key,
                    "standard": STANDARDS[standard_key].name,
                    "rule_id": rule.rule_id,
                    "rule": rule.title,
                    "severity": severity,
                    "why_it_matters": rule.plain,
                    "evidence": evidence,
                    "published_basis": basis,
                })
    return pd.DataFrame(findings, columns=[
        "ingredient_raw", "casrn", "canonical_name", "standard_key", "standard",
        "rule_id", "rule", "severity", "why_it_matters", "evidence",
        "published_basis",
    ])


def screen_products(data: Mapping) -> pd.DataFrame:
    """One row per (product, certification) with its screening outcome."""
    products = data.get("products", pd.DataFrame())
    identity = data.get("identity", pd.DataFrame())
    if products is None or len(products) == 0:
        return pd.DataFrame(columns=[
            "product_id", "product_name", "brand", "category_raw",
            "standard_key", "standard", "status", "status_icon",
            "blocking_count", "review_count", "blocking_ingredients",
            "review_ingredients", "summary",
        ])

    findings = screen_chemicals(data)
    by_ingredient: dict = {}
    if len(findings) > 0:
        for rec in findings.to_dict("records"):
            key = (rec["ingredient_raw"], rec["standard_key"])
            by_ingredient.setdefault(key, []).append(rec)

    ingredients_by_product: dict = {}
    if identity is not None and len(identity) > 0:
        for rec in identity[["product_id", "ingredient_raw"]].drop_duplicates().to_dict("records"):
            ingredients_by_product.setdefault(rec["product_id"], []).append(rec["ingredient_raw"])

    rows = []
    for prod in products.to_dict("records"):
        pid = prod.get("product_id")
        ingredients = ingredients_by_product.get(pid, [])
        for standard_key in STANDARD_KEYS:
            blocking, review = {}, {}
            for ingredient in ingredients:
                for rec in by_ingredient.get((ingredient, standard_key), []):
                    bucket = blocking if rec["severity"] == SEVERITY_BLOCKING else review
                    bucket.setdefault(ingredient, []).append(rec["rule"])

            if not ingredients:
                status = STATUS_NO_DATA
                summary = "No reported ingredients on file for this product."
            elif blocking:
                status = STATUS_BLOCKED
                summary = (
                    f"{len(blocking)} reported ingredient(s) match something this "
                    "program excludes outright."
                )
            elif review:
                status = STATUS_REVIEW
                summary = (
                    f"{len(review)} reported ingredient(s) would need a closer look "
                    "by the certifier."
                )
            else:
                status = STATUS_CLEAR
                summary = (
                    "Nothing disqualifying in the reported ingredients — the full "
                    "formula still has to be reviewed."
                )

            rows.append({
                "product_id": pid,
                "product_name": prod.get("product_name"),
                "brand": prod.get("brand"),
                "category_raw": prod.get("category_raw"),
                "standard_key": standard_key,
                "standard": STANDARDS[standard_key].name,
                "status": status,
                "status_icon": STATUS_ICONS[status],
                "blocking_count": len(blocking),
                "review_count": len(review),
                "blocking_ingredients": ", ".join(sorted(blocking)),
                "review_ingredients": ", ".join(sorted(review)),
                "summary": summary,
            })

    return pd.DataFrame(rows)


def standard_rollup(product_screen: pd.DataFrame) -> pd.DataFrame:
    """Product counts per certification and outcome, ready to chart."""
    if product_screen is None or len(product_screen) == 0:
        return pd.DataFrame(columns=["standard", "status", "products", "pct"])
    counts = (
        product_screen.groupby(["standard", "status"], dropna=False)
        .size().reset_index(name="products")
    )
    totals = counts.groupby("standard")["products"].transform("sum")
    counts["pct"] = (counts["products"] / totals * 100).round(1)
    counts["status"] = pd.Categorical(counts["status"], STATUS_ORDER, ordered=True)
    return counts.sort_values(["standard", "status"]).reset_index(drop=True)


def ingredient_impact(data: Mapping) -> pd.DataFrame:
    """Which ingredients block the most products, and for which programs."""
    identity = data.get("identity", pd.DataFrame())
    findings = screen_chemicals(data)
    if findings is None or len(findings) == 0:
        return pd.DataFrame(columns=[
            "ingredient_raw", "products_affected", "blocks", "needs_review",
        ])

    product_counts = {}
    if identity is not None and len(identity) > 0:
        product_counts = (
            identity[["product_id", "ingredient_raw"]].drop_duplicates()
            .groupby("ingredient_raw")["product_id"].nunique().to_dict()
        )

    rows = []
    for ingredient, group in findings.groupby("ingredient_raw"):
        blocks = sorted(set(
            group.loc[group["severity"] == SEVERITY_BLOCKING, "standard"]
        ))
        reviews = sorted(set(
            group.loc[group["severity"] == SEVERITY_REVIEW, "standard"]
        ) - set(blocks))
        rows.append({
            "ingredient_raw": ingredient,
            "products_affected": int(product_counts.get(ingredient, 0)),
            "blocks": ", ".join(blocks) if blocks else "—",
            "needs_review": ", ".join(reviews) if reviews else "—",
            "blocked_standard_count": len(blocks),
        })
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["blocked_standard_count", "products_affected"], ascending=False
        )
        .reset_index(drop=True)
    )


def product_certification_status(product_screen: pd.DataFrame, product_id) -> pd.DataFrame:
    """The three certification rows for one product, in display order."""
    if product_screen is None or len(product_screen) == 0:
        return pd.DataFrame()
    rows = product_screen[product_screen["product_id"] == product_id]
    if len(rows) == 0:
        return rows
    order = {key: i for i, key in enumerate(STANDARD_KEYS)}
    return rows.assign(_o=rows["standard_key"].map(order)).sort_values("_o").drop(columns="_o")
