"""Publish current validation context without reinterpreting historical experiments."""
import json
import shutil
import textwrap
import html
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment
from PIL import Image, ImageDraw, ImageFont
import pymupdf

OUT=Path(__file__).resolve().parents[2]/"generated-artifacts/clinical"

def refresh_outputs(fresh_figures=False):
    if (OUT/"scoped-study/scoped_results.json").exists():
        from export_scoped_study import export
        export(json.loads((OUT/"scoped-study/scoped_results.json").read_text()))
        return
    validation=json.loads((OUT/"clean_rebuild_validation.json").read_text())
    coverage=validation["coverage"]
    dual_path=OUT/"dual_track_validation.json"
    dual=json.loads(dual_path.read_text()) if dual_path.exists() else None
    if dual:
        coverage=[dict(r,targetColumns=r["targetFields"]) for r in dual["tracks"]["reference_replication"]["coverage"]]
    passed=sum(r["status"]=="PASSED" for r in coverage)
    conventions=sum(r["status"]=="PASSED (SAP-Aligned Convention)" for r in coverage)
    pending=sum(r["status"].startswith("NOT REBUILT") for r in coverage)
    failed=len(coverage)-passed-conventions-pending
    differences=validation["cibicDiagnostics"][1]["count"]
    stamp=datetime.now(timezone.utc).isoformat()
    headline=f"CURRENT VALIDATION: {passed}/9 dataset comparisons passed; {conventions} SAP-aligned exception accepted; paired challenges NOT EXECUTED."
    notes=[
        headline,
        f"CIBIC+: PASSED (SAP-Aligned Convention). SAP-selected-observation imputation retained. {differences} carried-forward records differ in six date/traceability fields; scores match. User-authorized exception, not exact-reference agreement.",
        f"{pending} rebuilds unimplemented; {failed} candidate rebuilds have not passed validation. The complete nine-dataset gate is {validation['status']}.",
        "Earlier ANCOVA, sensitivity simulations and frozen-ADaM Gate 2 table comparisons are exploratory results, not results from the requested paired intervention.",
        "Reference compatibility does not authenticate original SAS logic. Missing BMI categorized <25 is retained only in compatibility mode with a quality warning.",
        "Sources extend beyond the original cached define.xml/dataguide.pdf: separately added official inputs, SAP, and the published ADAE program were also used.",
        "Numeric agreement uses absolute tolerance 1e-8 and relative tolerance 1e-10; text is compared exactly. No claim of bitwise equality or universal CSR concordance.",
        "The DRP-B efficacy hypothesis has not been demonstrated. No validated majority-rule reduction, critical-error detection result, or paired CSR-wide variance estimate is available.",
    ]
    if dual:
        headline=f"CURRENT VALIDATION: Reference replication — {passed}/9 comparisons passed; {conventions} CIBIC+ exception accepted. Separate SAP-first sensitivity track; paired challenges NOT EXECUTED."
        notes[0]=headline
        notes[2]="Reference-replication clean gate "+("PASSED with the approved exception" if dual["tracks"]["reference_replication"]["passed"] else "BLOCKED")+". SAP-first candidates remain separate; five reference comparisons differ and are not waived. Intervention prerequisites remain unfinished."
        notes[4]="Target-calibrated compatibility is not independent validation or proof of SAP compliance. NPI mean compatibility uses Weeks 6/8/10/12 despite a Week 4–24 label; vital EOT includes Week 26; some missing lab results retain N."
        notes.append("Dual-track study approved: compare each A/B intervention to its own track's clean rebuild; do not pool cross-track differences with intervention effects.")
    archive=OUT/"archive_before_status_update"
    archive.mkdir(exist_ok=True)
    files=list(OUT.glob("*.xlsx"))+list(OUT.glob("*.png"))+[OUT/"analysis.json",OUT/"Variable_Tier_Audit.csv"]
    for path in files:
        if path.exists() and not (archive/path.name).exists():
            shutil.copy2(path,archive/path.name)
    for path in OUT.glob("*.xlsx"):
        book=openpyxl.load_workbook(path)
        if "Current_Validation_Status" in book:
            del book["Current_Validation_Status"]
        # Preserve the required Protocol_SAP_Blueprint first-tab position.
        index=1 if book.sheetnames[0]=="Protocol_SAP_Blueprint" else 0
        sheet=book.create_sheet("Current_Validation_Status",index)
        sheet.append(["Current evidence status","Updated UTC",stamp])
        for note in notes:sheet.append([note])
        sheet.append([])
        sheet.append(["Dataset","Reference records","Matching fields","Target fields","Status"])
        for r in coverage:
            sheet.append([r["dataset"],r["targetRows"],r["matchingFields"],r["targetColumns"],r["status"]])
        sheet.column_dimensions["A"].width=100
        for col in "BCDE":sheet.column_dimensions[col].width=28
        for row in sheet:
            for cell in row:cell.alignment=Alignment(wrap_text=True,vertical="top")
            sheet.row_dimensions[row[0].row].height=42
        sheet["A1"].font=Font(bold=True)
        sheet.freeze_panes="A2"
        book.save(path)
    tier=OUT/"Variable_Tier_Audit.csv"
    frame=pd.read_csv(tier)
    frame["Evidence_Status"]="Provisional classification; paired intervention not executed"
    frame.to_csv(tier,index=False)
    rows=[]
    for path in sorted(p for p in OUT.iterdir() if p.is_file() and p.suffix in (".csv",".xlsx",".json",".pdf",".html",".png")):
        if path.name=="Output_Status_Manifest.csv":continue
        name=path.name
        if name.startswith("ADQSCIBC"):status="PASSED (SAP-Aligned Convention); documented traceability exception retained"
        elif "Experimental_Reference" in name:status="Reference-compatible clean reconstruction matched; target-calibrated, not independent validation or paired evidence"
        elif name in ("dual_track_validation.json","CDISCPILOT01_Paired_Intervention_Results.xlsx"):status="Dual-track clean audit; reference gate passed with scoped CIBIC+ exception; paired outcomes NOT EVALUATED"
        elif name in ("ADaM_Clean_Rebuild_Validation.xlsx","clean_rebuild_validation.json"):status="SAP-first candidate reference comparisons; see separate dual-track reference-replication gate"
        elif "Candidate" in name:status="CANDIDATE ONLY: not validated; not paired-run output"
        elif "Conservative" in name or "Partial" in name:status="Conservative ADSL: 46/48 fields match; not validated"
        elif name.startswith(("ADSL_Reference","ADAE_","ADTTE_")):status="Clean-reference comparison passed within declared tolerance; not paired-run output"
        else:status="Provisional/exploratory; not paired-run evidence"
        rows.append({"file":name,"status":status,"pairedChallengesExecuted":False})
    pd.DataFrame(rows).to_csv(OUT/"Output_Status_Manifest.csv",index=False)
    for name in ["Manuscript_Results_Figure.png","Power_Erosion_and_Query_Reduction.png"]:
        path=OUT/name
        original=archive/name
        if fresh_figures:shutil.copy2(path,original)
        image=Image.open(original).convert("RGB")
        header=Image.new("RGB",(image.width,240),"#fff4df")
        draw=ImageDraw.Draw(header)
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",30) if Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists() else ImageFont.load_default(size=30)
        for i,line in enumerate([
            "EXPLORATORY FIGURE — NOT PAIRED DRP-A / DRP-B RESULTS",
            f"Clean-reference gate: {passed} matched + {conventions} convention accepted. Paired challenges have not run.",
            "SAP-first differences remain; DRP-B efficacy is not established.",
            "Original experiment below is preserved; no new model or CSR-wide concordance claim."
        ]):draw.text((45,20+i*52),line,fill="#332b1f",font=font)
        canvas=Image.new("RGB",(image.width,image.height+240),"white")
        canvas.paste(header,(0,0));canvas.paste(image,(0,240));canvas.save(path,dpi=(300,300))
    sections={
        "Status":"Working manuscript sections, not a completed publication or a proven efficacy claim. Updated "+stamp,
        "Methods":"Source-based reconstruction was evaluated against cached public synthetic CDISCPILOT01 ADaM targets. Target values were used for comparison, not as derivation inputs. Reference-compatible and conservative ADSL conventions were retained separately. CIBIC+ LOCF follows the SAP-selected observation; no alternate latest-unselected-observation method was activated. "+notes[5]+" "+notes[6],
        "Results":"; ".join(f"{r['dataset']}: {r['matchingFields']}/{r['targetColumns']} fields match throughout {r['targetRows']} reference records ({r['status']})" for r in coverage)+f". CIBIC+ assessment values match, but {differences} imputed records differ in source sequence, visit, visit number, date, relative day and target-day distance. This exception is explicitly accepted as SAP-aligned, not exact-reference reproduction. The full clean-reference gate did not pass. Neither challenge seed was executed.",
        "Earlier exploratory findings":notes[3]+" Historical results are preserved separately from the reconstruction evidence and must not be presented as causal evidence for DRP-B.",
        "Limitations":notes[4]+" "+notes[5]+" Equal clean scores cannot identify the original imputation algorithm when candidate source observations differ. "+notes[2]+" Agreement on three datasets plus one scoped exception does not validate all populations, models or CSR tables.",
        "Conclusion":notes[7]+" The current work supports partial technical feasibility only. The required clean reconstruction and paired intervention evaluation remain incomplete.",
    }
    if dual:
        sections["Methods"]+=" The user-approved dual-track design separates reference replication from SAP-first sensitivity analysis. Existing ADSL, ADAE, ADTTE and SAP-selected CIBIC+ conventions are shared; the five BDS builders vary by track."
        sections["Results"]=sections["Results"].replace("The full clean-reference gate did not pass.","The reference-replication gate passed with the documented CIBIC+ exception; this does not certify SAP compliance.")
        sections["Limitations"]=notes[4]+" "+notes[5]+" Conventions were calibrated against the same targets subsequently compared, not independently validated. "+notes[2]+" No paired outcomes have been evaluated."
        sections["Conclusion"]=notes[7]+" Reference reconstruction is technically feasible under disclosed compatibility conventions; intervention efficacy and SAP-first robustness remain unestablished."
        cells=dual["baselineModelComparison"]
        sections["Results"]+=f" Clean cross-track comparisons covered {len(cells)} model/survival summary cells; {sum(r['Status']!='MATCH' for r in cells)} differed within the declared tolerances. These are baseline comparisons, not paired Outcome C."
    content="<!doctype html><html><meta charset='utf-8'><title>CDISCPILOT01 — current manuscript sections</title><style>body{font:17px/1.65 Georgia,serif;max-width:900px;margin:50px auto;padding:24px;color:#222}h1,h2{font-family:Arial,sans-serif}h2{margin-top:32px}.notice{border:1px solid #aaa;padding:16px}</style><h1>CDISCPILOT01: reconstruction validation</h1><p class='notice'>"+html.escape(headline)+"</p>"
    for title,text in sections.items():content+=f"<h2>{html.escape(title)}</h2><p>{html.escape(text)}</p>"
    (OUT/"Manuscript_Current_Sections.html").write_text(content+"</html>")
    pdf=pymupdf.open()
    lines=[]
    for title,text in sections.items():lines += [title.upper(),""]+textwrap.wrap(text,90)+["",""]
    for start in range(0,len(lines),49):
        page=pdf.new_page()
        page.insert_text((45,45),"\n".join(lines[start:start+49]),fontsize=10,fontname="helv")
    pdf.save(OUT/"Manuscript_Current_Sections.pdf");pdf.close()
    report=json.loads((OUT/"analysis.json").read_text())
    previous=set(report.get("currentValidationNotes",[]))
    prefixes=("CURRENT VALIDATION:","CIBIC+: SAP-selected","CIBIC+: PASSED","5 dataset rebuilds remain","0 rebuilds unimplemented;")
    for key in ("warnings","methodology"):
        report[key]=[n for n in report[key] if n not in previous and not n.startswith(prefixes)]
    report["currentValidationNotes"]=notes
    report["warnings"]=list(dict.fromkeys(notes+report["warnings"]))
    report["methodology"]=list(dict.fromkeys(notes+report["methodology"]))
    extra=["ADaM_Clean_Rebuild_Validation.xlsx","Paired_Intervention_Preflight.xlsx","clean_rebuild_validation.json","Manuscript_Current_Sections.html","Manuscript_Current_Sections.pdf","Output_Status_Manifest.csv","ADSL_Conservative_Reconstruction.csv","ADSL_Reference_Compatible_Reconstruction.csv","ADAE_Reconstruction.csv","ADTTE_Reconstruction.csv","ADQSCIBC_Reconstruction.csv"]
    extra += [p.name for p in OUT.glob("*_Candidate_Reconstruction.csv")]
    extra += [p.name for p in OUT.glob("*_Experimental_Reference.csv")]
    extra += ["ADaM_Reference_Compatibility_Experiments.xlsx","reference_compatibility_experiments.json","dual_track_validation.json"]
    paired=OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx"
    if paired.exists():extra.append(paired.name)
    downloads={d["name"]:d for d in report["downloads"]}
    for name in extra:downloads[name]={"name":name,"url":"/api/analysis/files/"+name,"description":"Current validation evidence — paired challenges not executed"}
    for name in downloads:
        if "Candidate" in name:downloads[name]["description"]="Unvalidated candidate reconstruction — do not use as reference or paired results"
        if name=="CDISCPILOT01_Paired_Intervention_Results.xlsx":
            downloads[name]["description"]="Dual-track clean audit and model comparisons — paired outcomes have not been evaluated"
        if "Experimental_Reference" in name:
            downloads[name]["description"]="Matching reference-compatible reconstruction; target-calibrated, not SAP certification or paired evidence"
        if name in ("clean_rebuild_validation.json","ADaM_Clean_Rebuild_Validation.xlsx"):
            downloads[name]["description"]="SAP-first reference comparison audit; reference-replication gate is reported separately"
    for d in downloads.values():
        if d["name"] in ["CDISCPILOT01_Final_Verified_Results.xlsx","Gate2_Before_After_Audit.xlsx","Manuscript_Results_Figure.png"]:
            d["description"]="Earlier exploratory results with current validation caveats; not paired intervention evidence"
    report["downloads"]=list(downloads.values())
    (OUT/"analysis.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(headline)

if __name__=="__main__":
    refresh_outputs()
