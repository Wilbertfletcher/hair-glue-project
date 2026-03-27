# Hair Glue Project — Bug Reports

> Lightweight inbox for capturing bugs and data quality issues between sessions.
> At the end of each session, route items from `## Unresolved` to the task system (or GOTCHAS.md) and move verbatim to `## Incorporated into TODO`.
> Bugs confirmed fixed are moved to `## Resolved`.

---

## Unresolved

> Bugs or data quality issues reported but not yet triaged. Add items here when issues are discovered.

### Issue: Category Label Inconsistency in CSCP Data

**Symptom:** The same product may appear under different category labels (e.g., "Hair Adhesive" vs. "Adhesive Gel (Hair)"), making deduplication imprecise.

**Impact:** Keyword filtering and dimension deduplication may miss or duplicate products.

**Workaround:** Currently handled by grouping on (product_name, brand, company, category_raw); see M0.2 task.

**Status:** Observed; not yet formalized as a task.

---

## Incorporated into TODO

> Issues routed to the task system. Once routed, move items here with a reference to the task number.

*(None yet)*

---

## Resolved

> Bugs confirmed fixed and shipped.

*(None yet)*

---

## Known Issues (Not Bugs)

> Distinct from bugs: these are design trade-offs or inherent data limitations, not defects.

### CASRN Completeness Varies by Category (20–80%)

**Description:** Some product categories report CASRN consistently; others rarely do. This is a data characteristic, not a code bug. Handled intentionally in M0.2 (keep null CASRN rows) and M0.3 (fallback matching deferred).

**Reference:** [GOTCHAS.md — CASRN Completeness Varies](../GOTCHAS.md#casrn-completeness-varies-widely-across-categories)

---

## Reporting a New Issue

1. Describe the symptom (what went wrong)
2. Where it occurred (file, line, function)
3. Impact (does it block progress?)
4. Workaround (if any)
5. Add to `## Unresolved` section
6. At session end, route to task system or GOTCHAS.md
