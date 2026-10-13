# Literature & Data Sources

Works cited by the Hair Glue Project pipeline, reports, and dashboard.
Each entry notes where it's used in the repo. The same entries appear in the
Dangerous Beauty proposal's `references.bib` where they're cited there.

---

## Primary literature and datasets

### Boatman, Ferland & Whitehead (2026). Curated NTA consumer-product chemicals

> Boatman, A. K.; Ferland, T. M.; Whitehead, H. D. *Curated Chemicals Reported in
> Consumer Products Using Non-Targeted Analyses (NTA)* [Data set]. UL Research
> Institutes, Chemical Insights, Morrisville, NC, 2026. Release 2026-05-15.

**APA 7:** Boatman, A. K., Ferland, T. M., & Whitehead, H. D. (2026). *Curated chemicals
reported in consumer products using non-targeted analyses (NTA)* (Release 2026-05-15)
[Data set]. UL Research Institutes, Chemical Insights.

**BibTeX key:** `boatman2026nta`

- **What it is:** 11,952 chemical detections from 81 peer-reviewed non-targeted analysis
  (HRMS) studies of consumer products; 6,978 unique chemicals mapped to a DTXSID or PubChem
  CID, each flagged for presence in CPDat, ExpoCast, NHANES, ToxValDB, and ToxCast.
- **Local copy:** `data/raw/nta/NTA_consumer_products_curation_results_20260515.xlsx`
- **Used in:** `pipeline/extract/nta_curation.py`, `warehouse/source_nta_data.py`,
  `reports/M3.5_nta_crossref_report.md`, dashboard Chemical Database page
  ("Measured in Real Products").
- **Why it matters here:** it's the project's only source of *measured* (as opposed to
  *declared*) product chemistry. See DEC-014.
- **TODO:** add the DOI or repository URL once the dataset's landing page is public.

---

## Companion references cited by the NTA dataset

Resources the NTA dataset uses for its identifier mapping and evidence flags. Cite these
when reporting the corresponding flag.

1. Dionisio, K. L. et al. (2018). The Chemical and Products Database, a resource for
   exposure-relevant data on chemicals in consumer products. *Scientific Data*, 5, 180125.
   https://doi.org/10.1038/sdata.2018.125 — CPDat categories, `cpdat_yn`
2. Williams, A. J. et al. (2017). The CompTox Chemistry Dashboard: A community data resource
   for environmental chemistry. *Journal of Cheminformatics*, 9, 61.
   https://doi.org/10.1186/s13321-017-0247-6 — DTXSID mapping
3. Kim, S. et al. (2025). PubChem 2025 update. *Nucleic Acids Research*, 53(D1).
   https://doi.org/10.1093/nar/gkae1059 — PubChem CID mapping
4. Djoumbou Feunang, Y. et al. (2016). ClassyFire: automated chemical classification with a
   comprehensive, computable taxonomy. *Journal of Cheminformatics*, 8, 61.
   https://doi.org/10.1186/s13321-016-0174-y — `classyfire_superclass`
5. Wambaugh, J. F., & Rager, J. E. (2022). Exposure forecasting – ExpoCast – for data-poor
   chemicals in commerce and the environment. *JESEE*, 32(6), 783–793.
   https://doi.org/10.1038/s41370-022-00492-z — `expocast_yn`
6. CDC. About the Biomonitoring Data Tables. *National Report on Human Exposure to
   Environmental Chemicals.* https://www.cdc.gov/environmental-exposure-report/data-tables/index.html
   — `nhanes_yn`
7. Wall, J. T. et al. (2025). Development of the Toxicity Values Database, ToxValDB.
   *Computational Toxicology*, 35, 100365. https://doi.org/10.1016/j.comtox.2025.100365
   — `toxvaldb_yn`
8. Richard, A. M. et al. (2016). ToxCast chemical landscape: Paving the road to 21st century
   toxicology. *Chemical Research in Toxicology*, 29(8), 1225–1251.
   https://doi.org/10.1021/acs.chemrestox.6b00135 — `toxcast_yn`
