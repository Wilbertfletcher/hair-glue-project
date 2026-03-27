## DEC-006: US GHS Hazard Data Integration Approach

**Date:** 2026-03-27  
**Status:** In Progress  
**Owner:** Wilbert J Fletcher III

### Problem Statement

US GHS hazard data is not natively supported by GHScrunch. The tool only processes Japan, Korea, and New Zealand government datasets. For US hazard data, an external dataset (e.g., EPA CompTox Dashboard CSV) must be downloaded and integrated via a custom script or pipeline extension. GHScrunch may be extended, but is not plug-and-play for US data.

### Decision

Integrate US GHS hazard data by downloading a structured dataset (EPA CompTox Dashboard CSV or equivalent), placing it in data/raw/, and writing a custom script to join by CASRN. Optionally, extend GHScrunch or pipeline for US data parsing. Documented in STATUS.md and TODO.md.

### Implementation Details

- Download EPA CompTox GHS hazard CSV and place in data/raw/
- Write/extend script to join hazard data to chemical dimension by CASRN
- Optionally, extend GHScrunch or pipeline for US data parsing
- Document blockers and progress in STATUS.md, TODO.md, and GOTCHAS.md

### Alternatives Considered

1. **Extend GHScrunch for US data:** Possible, but requires significant code changes and data mapping
2. **Manual hazard lookup:** Not scalable for automated pipeline
3. **Accept NULL fields:** Not acceptable for regulatory analysis; must populate hazard fields for US chemicals
# Project Decisions

## DEC-004: Defer Hazard Enrichment to M2

**Date:** 2026-03-25  
**Status:** Approved  
**Owner:** Wilbert J Fletcher III  

### Problem Statement

Initial attempts to source hazard classification data from public APIs (EPA CompTox, PubChem) revealed significant limitations:

- **EPA CompTox API**: Does not expose structured GHS hazard classifications in a programmatically accessible format
- **PubChem API**: Hazard data is present but not consistently structured or complete for regulatory purposes
- **Other sources**: ECHA REACH API and ChemSpider require API keys or have usage restrictions that make them unsuitable for local-first pipeline

### Decision

**Defer hazard enrichment to M2** due to hazard data source limitations.

### Implementation Details

- **M1.1 Scope**: Hazard-related columns exist in canonical schema but remain NULL/empty by design
- **Schema Ready**: All hazard fields (ghs_classes, signal_word, hazard_statements, etc.) are included in dim_chemical with hazard_status="PENDING_SOURCE"
- **Pipeline Continuity**: Full end-to-end pipeline remains runnable (CSCP ingest → curated Parquet → DuckDB warehouse)
- **M1.2+ Unblocked**: Structural readiness for hazard data without actual data population

### Next Steps

- **M2 Planning**: Identify alternative hazard data sources (paid APIs, licensed databases, manual curation)
- **Schema Evolution**: Hazard fields remain in place; population logic to be implemented in M2
- **Monitoring**: v_hazard_pending_summary view tracks pending status (should show 0% populated in M1)

### Alternatives Considered

1. **Proceed with limited data**: Rejected due to incomplete coverage and data quality concerns
2. **Manual hazard lookup**: Rejected as not scalable for automated pipeline
3. **Accept NULL fields**: Current approach maintains schema readiness without compromising pipeline integrity

---

## DEC-005: ECHA REACH API Integration Framework

**Date:** 2026-03-25  
**Status:** Implemented (Framework Ready)  
**Owner:** Senior Python Data Engineer  

### Context

Following DEC-004, ECHA REACH was identified as the most promising source for comprehensive GHS hazard classifications. However, programmatic API access requires registration and credentials.

### Decision

**Implement ECHA REACH API integration framework** with mock data for development and production-ready structure for when API access is obtained.

### Implementation Details

- **API Client**: `pipeline/extract/echa_reach.py` with `ECHARearchAPI` class
- **Mock Data**: Includes sample hazard data for common chemicals (water, ethanol) for testing
- **Batch Processing**: `fetch_hazards_batch()` method with rate limiting
- **File-based Alternative**: `load_echa_hazards_from_file()` for bulk downloaded ECHA datasets
- **CLI Integration**: `python -m pipeline.cli enrich-hazards` command
- **Schema Compatibility**: Hazard fields match dim_chemical schema

### API Access Requirements

To activate full functionality:

1. Register for ECHA API access at https://echa.europa.eu/en/information-on-chemicals/api
2. Obtain API key and update `ECHARearchAPI.__init__()`
3. Uncomment actual API call in `search_by_casrn()`
4. Adjust data extraction logic based on actual API response structure

### Current Status

- ✅ Framework implemented and tested with mock data
- ✅ CLI command functional
- ✅ Schema integration complete
- ⏳ API credentials pending (requires ECHA registration)
- ⏳ Response structure validation pending

### Testing

```bash
# Test with mock data
python -m pipeline.cli enrich-hazards

# Expected output: All chemicals remain PENDING_SOURCE (mock data limited)
# Once API access available: Chemicals with CASRNs will be ENRICHED
```

### File-based Alternative

For immediate hazard data population using downloaded ECHA datasets:

```python
from pipeline.extract.echa_reach import load_echa_hazards_from_file
hazard_df = load_echa_hazards_from_file("path/to/echa_hazards.csv")
```