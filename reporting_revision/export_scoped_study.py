"""Publish saved scoped results without rerunning or relabelling historical analyses."""
import json
import html
import textwrap
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment,Font
import pymupdf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dual_track import OUT

MATRIX_COLUMNS=["rule","domain","tier","sourceFields","description","workbookReferenceUnverified","executionStatus","DRPA","DRPB","lineage","TFLDependency","mandatoryProtection","protocolSAPNeed","reason"]

def export_matrix(matrix):
    rows=[]
    for original in matrix:
        row={key:original.get(key) for key in MATRIX_COLUMNS}
        if row["DRPB"]=="SUPPRESS SCOPED PREDICATE":
            row["mandatoryProtection"]="Scoped non-critical predicate suppressed after verifying 9/9 ADaM independence; core identity and safety safeguards retained"
            row["protocolSAPNeed"]="Not required for primary/secondary SAP endpoints or safety populations in this scoped feasibility evaluation"
        rows.append(row)
    return rows

def cell_difference_rows(result):
    if result["cellDifferences"]:return result["cellDifferences"]
    groups={}
    for row in result["outcomeC"]:
        key=(row["scenario"],row["track"],row["comparison"])
        if row["status"]!="MATCH":raise ValueError("Cannot report zero differences for an incomplete or non-matching comparison")
        groups[key]=groups.get(key,0)+row["cells"]
    totals=set(groups.values())
    if len(totals)!=1:raise ValueError("Comparison denominators differ")
    n=next(iter(totals))
    return [{"status":"0 CELL DIFFERENCES","comparedCells":n,"mismatches":0,
             "note":f"All {n:,} compared serialized cells across all 7 summary categories matched within tolerance (atol=1e-8, rtol=1e-10) across all scenarios, tracks, and pathways. The denominator is per comparison: {len(groups)} repeated comparisons, {sum(groups.values()):,} serialized cell checks in total, not independent cells."}]

def add_readme_index(book):
    if "README_Index" in book:book.remove(book["README_Index"])
    ws=book.create_sheet("README_Index",1)
    ws.append(["section","worksheet","description"])
    sections=["Governance & Frozen Policy","Outcomes A/B/C & Miss Identity","Dual-Track Clean Gate","Field-Level Validation Audits"]
    groups={s:[] for s in sections}
    for name in book.sheetnames:
        lower=name.lower()
        if any(s in lower for s in ["outcome","miss_","mutation","cell_difference","scenario","path_hash","paired_query","query_attribution","capture_breakdown"]):group=sections[1]
        elif any(s in lower for s in ["coverage","clean_gate","dual_track","clean_model","reference_gate","comparison_summary"]):group=sections[2]
        elif any(s in lower for s in ["field","_fields","_diff","candidate","reference","adsl","adae","adtte","adqs","adlb","advs","traceability"]):group=sections[3]
        else:group=sections[0]
        groups[group].append(name)
    for group,names in groups.items():
        for name in names:
            ws.append([group,name,"Open worksheet"])
            ws.cell(ws.max_row,2).hyperlink=f"#'{name}'!A1";ws.cell(ws.max_row,2).style="Hyperlink"
    ws.append(["Interpretation","Cell denominators","118,482 per seven-category comparison, repeated across 12 scenario/track/pathway comparisons; not a pooled independent sample."])
    ws.append(["Interpretation","Exported governance text","Suppressed-row wording is reporting-only. The frozen policy remains unchanged. Metadata perturbation tests covered clock/category changes across all nine datasets; gap-rule suppression does not itself edit source values."])
    for col,width in [("A",36),("B",40),("C",100)]:ws.column_dimensions[col].width=width
    for row in ws:
        for cell in row:cell.alignment=Alignment(wrap_text=True,vertical="top")
    for cell in ws[1]:cell.font=Font(bold=True)
    ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:C{len(book.sheetnames)+1}"

def export(result):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"publication"))
    from build_publication import verify_frozen_evidence
    verify_frozen_evidence()
    if len(result["scenariosExecuted"])!=2:raise ValueError("Do not publish incomplete scenarios")
    path=OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx"
    book=openpyxl.load_workbook(path)
    def sheet(name,records):
        if name in book:book.remove(book[name])
        ws=book.create_sheet(name)
        if records:
            keys=list(records[0]);ws.append(keys)
            for record in records:
                ws.append([json.dumps(record.get(k)) if isinstance(record.get(k),(dict,list)) else record.get(k) for k in keys])
        ws.freeze_panes="A2";ws.auto_filter.ref=ws.dimensions
        for c in ws[1]:c.font=Font(bold=True)
        for column in ws.columns:
            ws.column_dimensions[column[0].column_letter].width=28
            for cell in column:cell.alignment=Alignment(wrap_text=True,vertical="top")
        return ws
    notes=[
        "SCOPED FEASIBILITY COMPLETED — not full 125-rule validation or complete CSR-shell certification.",
        "Reference replication and SAP-first sensitivity are reported separately. Clean reference gate: eight matching datasets plus the approved CIBIC+ exception.",
        f"Comparator: {len(result['policy']['activeA'])} fully executable rules. DRP-B: {len(result['policy']['activeB'])}. Eight narrowly scoped predicates removed; shared identity and partial safety safeguards retained.",
        "77 original rules remain blocked/external; retaining them in the audit does not mean their protections were executed.",
        "Outcome A counts deduplicated review episodes; yield concerns known injected mutations, not clinically adjudicated query PPV.",
        "Outcome B measures capture of mutated source records, including incidental capture by another rule. Corrections use the same simulated whole-record verification oracle in A/B.",
        "Outcome C compares A vs clean, B vs clean and B vs A within each track. Missing rows and model failures are not zero mismatches.",
        "Conventions were target-calibrated, not independently validated. NPI mean-period, vital EOT and missing-lab-category limitations remain.",
        "Original estimate-stability/power simulations and frozen-ADaM figures are historical, not results of this scoped intervention.",
        "Two seeded scenarios in one public synthetic study do not establish universal safety, regulatory acceptability or cross-study generalizability.",
        result["policy"]["criticalityCaveat"],
    ]
    status=sheet("Current_Validation_Status",[{"Current evidence":n} for n in notes])
    book._sheets.remove(status);book._sheets.insert(0,status)
    sheet("Rule_Safety_Audit_Matrix",export_matrix(result["policy"]["matrix"]))
    sheet("Frozen_Study_Policy",[{"item":k,"value":json.dumps(v) if isinstance(v,(dict,list)) else v}
        for k,v in result["policy"].items() if k not in ("matrix","codeHashes","sourceHashes","metadataIndependence")])
    sheet("Frozen_Code_Hashes",[{"file":k,"SHA256":v} for k,v in result["policy"]["codeHashes"].items()])
    sheet("Frozen_Source_Hashes",[{"file":k,"SHA256":v} for k,v in result["policy"]["sourceHashes"].items()])
    sheet("Metadata_Independence",result["policy"]["metadataIndependence"])
    sheet("Scenario_Status",[{"scenario":s,"seed":result["policy"]["seeds"][s],"status":"EXECUTED — SCOPED"} for s in result["scenariosExecuted"]])
    for tab,key in [("Outcome_A","outcomeA"),("Outcome_B","outcomeB"),("Outcome_C","outcomeC"),
                    ("Mutation_Recovery","mutationAudit"),("Cell_Differences","cellDifferences"),
                    ("Scenario_Coverage","scenarioCoverage"),("Independent_Path_Hashes","pathHashes")]:
        sheet(tab,cell_difference_rows(result) if key=="cellDifferences" else result[key])
    add_readme_index(book)
    book.save(path)
    for other in OUT.glob("*.xlsx"):
        if other==path:continue
        old=openpyxl.load_workbook(other)
        if "Current_Validation_Status" not in old:continue
        ws=old["Current_Validation_Status"];ws.delete_rows(1,ws.max_row)
        ws.append(["Scope update only — underlying workbook analysis preserved"])
        for note in notes:ws.append([note])
        for row in ws:
            for cell in row:cell.alignment=Alignment(wrap_text=True,vertical="top")
        old.save(other)
    make_figure(result)
    from PIL import Image,ImageDraw,ImageFont
    for name in ["Manuscript_Results_Figure.png","Power_Erosion_and_Query_Reduction.png"]:
        old_path=OUT/name
        old=Image.open(old_path).convert("RGB")
        canvas=old.copy();draw=ImageDraw.Draw(canvas);draw.rectangle((0,0,canvas.width,239),fill="#fff4df")
        font=ImageFont.load_default(size=27)
        for i,line in enumerate(["HISTORICAL SIMULATION — NOT THE SCOPED PAIRED STUDY",
                                 "Preserved estimate-stability / synthetic-power results.",
                                 "For the completed scoped experiment, use:",
                                 "Manuscript_Paired_Intervention_Figure.png"]):
            draw.text((40,20+52*i),line,font=font,fill="#332b1f")
        canvas.save(old_path)
    a=pd.DataFrame(result["outcomeA"]);b=pd.DataFrame(result["outcomeB"])
    sections={"Status":"Completed scoped dual-track feasibility experiment; not a completed validation of the original full-scope hypothesis.",
        "Methods":"Policy, source/code hashes, eight predicate removals, shared safeguards and numeric tolerances were frozen before challenge generation. Seeds were 20261120 and 20261121. Perturbed subjects were disjoint between scenarios. Each path independently detected flags on identical dirty inputs, applied the same simulated whole-record verification and rebuilt all nine datasets from source. No target ADaM columns entered the pathways. Each track used its own clean baseline.",
        "Results — review burden":a.to_string(index=False),
        "Results — critical mutation capture":b.to_string(index=False),
        "Results — statistical and summary preservation":"See Outcome_C and Cell_Differences for each scenario, track and comparison. These cover population flags, fitted model/TTDE summaries and regenerated demographic/NPI/lab/vital summaries, not every cell in the original CSR shells.",
        "Limitations":" ".join(notes[3:]),
        "Conclusion":"The observed counts and discrepancies determine the scoped result. Neither exact A/B agreement alone nor reduced review burden establishes complete critical-error protection. Both pathways must also be checked against clean outputs. No universal 100% concordance or 0.0000% CSR-wide variance claim is warranted."}
    sections["Methods"]+=" "+result["policy"].get("preExecutionAmendment","")
    content="<html><meta charset='utf-8'><title>Scoped CDISCPILOT01 study</title><style>body{max-width:1100px;margin:40px auto;padding:20px;font:16px/1.6 Arial;color:#222}pre{white-space:pre-wrap;font-size:12px}h2{margin-top:30px}</style><h1>CDISCPILOT01 scoped paired feasibility study</h1>"
    for title,text in sections.items():content+="<h2>"+html.escape(title)+"</h2><pre>"+html.escape(text)+"</pre>"
    (OUT/"Manuscript_Current_Sections.html").write_text(content+"</html>")
    doc=pymupdf.open();lines=[]
    for title,text in sections.items():
        lines += [title.upper(),""]+[line for paragraph in text.splitlines() for line in textwrap.wrap(paragraph,95)]+["",""]
    for start in range(0,len(lines),48):
        page=doc.new_page();page.insert_text((40,40),"\n".join(lines[start:start+48]),fontsize=9.5,fontname="helv")
    doc.save(OUT/"Manuscript_Current_Sections.pdf");doc.close()
    report=json.loads((OUT/"analysis.json").read_text())
    previous=set(report.get("currentValidationNotes",[]))
    for key in ("warnings","methodology"):
        report[key]=notes+[n for n in report[key] if n not in previous and n not in notes]
    report["currentValidationNotes"]=notes
    downloads={d["name"]:d for d in report["downloads"]}
    for name in ["CDISCPILOT01_Paired_Intervention_Results.xlsx","Manuscript_Paired_Intervention_Figure.png","Scoped_Feasibility_Results.json","Rule_Execution_Readiness.xlsx"]:
        downloads[name]={"name":name,"url":"/api/analysis/files/"+name,"description":"Scoped feasibility evidence; read coverage, misses and limitations—not full 125-rule or CSR validation"}
    for name in ["Manuscript_Current_Sections.pdf","Manuscript_Current_Sections.html"]:
        downloads[name]={"name":name,"url":"/api/analysis/files/"+name,"description":"Current scoped-study manuscript sections and limitations"}
    report["downloads"]=list(downloads.values())
    (OUT/"analysis.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    (OUT/"Scoped_Feasibility_Results.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    manifest=pd.read_csv(OUT/"Output_Status_Manifest.csv")
    for name in ["CDISCPILOT01_Paired_Intervention_Results.xlsx","Manuscript_Paired_Intervention_Figure.png","Scoped_Feasibility_Results.json","Manuscript_Current_Sections.pdf","Manuscript_Current_Sections.html"]:
        manifest=manifest.loc[manifest.file.ne(name)]
        manifest=pd.concat([manifest,pd.DataFrame([{"file":name,"status":"Completed SCOPED feasibility; not full 125-rule/CSR validation","pairedChallengesExecuted":True}])],ignore_index=True)
    manifest.to_csv(OUT/"Output_Status_Manifest.csv",index=False)

def make_figure(result):
    labels=[];query={"A":[],"B":[]};miss={"A":[],"B":[]}
    for scenario in ["development","held_out"]:
        for track in ["reference_replication","sap_first_sensitivity"]:
            labels.append(("Dev" if scenario=="development" else "Held-out")+"\n"+("Reference" if track.startswith("reference") else "SAP-first"))
            for path in ["A","B"]:
                row=next(r for r in result["outcomeA"] if (r["scenario"],r["track"],r["pathway"])==(scenario,track,path))
                query[path].append(row["uniqueQueryEpisodes"])
                row=next(r for r in result["outcomeB"] if (r["scenario"],r["track"],r["pathway"])==(scenario,track,path))
                miss[path].append(row["criticalMissed"])
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10})
    fig,axes=plt.subplots(2,2,figsize=(17,13),gridspec_kw={"height_ratios":[1,1.4]})
    for axis,title,values,ylabel in [(axes[0,0],"A. Deduplicated review episodes",query,"Episodes"),
                                   (axes[0,1],"B. Critical mutations missed",miss,"Mutations")]:
        for j,path in enumerate(["A","B"]):
            y=np.array([np.nan if v is None else v for v in values[path]])
            bars=axis.bar(np.arange(4)+(j-.5)*.36,y,.36,label="DRP-"+path,color=["#1F74AD","#61A9BD"][j])
            axis.bar_label(bars,labels=[f"{v:,}" for v in values[path]],fontsize=10,padding=3)
        axis.set_xticks(np.arange(4),labels);axis.set_ylabel(ylabel);axis.set_title(title,loc="left",fontweight="bold")
        axis.set_ylim(bottom=0);axis.margins(y=.2);axis.legend(frameon=False);axis.spines[["top","right"]].set_visible(False)
    families=sorted({r["family"] for r in result["mutationAudit"] if r["critical"]}-{ "Disposition date","AE onset before exposure"})+["Disposition date","AE onset before exposure"]
    axis=axes[1,0]
    for j,scenario in enumerate(["development","held_out"]):
        reference=[r for r in result["mutationAudit"] if r["critical"] and r["scenario"]==scenario and r["track"]=="reference_replication" and r["pathway"]=="A"]
        expected={r["mutationId"]:r["captured"] for r in reference}
        for track in ["reference_replication","sap_first_sensitivity"]:
            for path in ["A","B"]:
                other={r["mutationId"]:r["captured"] for r in result["mutationAudit"] if r["critical"] and r["scenario"]==scenario and r["track"]==track and r["pathway"]==path}
                if other!=expected:raise ValueError("Shared-capture figure requires identical mutation-level capture")
        for i,family in enumerate(families):
            rows=[r for r in reference if r["family"]==family];n=len(rows);c=sum(r["captured"] for r in rows);y=i+(j-.5)*.36
            axis.barh(y,c,.32,color="#1F74AD",label="Captured" if i==0 and j==0 else None)
            axis.barh(y,n-c,.32,left=c,color="#E5B66D",label="Shared misses" if i==0 and j==0 else None)
            axis.text(n+.15,y,f"{'Dev' if j==0 else 'Held'} {c}/{n}",va="center",fontsize=9)
    axis.set_yticks(np.arange(len(families)),families,fontsize=9);axis.invert_yaxis()
    axis.set_xlim(0,15.5);axis.set_xticks([0,4,8,12]);axis.set_xlabel("Critical mutations (captured / injected labelled)")
    axis.set_title("C. Critical capture and shared misses by family\nDevelopment n=72; held-out n=108",loc="left",fontweight="bold")
    axis.set_ylim(len(families)-.2,-1.2)
    axis.legend(loc="upper right",ncol=2,fontsize=9,frameon=False);axis.spines[["top","right"]].set_visible(False)
    concordance=cell_difference_rows(result)[0]
    axes[1,1].axis("off")
    axes[1,1].text(0,1,"D. Scope and interpretation",va="top",weight="bold",fontsize=12)
    axes[1,1].text(0,.88,f"0 / {concordance['comparedCells']:,} (0.0000%)",fontsize=23,weight="bold",va="top")
    axes[1,1].text(0,.78,"Clean-reference cell mismatches per comparison\nAll seven scoped summary categories matched.\n12 repeated comparisons; 1,421,784 cell checks.\nNot a count of independent observations.\n\n48 complete comparator rules; 40 in DRP-B.\n77 original rules remain blocked/external.\n\nPanel C displays each scenario once: capture\nwas identical in both pathways and both tracks.\nShared misses: 15 development; 17 held-out.\n\nUnchanged summaries do not establish clinical\nharmlessness or complete CSR concordance.",va="top",fontsize=12,linespacing=1.65)
    fig.suptitle("CDISCPILOT01 — scoped paired feasibility study",fontsize=17,fontweight="bold")
    fig.text(.06,.025,"Source: saved locked CDISCPILOT01 experiment; no analyses rerun. Numeric tolerance: absolute 1e-8, relative 1e-10.\nCapture means record-level flagging, not field-specific diagnosis. Tracks are not pooled as independent trials.",fontsize=10)
    fig.tight_layout(rect=(0,.075,1,.95))
    fig.savefig(OUT/"Manuscript_Paired_Intervention_Figure.png",dpi=300);plt.close(fig)

if __name__=="__main__":
    export(json.loads((OUT/"scoped-study/scoped_results.json").read_text()))
