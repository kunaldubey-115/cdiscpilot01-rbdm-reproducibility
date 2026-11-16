"""Export an explicitly blocked paired-study workbook; never invent outcomes."""
import json
import copy
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Font

OUT=Path(__file__).resolve().parents[2]/"generated-artifacts/clinical"

def main():
    report=json.loads((OUT/"clean_rebuild_validation.json").read_text())
    book=openpyxl.Workbook()
    status=book.active
    status.title="Current_Validation_Status"
    status.append(["PAIRED INTERVENTION NOT EXECUTED","This is a blocked-status workbook, not final paired results."])
    status.append(["Gate",report["status"]])
    status.append(["CIBIC+ exception",report["cibicImputationPolicy"]["status"]])
    status.append(["Rule dispositions","Draft conservative inventory only; not frozen for challenge execution while the gate remains blocked."])
    status.append(["Figure","No paired publication figure generated; no paired outcomes exist."])
    status.append([])
    status.append(["Dataset","Status","Reference records","Candidate records","Fields matching throughout"])
    for row in report["coverage"]:
        status.append([row["dataset"],row["status"],row["targetRows"],row.get("rebuiltRows",row["targetRows"]),row["matchingFields"]])
    sources=[
        ("CDISCPILOT01_Final_Verified_Results.xlsx",["Protocol_SAP_Blueprint","CRF_Page_Domain_Annotations"]),
        ("Paired_Intervention_Preflight.xlsx",["Rule_Safety_Audit_Matrix"]),
        ("ADaM_Clean_Rebuild_Validation.xlsx",["CIBIC_Methodology_Decision","CIBIC_Accepted_Rows","ADQSADAS_Comparison","ADQSNPIX_Comparison","ADLBC_Comparison","ADLBH_Comparison","ADVS_Comparison"]),
    ]
    for filename,names in sources:
        original=openpyxl.load_workbook(OUT/filename)
        for name in names:
            if name not in original.sheetnames:raise ValueError(f"Required source tab missing: {name}")
            dest=book.create_sheet(name)
            for row in original[name]:
                for cell in row:
                    dest.cell(cell.row,cell.column,cell.value)
                    if cell.has_style:
                        target=dest.cell(cell.row,cell.column)
                        for attr in ("font","fill","border","alignment","protection"):
                            setattr(target,attr,copy.copy(getattr(cell,attr)))
                        target.number_format=cell.number_format
    assert book["Rule_Safety_Audit_Matrix"].max_row==126
    scenarios=book.create_sheet("Scenario_Status")
    scenarios.append(["Scenario","Seed","Status"])
    for name,seed in [("Development",20261120),("Held-out stress",20261121)]:
        scenarios.append([name,seed,"NOT GENERATED / NOT EXECUTED — clean-reference gate blocked"])
    for name,measures in [
        ("Outcome_A",["Unique discrepancy episodes","Actionable-query yield"]),
        ("Outcome_B",["Critical errors injected","Critical errors detected","Critical errors missed"]),
        ("Outcome_C",["ITTFL / SAFFL / EFFFL / COMP24FL","Three-arm ADAS-Cog ANCOVA","Three-arm CIBIC+ ANOVA","Continuous-dose trend","ADTTE TTDE survival",
                      "CSR 14-2.01","CSR 14-3.01","CSR 14-3.02","CSR 14-3.10","CSR 14-6.04","CSR 14-7.01","CSR 14-7.02"]),
    ]:
        sheet=book.create_sheet(name)
        sheet.append(["Measure","Status","Pathway A","Pathway B","Mismatch rate"])
        for measure in measures:sheet.append([measure,"NOT EVALUATED — no paired runs",None,None,None])
    for sheet in book:
        if sheet.title in ("Protocol_SAP_Blueprint","CRF_Page_Domain_Annotations"):continue
        sheet.freeze_panes="A2"
        for cell in sheet[1]:cell.font=Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width=48
            for cell in col:cell.alignment=Alignment(wrap_text=True,vertical="top")
    book.save(OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx")

if __name__=="__main__":
    main()
