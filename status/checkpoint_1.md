# Project Status — Wilbert Fletcher — Wednesday - Mar 19, 2026

## What is working
- VS Code project environment is set up and the CSCP dataset loads successfully in Python.
- I created a strict subset for hair glues / weaving adhesives using keyword filtering across product name and category.
- I generated exploratory plots:
  1) Top CSCP categories in the hair-glue subset
  2) Top ingredients reported in hair-glue products
  3) CASRN missingness rate by category (to estimate feasibility of chemical identity resolution)
  (Optional) Top brands represented in the hair-glue subset

## What is not working or needs to change
- CSCP category labels are not standardized, so keyword rules are necessary and may create false positives/negatives.
- CASRN completeness varies across categories, which could limit automated mapping coverage in Phase 1.
- I still need to finalize whether to broaden the keyword rule set beyond the strict primary keywords.

## Feedback requested
- Is the hair-glue/weaving-adhesive subset definition appropriately scoped for Phase 1?
- Should I prioritize high precision (strict keywords) or broaden to reduce false negatives before identity resolution?
- Are there specific hair glue product types (lace glue vs bonding glue) you recommend explicitly including/excluding?