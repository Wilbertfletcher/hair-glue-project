# Certification Screening — Reference

How the dashboard's **Certifications** page works, what it can claim, and what
it cannot.

Code: [`certifications.py`](../certifications.py) · Page:
`page_certifications()` in [`app.py`](../app.py) · Tests:
[`tests/test_certifications.py`](../tests/test_certifications.py)

---

## The three standards

| Standard | Issuer | What it evaluates | Ingredient rules come from |
|---|---|---|---|
| **EWG VERIFIED** | Environmental Working Group | Full ingredient disclosure, avoidance of chemicals of concern, and strict transparency, to verify that personal and hair care products are truly non-toxic | EWG's Unacceptable / Restricted ingredient criteria, built on Skin Deep scoring plus authoritative lists (Prop 65, EU cosmetic restrictions, IARC) |
| **Cradle to Cradle Certified** | Cradle to Cradle Products Innovation Institute | Material health, product circularity, and environmental stewardship, down to specific chemical safety thresholds | The Restricted Substances List / Banned List of Chemicals — CMRs, added formaldehyde, PFAS, phthalates, toxic heavy metals, assessed above 100 ppm |
| **The Living Product Challenge** | International Living Future Institute | Complete material health transparency for consumer goods and personal care items, plus net-positive water and energy; less common for hair care than for building materials | The ILFI Red List plus the Declare-label disclosure requirement down to 100 ppm |

Each standard's full metadata — what it checks, what must be disclosed, what an
ingredient list cannot tell you, and its official criteria URL — lives in
`certifications.STANDARDS`.

## How a product is screened

1. **Profile each ingredient.** `build_chemical_profiles()` joins every distinct
   label ingredient to its GHS hazard record and its regulatory record. Manual
   mappings arrive without a CAS number, so they fall back to a join on the
   label name — that is how they were recorded in the warehouse.
2. **Flag it.** `chemical_flags()` returns `{flag: evidence}` — for example
   `carcinogen`, `reprotox`, `prop65`, `formaldehyde`, `disclosure_gap`. Every
   flag carries the plain-language evidence that produced it, so the dashboard
   can always show its work.
3. **Apply the rules.** Each entry in `RULES` names the flags that trip it and
   what each program does about it: `blocking` or `review`, with the published
   basis quoted per standard. The same finding is often treated differently by
   different programs — a generic CMR substance is banned outright by EWG and
   C2C, but for the Living Product Challenge it is a disclosure-and-justify
   matter unless it is a named Red List class.
4. **Roll up to the product.** `screen_products()` returns one row per
   (product, standard):

   | Status | Meaning |
   |---|---|
   | 🔴 Would not qualify | At least one reported ingredient matches a `blocking` rule |
   | 🟠 Needs review | Nothing banned outright, but something a certifier would question |
   | 🟢 No blockers found | Nothing disqualifying in the chemicals we can see |
   | ⚫ No ingredient data | No reported ingredients on file |

## Limits — read before quoting any number

- **Our ingredient data is not a formula.** CSCP collects only the *reportable
  hazardous* ingredients of a product. "No blockers found" means "nothing
  disqualifying in the chemicals we can see," never "this product would be
  certified." Every product in this database is here precisely because it
  reports at least one chemical of concern, which is why the pass rate is
  near zero.
- **Certification is more than chemistry.** All three programs audit factories,
  packaging, supply-chain disclosure, water and energy use, and social
  fairness. No ingredient table can screen for any of that.
- **Absence of a flag is not safety.** Carbon black is flagged from its IARC
  Group 2B classification because our regulatory table is missing its Prop 65
  entry — other gaps like it may still exist.
- **Criteria change.** `certifications.CRITERIA_REVIEWED` records when the
  published criteria behind `RULES` were last reviewed by a human. Confirm
  against the official criteria before acting on a result.

## Adding or changing a rule

1. Add the flag to `chemical_flags()`, with the evidence string a reader
   would need to check it.
2. Add a `Rule` to `RULES` naming that flag in `triggers`, with an entry in
   `applies` for **every** standard — severity plus the published basis. A test
   enforces full coverage.
3. Add a case to `tests/test_certifications.py`, including a negative case if
   the rule matches on chemical names (see the mica/`difluoride` test — name
   patterns false-positive easily).
4. Re-run `pytest tests/test_certifications.py` and bump `CRITERIA_REVIEWED` if
   you re-checked the published criteria.
