"""Cache-only safety inventory; not a claim that paired ADaM reconstruction passed."""
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[2]

def main():
    source = openpyxl.load_workbook(ROOT/"scripts/clinical/input/template.xlsx", data_only=True)
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Rule_Safety_Audit_Matrix"
    sheet.append(["Rule ID", "Domain", "Rule description", "Workbook protocol/SAP reference (unverified)",
                  "Source fields", "SDTM-to-ADaM lineage", "CSR/submission dependency",
                  "Mandatory protection assessment", "Original disposition", "Effective disposition",
                  "Suppression rationale / evidence gap"])
    for row in source["Published_Control_DRP_A"].iter_rows(min_row=5, max_row=129, values_only=True):
        rid, _, domain, fields, _, description, reference, tier, disposition = row[:9]
        if rid in ("DRP-A-065", "DRP-A-081"):
            description = f"Verify uniqueness of USUBJID + {domain}SEQ; sequence gaps are allowed."
        protection = ("Potential consent/safety/compliance dependency — retain pending documented adjudication"
                      if domain in ("DM", "DS", "AE", "EX", "LB", "VS", "CM")
                      else "Mandatory protection not yet adjudicated — retain")
        sheet.append([rid, domain, description, reference, fields,
                      "Unverified: joins, windows, imputation, populations, endpoints and safety flags require field-level specification",
                      "Unverified: blueprint/domain association alone does not certify submission independence",
                      protection, disposition, "RETAIN",
                      "Unknown dependency = retain. No suppression approved by this preflight inventory."])
    assert sheet.max_row == 126
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    scope = book.create_sheet("Validation_Gate")
    scope.append(["Status", "Reason"])
    scope.append(["NOT VALIDATED", "No paired cleaning, independent ADaM rebuild or end-to-end outcome has been asserted."])
    scope.append(["Cache-only", "Source XPTs, PDFs, define.xml and existing Protocol_SAP_Blueprint were not modified or downloaded."])
    scope.append(["Prerequisite", "Resolve authoritative derivation specifications and verify clean SDTM reconstruction against all nine ADaM targets before freezing challenges or reporting paired outcomes."])
    output = ROOT/"generated-artifacts/clinical/Paired_Intervention_Preflight.xlsx"
    book.save(output)
    print(output)

if __name__ == "__main__":
    main()
