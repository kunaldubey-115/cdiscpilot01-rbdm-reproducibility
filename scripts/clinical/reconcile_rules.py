"""Read-only reconciliation evidence; never changes production rules or populations."""
import csv
import hashlib
import json
from collections import Counter

import openpyxl
import pandas as pd

from fetch_data import ROOT, DATA, SDTM, ADAM
from rules import evaluate_rules


def main():
    template = ROOT / "scripts/clinical/input/template.xlsx"
    paths = {n: DATA / f"{n}.xpt" for n in SDTM + ADAM}
    # Missing input is an error, never a fabricated passing audit.
    data = {n: pd.read_sas(p, format="xport", encoding="cp1252") for n, p in paths.items()}
    w = openpyxl.load_workbook(template)
    results = evaluate_rules(w, data)
    originals = {
        row[0]: row for row in w["Published_Control_DRP_A"].iter_rows(
            min_row=5, max_row=129, values_only=True)
        if str(row[0]).startswith("DRP-A-")
    }
    groups = {
        "C01": [57], "C02": [4], "C03": [24], "C04": [25, 16, 56],
        "C05": [26], "C06": [54], "C07": [58], "C08": [35, 36, 39, 40],
        "C09": [67, 82, 86], "C10": [5, 76, 84, 85, 89],
        "C11": [17, 38, 6, 41, 42], "C12": [3, 53, 54, 55, 56, 57, 58, 59],
    }
    inventory = []
    for result in results:
        row = originals[result["id"]]
        conflicts = [c for c, numbers in groups.items() if int(result["id"][-3:]) in numbers]
        inventory.append({
            **result, "workbookTargets": row[3], "workbookReference": row[6],
            "registerEntries": ", ".join(conflicts or ["C13"]),
            "scientificReview": "Unresolved; execution is not scientific validation",
        })
    a, dm = data["adsl"], data["dm"]
    summary = {
        "scope": "Read-only audit; no change to eligibility, execution status or thresholds",
        "register": "docs/clinical-rule-conflicts.md",
        "statusCounts": dict(Counter(r["status"] for r in results)),
        "populations": {
            "dmRows": len(dm), "dmSubjects": int(dm.USUBJID.nunique()),
            "dmArmCounts": dm.ARM.value_counts(dropna=False).to_dict(),
            "adslRows": len(a), "adslSubjects": int(a.USUBJID.nunique()),
            "adslFlags": {c: a[c].value_counts(dropna=False).to_dict()
                          for c in ["ITTFL", "SAFFL", "EFFFL"]},
        },
        "mmseSensitivityNotEligibility": {
            "population": "All supplied ADSL rows, not all screened subjects",
            "missing": int(a.MMSETOT.isna().sum()),
            "equal24": int(a.MMSETOT.eq(24).sum()),
            "current10to24Failures": int((~a.MMSETOT.between(10, 24)).sum()),
            "documented10to23Failures": int((~a.MMSETOT.between(10, 23)).sum()),
        },
        "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [template, *paths.values(),
                             ROOT / "scripts/clinical/rules.py",
                             ROOT / "scripts/clinical/extended_rules.py"]},
        "rules": inventory,
    }
    out = DATA.parent
    (out / "Rule_Reconciliation.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (out / "Rule_Reconciliation.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(inventory[0]))
        writer.writeheader()
        writer.writerows(inventory)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rules", "sha256")}, indent=2))


if __name__ == "__main__":
    main()
