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

def export(result):
    from scoped_policy import load_policy
    load_policy()
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
    sheet("Rule_Safety_Audit_Matrix",result["policy"]["matrix"])
    sheet("Frozen_Study_Policy",[{"item":k,"value":json.dumps(v) if isinstance(v,(dict,list)) else v}
        for k,v in result["policy"].items() if k not in ("matrix","codeHashes","sourceHashes","metadataIndependence")])
    sheet("Frozen_Code_Hashes",[{"file":k,"SHA256":v} for k,v in result["policy"]["codeHashes"].items()])
    sheet("Frozen_Source_Hashes",[{"file":k,"SHA256":v} for k,v in result["policy"]["sourceHashes"].items()])
    sheet("Metadata_Independence",result["policy"]["metadataIndependence"])
    sheet("Scenario_Status",[{"scenario":s,"seed":result["policy"]["seeds"][s],"status":"EXECUTED — SCOPED"} for s in result["scenariosExecuted"]])
    for tab,key in [("Outcome_A","outcomeA"),("Outcome_B","outcomeB"),("Outcome_C","outcomeC"),
                    ("Mutation_Recovery","mutationAudit"),("Cell_Differences","cellDifferences"),
                    ("Scenario_Coverage","scenarioCoverage"),("Independent_Path_Hashes","pathHashes")]:
        sheet(tab,result[key])
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
    labels=[];query={"A":[],"B":[]};miss={"A":[],"B":[]};rate={"A":[],"B":[]}
    for scenario in ["development","held_out"]:
        for track in ["reference_replication","sap_first_sensitivity"]:
            labels.append(("Dev" if scenario=="development" else "Held-out")+"\n"+("Reference" if track.startswith("reference") else "SAP-first"))
            for path in ["A","B"]:
                row=next(r for r in result["outcomeA"] if (r["scenario"],r["track"],r["pathway"])==(scenario,track,path))
                query[path].append(row["uniqueQueryEpisodes"])
                row=next(r for r in result["outcomeB"] if (r["scenario"],r["track"],r["pathway"])==(scenario,track,path))
                miss[path].append(row["criticalMissed"])
                checks=[r for r in result["outcomeC"] if (r["scenario"],r["track"],r["comparison"])==(scenario,track,path+" vs clean")]
                rate[path].append(None if any(r["cells"] is None for r in checks) else 100*sum(r["mismatches"] for r in checks)/sum(r["cells"] for r in checks))
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10})
    fig,axes=plt.subplots(2,2,figsize=(14,10))
    for axis,title,values,ylabel in [(axes[0,0],"A. Deduplicated review episodes",query,"Episodes"),
                                   (axes[0,1],"B. Critical mutations missed",miss,"Mutations"),
                                   (axes[1,0],"C. Regenerated summary mismatch vs clean",rate,"Compared cells (%)")]:
        for j,path in enumerate(["A","B"]):
            y=np.array([np.nan if v is None else v for v in values[path]])
            bars=axis.bar(np.arange(4)+(j-.5)*.36,y,.36,label="DRP-"+path,color=["#1F74AD","#61A9BD"][j])
            axis.bar_label(bars,labels=["Not evaluable" if v is None else (f"{v:.4f}" if values is rate else f"{v:,}") for v in values[path]],fontsize=8,padding=3)
        axis.set_xticks(np.arange(4),labels);axis.set_ylabel(ylabel);axis.set_title(title,loc="left",fontweight="bold")
        axis.set_ylim(bottom=0);axis.margins(y=.2);axis.legend(frameon=False);axis.spines[["top","right"]].set_visible(False)
    axes[1,1].axis("off")
    axes[1,1].text(0,1,"D. Scope and interpretation",va="top",weight="bold",fontsize=12)
    axes[1,1].text(0,.87,"48 complete comparator rules; 40 in DRP-B.\n77 original rules remain blocked/external.\nShared structural and partial safety safeguards.\n\nTwo fixed seeds; disjoint perturbed subjects.\nTracks are not pooled as independent trials.\nCapture means the mutated record was flagged.\n\nPanel C audits regenerated summaries—not\ncomplete CSR shells. A/B agreement alone does\nnot show that either pathway preserved clean data.",va="top",linespacing=1.65)
    fig.suptitle("CDISCPILOT01 — scoped paired feasibility study",fontsize=17,fontweight="bold")
    fig.text(.06,.025,"Source: locked source-level simulations. Numeric tolerance: absolute 1e-8, relative 1e-10.\nDescriptive results from one public synthetic study; no universal clinical-safety or CSR-concordance claim.",fontsize=10)
    fig.tight_layout(rect=(0,.075,1,.95))
    fig.savefig(OUT/"Manuscript_Paired_Intervention_Figure.png",dpi=220);plt.close(fig)

if __name__=="__main__":
    export(json.loads((OUT/"scoped-study/scoped_results.json").read_text()))
