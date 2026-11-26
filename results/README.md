# Aggregate study results (post-freeze reporting extract)

This directory contains only aggregate results derived from the original saved
publication workbook and evidence snapshot. The original archives remain
unchanged and retained separately. No source datasets, subject identifiers,
record-level examples, mutation identifiers, CRF annotation text, original
clinical documents, or reconstructed patient-level data are included.

- `pathway_metrics.csv`: review-episode and critical-designated capture counts
  for each scenario, reconstruction track and pathway (8 rows).
- `paired_comparisons.csv`: episode reductions and critical-designated paired
  misses (4 rows). Percentage reductions are rounded to six decimal places.
- `mutation_family.csv`: all 16 mutation families per scenario (32 rows),
  derived from 1,280 saved mutation-recovery records. Counts are identical in
  both reconstruction tracks and are shown once per scenario and family.
- `output_agreement.csv`: the seven audited output categories. Each row's
  counts apply to each of the 12 comparison blocks, not pooled observations.
- `aggregate_evidence_index.json`: hashes of the separately retained original
  evidence and source archive, immutable code and manifest references, and
  recorded reporting-environment versions.

Source: CDISCPILOT01_Publication_Results.xlsx (Outcome_A, Outcome_B, Outcome_C,
Paired_Query_and_Miss_Summary and Mutation_Recovery) and
Publication_Evidence_Snapshot.json. The saved outcome and paired summary rows
were reconciled across those two artifacts. The original workbook and snapshot
are not redistributed here. The aggregate extract is not a replacement for the
original raw flags, truth/correction ledgers or scoped_results.json.

Review episodes are deduplicated flags, not adjudicated queries or staff time.
Capture is record-level, and correction is the study's oracle correction, not
field-specific detection or observed human resolution. Criticality is the
study's designation, not independent clinical adjudication. The tracks share
reconstruction code. Cell counts include values and keys and are not
independent observations; 118,482 serialized cells (19,986 value cells and
98,496 key/identifier cells) were compared per block. This is a bounded
feasibility study, not evidence of clinical non-inferiority or full validation.

The original inputs remain subject to applicable source terms. Their
applicability to the perturbation analysis and dissemination has not been
independently established.
CDISC and PHUSE source attribution and terms are described in the root README
and frozen_source_manifest. No third-party source material is redistributed
through this aggregate extract. No experiment was rerun to create it.
