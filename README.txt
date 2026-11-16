Reproducibility code supplement — Kunal Dubey

This archive contains the frozen analysis scripts, their input rule template,
publication-reporting code and frozen policy. It contains no cached XPT datasets
or reference PDFs/XML files. Data-use permissions remain unresolved.

The original rule template contains hypotheses and unverified catalogue claims;
it is an executable input, not a report of confirmed results.

To reproduce the study, use a separate clean workspace with the original layout,
the permitted cached inputs listed in audit/frozen_policy.json at their specified
paths, and the package versions recorded in Publication_Evidence_Snapshot.json.
Do not overwrite or alter the original study's locked outputs.

The scientific entry point is python scripts/clinical/run_scoped_study.py.
Running it performs a new reconstruction and challenge experiment; it was NOT
run to assemble this submission package. The reporting-only entry point is
python scripts/publication/build_publication.py --require-complete.

Reproduction requires the source cache; this code-only archive is not a
self-contained executable dataset. Confirm permissions before sharing any
data or source-derived materials. No redistribution license is granted here.
