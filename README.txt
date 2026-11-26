CDISCPILOT01 — Paired-perturbation feasibility study
Reproducibility code and source-provenance supplement
Author: Kunal Dubey, Independent Researcher, Garner, NC, USA

PURPOSE

This repository documents a computational feasibility study comparing two
clinical data review rule policies (DRP-A and DRP-B) using paired synthetic
perturbations of CDISCPILOT01 reference data. It contains the frozen analysis
scripts, input rule template, frozen policy, reporting code and source
verification metadata. It is not a validation of all 125 catalogue rules or
a demonstration of clinical non-inferiority or operational time savings.

The original rule template contains hypotheses and unverified catalogue
claims; it is an executable study input, not a report of confirmed results.

FROZEN STUDY AND VERSION HISTORY

Original frozen code commit:
https://github.com/kunaldubey-115/cdiscpilot01-rbdm-reproducibility/tree/401f4bf9865e8327b5a1b9ce3bf2c91c88e3278a

Post-experiment source-manifest documentation commit:
https://github.com/kunaldubey-115/cdiscpilot01-rbdm-reproducibility/tree/ac7f1904272ca3280e1016df8ec88ffed99f07e2/frozen_source_manifest

Frozen policy: audit/frozen_policy.json
Policy SHA-256:
a8f92a1aa9a0865c5eb55367bff4fb46f0f5a5c4be4cd77b557c5e5aa55ea700

The recovered frozen-source archive and subsequent documentation additions do
not change the original scientific code, rule policies, source inputs or
original locked results. The original code version remains available at the
commit above. No new experiment was executed for these documentation updates.

REPOSITORY CONTENTS

audit/                         Frozen policy and protected file hashes
scripts/clinical/              Frozen analysis and verification scripts
scripts/clinical/input/        Original rule template
scripts/publication/           Original publication-reporting code
reporting_revision/            Separate reporting-only revision
frozen_source_manifest/        Source provenance and verification metadata
results/                       Aggregate results and evidence index

SOURCE DATA AND VERIFICATION

The original 33 frozen input paths, including cached copies and local study
inputs, have been retained separately in
CDISCPILOT01_Frozen_Source_Data_v1.zip. All 33 archived files were verified
against the SHA-256 hashes recorded in the frozen study policy.

Retained source archive SHA-256:
ded48ed9207df31d55582686f787fdf9b4ac18399387c316f01eb183226ba242

The public repository contains provenance metadata, not the original
third-party transport datasets or reference PDFs/XML. See:

  frozen_source_manifest/README.md
  frozen_source_manifest/SHA256SUMS.txt
  frozen_source_manifest/source_manifest.json
  frozen_source_manifest/verify_frozen_sources.py

CDISC pilot project: https://github.com/cdisc-org/sdtm-adam-pilot-project
PHUSE scripts: https://github.com/phuse-org/phuse-scripts

The source manifest distinguishes inputs retrieved at a pinned CDISC commit,
inputs retrieved from the PHUSE master branch, and local study inputs. PHUSE
upstream files were not pinned to a commit; their recorded checksums establish
the identity of the retained copies, not the identity of current upstream
versions.

Follow the source-manifest README to verify permitted local copies against the
recorded hashes. The verification script reads files in a local files/
directory and does not run the clinical experiment. A public repository
checkout alone does not contain all 33 files.

EXECUTION AND REPORTING

Use a separate clean workspace with the original file layout, the permitted
cached inputs listed in the frozen policy and source manifest, and an
appropriately documented software environment. Do not overwrite or alter the
original study's locked outputs or remove its run-start protection.

Scientific entry point:
  python scripts/clinical/run_scoped_study.py

This performs a new reconstruction and challenge experiment. It is not needed
to verify source checksums or review the saved publication results, and was not
run to prepare this documentation.

Reporting-only entry point:
  python scripts/publication/build_publication.py --require-complete

The reporting-only revision is described in reporting_revision/README.txt.
Regenerating reports requires the exact original saved result and policy files
at their expected paths. The original reporting materials may differ from
later editorial versions of the manuscript.

The original Publication_Evidence_Snapshot.json and publication results
workbook are retained separately and are not included in the public repository.
The results/ directory provides a separate, post-freeze aggregate reporting
extract of the saved outputs, with no source data, subject-level examples or
mutation identifiers. See results/README.md for definitions and limitations. Software versions recorded in the snapshot describe the reporting
environment; they do not independently establish the original clinical
execution environment. The original scoped_results.json and raw flag and
attribution ledgers are not included in this repository. Their absence limits
independent verification of the saved results. The expected scoped_results.json
SHA-256 is recorded in audit/protected-hashes.json.

Source-file checksum verification and frozen code identity do not constitute
an independent end-to-end reproduction of the experiment.

DATA USE AND ATTRIBUTION

Original CDISC and PHUSE source transport files were used as received for the
unperturbed reference inputs and were preserved unchanged on disk. Synthetic
perturbations were applied to temporary in-memory working copies. No original
or modified third-party transport datasets are redistributed here.

Third-party source materials remain subject to their applicable terms and
attribution requirements. Separate written authorization has not been
obtained, and the applicability of those terms to the perturbation analysis
has not been independently established. This repository does not grant a
license to redistribute or alter third-party materials. Confirm applicable
permissions before using or sharing source data or source-derived materials.
