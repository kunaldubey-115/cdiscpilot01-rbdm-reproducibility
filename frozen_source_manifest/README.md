# CDISCPILOT01 frozen source manifest (v1)

Author: Kunal Dubey

## Purpose and freeze status

This directory provides source provenance and checksum verification metadata for
the frozen CDISCPILOT01 DRP-A versus DRP-B paired-perturbation feasibility study.
The original 33 hash-locked input files are retained separately in
`CDISCPILOT01_Frozen_Source_Data_v1.zip`. All 33 archived files match the SHA-256
hashes recorded in the frozen study policy. The original source transport files
were used as received for the unperturbed reference inputs and were not modified
on disk. Synthetic perturbations were applied to temporary in-memory working
copies only.

This manifest is a post-experiment reproducibility documentation addition. No
experimental rules, frozen code, source files, or original results were changed,
and no experiment was rerun to prepare this documentation.

## Frozen identifiers

- Original code commit: [`401f4bf9865e8327b5a1b9ce3bf2c91c88e3278a`](https://github.com/kunaldubey-115/cdiscpilot01-rbdm-reproducibility/tree/401f4bf9865e8327b5a1b9ce3bf2c91c88e3278a)
- Frozen policy: [`audit/frozen_policy.json`](../audit/frozen_policy.json)
- Frozen policy SHA-256: `a8f92a1aa9a0865c5eb55367bff4fb46f0f5a5c4be4cd77b557c5e5aa55ea700`
- Retained source archive SHA-256: `ded48ed9207df31d55582686f787fdf9b4ac18399387c316f01eb183226ba242`
- Frozen input files: 33 (including cached copies)

## Contents of this public directory

- `SHA256SUMS.txt`: original SHA-256 checksums for all 33 input paths.
- `source_manifest.json`: original file-by-file provenance, source locations,
  byte counts, and SHA-256 checksums.
- `verify_frozen_sources.py`: original read-only checksum verification script.
- `README.md`: instructions and limitations for the public manifest.

The actual third-party datasets and reference documents are not included here.
The complete retained source archive is stored separately and is not made public
through this repository.

## Provenance

- Eight input paths correspond to the [CDISC SDTM/ADaM Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project/tree/667511d4b183871d74392ba691c935c38d431d39), pinned to commit `667511d4b183871d74392ba691c935c38d431d39`.
- Twenty-three input paths correspond to the [PHUSE scripts repository](https://github.com/phuse-org/phuse-scripts), retrieved from the `master` branch. That branch was not pinned to a commit. The recorded SHA-256 hashes identify the exact retained bytes; current upstream versions must be verified before use.
- Two files are local study inputs: the author-supplied rule template (`scripts/clinical/input/template.xlsx`, also included in the frozen code commit) and the study-generated reference-evidence citation manifest (`generated-artifacts/clinical/reference-evidence/manifest.json`, retained in the source archive).

Full file-specific source locations and hashes are listed in `source_manifest.json`.

## Verification instructions

Use a separate local workspace, outside a public Git checkout, and obtain the
source files under their applicable terms. Place the verification script and
`SHA256SUMS.txt` in a folder alongside a `files/` directory. The paths under
`files/` must match those listed in `SHA256SUMS.txt` exactly. The two locally
supplied inputs must also be present for complete verification.

From that local folder, run:

```bash
python3 verify_frozen_sources.py
```

Expected output when all original files are present and match:

```text
33/33 files verified
```

Running the script on a public repository checkout alone will not verify all 33
files, because the full source cache is not included. Missing or changed inputs
must be resolved before attempting reproduction. The original frozen archive can
be verified locally by extracting it into a separate workspace and running its
included verification script. The script checks file identity only; it does not
execute the study or establish permission to use the inputs.

## Data-use and redistribution

Third-party source materials remain subject to their applicable terms and
attribution requirements. This directory provides metadata rather than granting
rights to redistribute or modify those materials. The complete source archive is
retained privately pending clarification of applicable data-use and redistribution
permissions. The status of those permissions is not resolved by checksum verification.

## Reproducibility scope

Verification establishes the identity of the retained source inputs. It does not
establish independent execution reproducibility, validate the original software
environment, or replace the original raw result and audit ledgers. The frozen
scientific code must be preserved unchanged. Any future verification run must use
a separate workspace and must not overwrite the original locked results.

## Frozen input inventory

| Path | Role | Bytes | SHA-256 (prefix) |
|---|---|---:|---|
| `generated-artifacts/clinical/data/adae.xpt` | ADaM dataset — ground-truth reconstruction target | 713,600 | `b8678e70946473a7…` |
| `generated-artifacts/clinical/data/adam-dataguide.pdf` | ADaM data guide | 92,311 | `045d5c2cfd72d0fc…` |
| `generated-artifacts/clinical/data/adam-define.xml` | ADaM define.xml | 606,474 | `3240034eea9ac5e2…` |
| `generated-artifacts/clinical/data/adlbc.xpt` | ADaM dataset — ground-truth reconstruction target | 34,242,960 | `b9f6b5106965b5e2…` |
| `generated-artifacts/clinical/data/adlbh.xpt` | ADaM dataset — ground-truth reconstruction target | 23,025,920 | `de568850f5585266…` |
| `generated-artifacts/clinical/data/adqsadas.xpt` | ADaM dataset — ground-truth reconstruction target | 5,178,480 | `ac3fa1217651810b…` |
| `generated-artifacts/clinical/data/adqscibc.xpt` | ADaM dataset — ground-truth reconstruction target | 290,480 | `16e7118f606d907e…` |
| `generated-artifacts/clinical/data/adqsnpix.xpt` | ADaM dataset — ground-truth reconstruction target | 13,147,600 | `90cf438913cfb976…` |
| `generated-artifacts/clinical/data/adsl.xpt` | ADaM dataset — ground-truth reconstruction target | 114,640 | `c5139f873a93ef6a…` |
| `generated-artifacts/clinical/data/adtte.xpt` | ADaM dataset — ground-truth reconstruction target | 91,840 | `68513fc4126744b6…` |
| `generated-artifacts/clinical/data/advs.xpt` | ADaM dataset — ground-truth reconstruction target | 13,632,480 | `28233c8ed038d0f3…` |
| `generated-artifacts/clinical/data/ae.xpt` | SDTM dataset (SAS transport) | 1,495,680 | `05cf23dadadf1b6a…` |
| `generated-artifacts/clinical/data/blankcrf.pdf` | Annotated CRF | 2,119,938 | `f05d54711735bbad…` |
| `generated-artifacts/clinical/data/cdisc-667511d4b183871d74392ba691c935c38d431d39-blankcrf.pdf` | Annotated CRF (content-addressed copy) | 2,119,938 | `f05d54711735bbad…` |
| `generated-artifacts/clinical/data/cdisc-667511d4b183871d74392ba691c935c38d431d39-dataguide.pdf` | ADaM data guide (content-addressed copy) | 92,311 | `045d5c2cfd72d0fc…` |
| `generated-artifacts/clinical/data/cdisc-blankcrf.pdf` | Annotated CRF (cached copy) | 2,119,938 | `f05d54711735bbad…` |
| `generated-artifacts/clinical/data/cm.xpt` | SDTM dataset (SAS transport) | 3,758,720 | `bb31e91b93a8e485…` |
| `generated-artifacts/clinical/data/dm.xpt` | SDTM dataset (SAS transport) | 110,800 | `7327baea97fd532d…` |
| `generated-artifacts/clinical/data/ds.xpt` | SDTM dataset (SAS transport) | 146,800 | `0dea6d298cf248c9…` |
| `generated-artifacts/clinical/data/ex.xpt` | SDTM dataset (SAS transport) | 87,120 | `37daacb3fdafba7b…` |
| `generated-artifacts/clinical/data/lb.xpt` | SDTM dataset (SAS transport) | 34,262,560 | `47394de7c6484bdf…` |
| `generated-artifacts/clinical/data/mh.xpt` | SDTM dataset (SAS transport) | 1,586,960 | `d4c3539c2e9e1461…` |
| `generated-artifacts/clinical/data/qs.xpt` | SDTM dataset (SAS transport) | 33,849,760 | `a1a68fbebbceb623…` |
| `generated-artifacts/clinical/data/sc.xpt` | SDTM dataset (SAS transport) | 30,160 | `9dca4cc3ef9631cb…` |
| `generated-artifacts/clinical/data/sdtm-define.xml` | SDTM define.xml | 262,416 | `b55f196e37a379be…` |
| `generated-artifacts/clinical/data/supplemental/adae.sas` | Supplemental CDISC pilot submission file | 5,794 | `bf752a85bb3301a2…` |
| `generated-artifacts/clinical/data/supplemental/adam-define.xml` | Supplemental CDISC pilot submission file | 587,336 | `7e6d580e0839564f…` |
| `generated-artifacts/clinical/data/supplemental/sv.xpt` | Supplemental CDISC pilot submission file | 286,560 | `ea831a4aceede71d…` |
| `generated-artifacts/clinical/data/ts.xpt` | SDTM dataset (SAS transport) | 22,160 | `517ceea43a3c363e…` |
| `generated-artifacts/clinical/data/vs.xpt` | SDTM dataset (SAS transport) | 24,014,960 | `eb54bb58944c1d72…` |
| `generated-artifacts/clinical/reference-evidence/cdiscpilot01.pdf` | CSR with protocol/SAP appendices | 5,985,424 | `0cab016c76abb3dc…` |
| `generated-artifacts/clinical/reference-evidence/manifest.json` | Reference-evidence page citation manifest (study-generated) | 1,442 | `15c2488f8b408494…` |
| `scripts/clinical/input/template.xlsx` | Author-supplied DRP rule template workbook | 54,168 | `f15d9cf8a5c1fd49…` |
