# Exploration Notes — Hair Glue / Weaving Adhesives (CSCP)

## What I loaded
- CSCP CSV file: data/raw/cscp_chemicals_in_cosmetics.csv
- Date: March 24, 2026
- Rows loaded: 114,635

## How I defined "hair glue / weaving adhesives"
I filtered rows using keywords that appear in:
- product_name and category_raw

Primary keywords used:
glue, adhesive, bond, bonding, wig, lace, weave, closure, frontal

Why this is a good scope:
- High precision subset
- Matches my project focus and keeps Phase 1 realistic

Limitations:
- Some glue products might not include these keywords (false negatives)
- Some hits might be unrelated (false positives)

## Plot 1 — Top categories (hair glue subset)
- File: figures/explore_1_top_categories_hair_glue.png
- What I notice:

## Plot 2 — Top ingredients (hair glue subset)
- File: figures/explore_2_top_ingredients_hair_glue.png
- What I notice:

## Plot 3 — CAS missingness rate by category
- File: figures/explore_3_cas_missingness_by_category.png
- What I notice:
- What this means for identity resolution:

## (Optional) Plot 4 — Top brands
- File: figures/explore_4_top_brands_hair_glue.png
- What I notice:

## Data quality issues I found
- Missing CAS: [high/medium/low] (fill in)
- Category labels inconsistent: [yes/no] (fill in)
- Anything surprising:

## What I will do next
1. Lock final hair-glue keyword rules
2. Build the product dimension + product-ingredient link table (Parquet)
3. Start chemical identity resolution (CAS-first)