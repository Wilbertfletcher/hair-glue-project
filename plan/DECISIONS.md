# Hair Glue Project — Decision Log

> **Purpose:** A permanent record of resolved design questions.
> When an open question is settled, add an entry here with the date, rationale, and
> any consequences for other documents.
>
> **Do NOT delete old decisions** — they explain why things are the way they are.
> If a decision is revised, append an `**Amended:**` note to the original entry;
> do not overwrite it.

Format:
```
## DEC-NNN: Short title
**Question:** What was the open question?
**Decision (YYYY-MM-DD):** What was decided, and why.
**Consequences:** What changes as a result (files to update, tasks that unblock, etc.)
**Source:** Where the question came from.
```

---

## DEC-001: Hair-Glue Keyword Filtering Scope (Precision vs. Recall)

**Question:** Should the hair-glue keyword filter prioritize high precision (strict keywords, fewer false positives) or broader scope (reduce false negatives)? Are there specific product types (e.g., lace glue vs. bonding glue) that should be explicitly included or excluded?

**Decision (2026-03-25):** Use HIGH-PRECISION approach. Keep PRIMARY_KWS strict and accept false negatives. Do NOT expand with vague terms like "hold", "grip", or "sealer" in Phase 1.

Product Scope:
- INCLUDE: lace glue, wig glue, bonding glue, weave glue, closure/frontal adhesives, edge control
- EXCLUDE: gels, sprays, pomades, waxes, lash/nail glue, non-cosmetic adhesives

Do NOT use brand names or product lines as inclusion criteria. Brands may be analyzed only AFTER subset selection, never for filtering.

**Implementation Note (2026-03-25):** Initially added "edge" to PRIMARY_KWS to capture edge control products, but testing revealed it matches shaving products (false positives). Removed "edge" to maintain high precision. Edge control products without explicit glue terms will be false negatives, acceptable for Phase 1.

**Consequences:**
- PRIMARY_KWS updated to include "edge" for edge control products
- Keyword filtering remains conservative to minimize false positives
- Broader recall deferred to Phase 2
- Preserves interpretability of chemical frequency and functional use mapping
- Unblocks M0.2 (dimension table building)

---

## DEC-002: Hazard Data Source Selection (M1.1)

**Question:** Which authoritative sources should be used for GHS hazard classifications? Trade-off between coverage, data quality, latency, and cost?

**Decision (2026-03-25):** Three-tier strategy:
1. **Primary (M0-matched chemicals, 91 rows):** EPA CompTox Dashboard API
   - Rationale: Free, comprehensive (~700k chemicals), direct GHS classifications, excellent API
   - Query by CAS number; retrieve H-codes, signal words, pictograms, hazard phrases
2. **Fallback (Unmatched chemicals, 56 rows):** PubChem (already integrated in M0.3)
   - Rationale: Free, good coverage, proven API, can fuzzy-match by ingredient name
   - Risk: Fuzzier matching (lower confidence) — will mark as "fallback_fuzzy_match"
3. **Secondary (Deferred to M2+):** ECHA REACH database
   - Rationale: Most comprehensive EU regulations, but slower API and rate-limited
   - Use for regulatory verification and high-priority chemicals only

**Not Selected:** NIOSH, ATSDR, ChemSpider, paid databases (too slow or expensive for Phase 1)

**Implementation in M1.1:**
- Implement EPA API integration first (target ≥80% match rate on 91 chemicals)
- Implement PubChem fallback as backup (target ≥50% match rate on 56 unmatched)
- Flag all fallback matches with confidence < 0.8; clearly distinguish in reports
- Document any API failures or rate-limit issues in `logs/M1.1_hazard_sourcing.log`

**Consequences:**
- Unblocks M1.1 task in TODO.md
- Requires two API integrations (EPA + PubChem)
- Creates M1.1 output table: `warehouse/ref_chemicals_hazard.parquet`
- Sets up M1.2 hazard classification and risk scoring

**Source:** Stakeholder input + independent hazard data source evaluation (2026-03-25)

---

## DEC-003: Hazard Risk Scoring Model (M1.2)

**Question:** How should we aggregate multiple GHS hazards per product into a single risk score? What weighting should reflect true hazard severity?

**Decision (2026-03-25):** Linear scoring algorithm, 0.0–100.0 scale:
- Base score: 0
- Add 50 per hazard with signal word "Danger"
- Add 25 per hazard with signal word "Warning"
- Add 15 per chemical with reproductive/developmental hazard
- Add 10 per suspected carcinogen; +20 per confirmed carcinogen
- Subtract 5 if match_confidence ≥ 0.9 (exact CAS match, bonus)
- Add 10 if match_confidence < 0.5 (fuzzy match, penalty for uncertainty)
- Cap final score at 100

**Rationale:** 
- Danger signal word represents more severe hazards (acute toxicity, serious health effects) → higher weight
- Warning represents moderate concerns → moderate weight
- Reproductive/carcinogen hazards warrant special emphasis (future health impacts)
- Confidence adjustment accounts for data quality (exact matches are more reliable)

**Risk Classifications:**
- HIGH: Max signal word = "Danger" OR reproductive hazard count > 0 OR carcinogen count > 0
- MEDIUM: Max signal word = "Warning" AND no special hazards
- LOW: No hazardous ingredients AND high match confidence
- NO_DATA: Match confidence < 0.5 (unreliable; insufficient data)

**Limitations:** 
- Algorithm is somewhat arbitrary; may need refinement based on stakeholder feedback
- Does not account for exposure route (inhalation vs. dermal vs. ingestion)
- Does not account for concentration thresholds (e.g., formaldehyde <0.2% is exempt from some regulations)

**If Stakeholder Disagrees:** 
- Update weighting constants in `warehouse/build_hazard_dimensions.py` 
- Append **Amended (YYYY-MM-DD)** note to this decision
- Re-run M1.2 with new weights; regenerate reports

**Consequences:**
- Defines scoring logic for M1.2 task
- Creates product_hazard_summary.parquet with hazard_score and hazard_flag columns
- Feeds into M1.3 brand/category risk analysis

**Source:** Stakeholder input + independent risk assessment best practices (2026-03-25)

<!-- 
Add new decisions by appending below. Keep DEC numbering sequential.
To amend an existing decision (if circumstances changed):
  Append to the entry: **Amended (YYYY-MM-DD):** <what changed and why>
  Do NOT remove the original decision text.
-->

## DEC-004: ChemSpider API Integration for Chemical Structure Data

**Question:** Should we integrate ChemSpider API for chemical structure data (SMILES, InChIKey, molecular properties) to complement ECHA hazard data? What fields should be prioritized?

**Decision (2026-03-25):** Yes, integrate ChemSpider API as secondary enrichment source. Prioritize core structure identifiers and basic molecular properties.

Selected Fields (in priority order):
1. **SMILES** - Canonical SMILES string for chemical structure
2. **InChIKey** - Standard chemical identifier for database cross-referencing  
3. **ChemSpider ID** - Primary identifier in ChemSpider database
4. **Molecular Formula** - Chemical composition
5. **Molecular Weight** - Basic physical property

**Rationale:** 
- ChemSpider provides high-quality, curated chemical structure data
- SMILES and InChIKey enable integration with cheminformatics tools
- Complements ECHA hazard data with structural information
- Free API with reasonable rate limits for research use

**Implementation:**
- Query by CASRN (primary key from CSCP data)
- Batch processing with rate limiting (1 request/second)
- Store in dim_chemical.parquet alongside ECHA hazard fields
- Mock data for development (water/ethanol test cases)
- Production requires API key registration at developer.rsc.org

**Not Selected:** Advanced properties (logP, pKa, etc.) - deferred to future phases

**Consequences:**
- Extends dim_chemical table with structure fields
- Adds enrich-chemspider CLI command
- Creates pipeline/extract/chemspider.py and pipeline/transform/enrich_chemspider.py
- Requires API key for production data access
- Unblocks comprehensive chemical profiling for regulatory analysis

**Source:** Pipeline expansion requirements + chemical data source evaluation (2026-03-25)
