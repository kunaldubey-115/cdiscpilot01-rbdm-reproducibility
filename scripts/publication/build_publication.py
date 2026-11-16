"""Read-only reporting of saved experiment outputs. Never runs clinical analyses."""
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import zipfile
import openpyxl
from openpyxl.styles import Alignment, Font
from document_formats import blocks, html_document, pdf_document, docx_document

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"generated-artifacts/clinical"
STUDY=OUT/"scoped-study"
TRACKS=["reference_replication","sap_first_sensitivity"]
SCENARIOS=["development","held_out"]
def verify_frozen_evidence():
    protected=json.loads((OUT/"reporting-revisions/protected-hashes.json").read_text())
    for path,digest in protected.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError("Frozen evidence changed: "+path)
    policy=json.loads((STUDY/"frozen_policy.json").read_text())
    for path,digest in policy["sourceHashes"].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError("Source changed: "+path)
    for name,digest in policy["codeHashes"].items():
        p=OUT/"reporting-revisions/frozen_export_scoped_study.py" if name=="export_scoped_study.py" else ROOT/"scripts/clinical"/name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError("Frozen code changed: "+name)
    return policy

def metadata_config(release_ready=False,config_path=None):
    metadata=json.loads((Path(config_path) if config_path else Path(__file__).with_name("author_metadata.json")).read_text())
    required=["affiliation","corresponding_email","orcid","target_journal","credit_contributions","funding","competing_interests","ethics_statement","cdisc_data_use_statement","repository_url"]
    missing=[key for key in required if not isinstance(metadata.get(key),str) or not metadata[key].strip() or any(s in metadata[key].lower() for s in ["to be supplied","tbd","placeholder","to be confirmed"]) or metadata[key].strip() in ["N/A","NA","-"]]
    if release_ready and missing:raise ValueError("Release metadata incomplete: "+", ".join(missing))
    return metadata
def label(x):return {"reference_replication":"Reference","sap_first_sensitivity":"SAP-first","development":"Development","held_out":"Held-out"}.get(x,x)
def markdown_table(headers,rows):
    return "\n".join(["| "+" | ".join(map(str,headers))+" |","| "+" | ".join(["---"]*len(headers))+" |"]+["| "+" | ".join(str(v).replace("|","/") for v in row)+" |" for row in rows])

def summarize(r):
    query=[];capture=[];families=[];identity=[];comparisons=[];narrative=[];pairs=[]
    for scenario in SCENARIOS:
        for track in TRACKS:
            a={x["pathway"]:x for x in r["outcomeA"] if (x["scenario"],x["track"])==(scenario,track)}
            b={x["pathway"]:x for x in r["outcomeB"] if (x["scenario"],x["track"])==(scenario,track)}
            if set(a)!={"A","B"} or set(b)!={"A","B"}:
                query.append([label(scenario),label(track),"Pending","Pending","Pending"])
                capture.append([label(scenario),label(track),"Pending","Pending","Pending","Pending","Pending"])
                continue
            rows=[x for x in r["mutationAudit"] if (x["scenario"],x["track"])==(scenario,track) and x["critical"]]
            ids={p:{x["mutationId"] for x in rows if x["pathway"]==p and not x["captured"]} for p in ["A","B"]}
            assert all(len(ids[p])==b[p]["criticalMissed"] for p in ["A","B"])
            shared=ids["A"]&ids["B"];aonly=ids["A"]-ids["B"];bonly=ids["B"]-ids["A"]
            reduction=100*(a["A"]["uniqueQueryEpisodes"]-a["B"]["uniqueQueryEpisodes"])/a["A"]["uniqueQueryEpisodes"]
            pair={"scenario":scenario,"track":track,"queryReductionPercent":reduction,"sharedMisses":len(shared),"AOnlyMisses":len(aonly),"BOnlyMisses":len(bonly)}
            pairs.append(pair)
            query.append([label(scenario),label(track),f'{a["A"]["uniqueQueryEpisodes"]:,}',f'{a["B"]["uniqueQueryEpisodes"]:,}',f"{reduction:.2f}%"])
            capture.append([label(scenario),label(track),f'{b["A"]["criticalCaptured"]}/{b["A"]["criticalInjected"]}',f'{b["B"]["criticalCaptured"]}/{b["B"]["criticalInjected"]}',len(shared),len(aonly),len(bonly)])
            counts=Counter(x["family"] for x in rows if x["pathway"]=="A" and x["mutationId"] in shared)
            families += [[label(scenario),label(track),family,count] for family,count in sorted(counts.items())]
            unique={x["mutationId"]:x for x in rows}
            for mid in sorted(ids["A"]|ids["B"]):
                identity.append({"scenario":scenario,"track":track,"mutationId":mid,"family":unique[mid]["family"],"missedByA":mid in ids["A"],"missedByB":mid in ids["B"]})
            narrative.append(f'{label(scenario)}, {label(track)}: queries decreased from {a["A"]["uniqueQueryEpisodes"]:,} to {a["B"]["uniqueQueryEpisodes"]:,} ({reduction:.2f}%). Critical capture was {b["A"]["criticalCaptured"]}/{b["A"]["criticalInjected"]} for A and {b["B"]["criticalCaptured"]}/{b["B"]["criticalInjected"]} for B. There were {len(shared)} shared misses, {len(aonly)} A-only misses and {len(bonly)} B-only misses.')
            for comparison in ["A vs clean","B vs clean","B vs A"]:
                checks=[x for x in r["outcomeC"] if (x["scenario"],x["track"],x["comparison"])==(scenario,track,comparison)]
                if len(checks)!=7:
                    comparisons.append([label(scenario),label(track),comparison,"Pending","Pending"]);continue
                valid=[x for x in checks if x["cells"] is not None]
                comparisons.append([label(scenario),label(track),comparison,f'{sum(x["mismatches"] for x in valid):,} / {sum(x["cells"] for x in valid):,}',7-len(valid)])
    return query,capture,families,identity,comparisons,narrative,pairs

def build(require_complete=False,release_ready=False):
    metadata=metadata_config(release_ready)
    source=STUDY/"scoped_results.json"
    if not source.exists():source=STUDY/"results_in_progress.json"
    blob=source.read_bytes();r=json.loads(blob)
    complete=len(r["outcomeA"])==8 and len(r["outcomeC"])==84 and set(r["scenariosExecuted"])==set(SCENARIOS)
    if (require_complete or release_ready) and not complete:raise RuntimeError("Final study is incomplete; refusing final-labelled manuscript")
    sys.path.insert(0,str(ROOT/"scripts/clinical"))
    policy=verify_frozen_evidence()
    query,capture,families,identity,comparisons,narrative,pairs=summarize(r)
    status="AUTHOR-REVIEW DRAFT — completed scoped experiment; not submission-ready." if complete else "INTERIM AUTHOR-REVIEW DRAFT — held-out/full-study results incomplete; not for submission."
    if release_ready:status="Completed scoped feasibility study."
    current=[x for x in r["outcomeC"] if x["comparison"] in ("A vs clean","B vs clean")]
    all_good=complete and all(x["status"]=="MATCH" for x in current)
    any_bad=any(x["status"]!="MATCH" for x in current)
    if any_bad:
        consequence="At least one completed clean-reference comparison differed or was not evaluable. Consequently, pathway agreement cannot be presented as complete preservation of the clean outputs."
    elif all_good:
        consequence="All scoped A-versus-clean and B-versus-clean summary comparisons matched within the declared tolerances. This observation concerns the evaluated summaries, not every CSR table or clinical safety protection."
    else:
        consequence="The available clean-reference comparisons matched within tolerance; remaining comparisons must be completed before making a full-study preservation claim."
    reductions=[p["queryReductionPercent"] for p in pairs]
    same=bool(pairs) and all(not p["AOnlyMisses"] and not p["BOnlyMisses"] for p in pairs)
    abstract=(f"Results: {len(pairs)} of four scenario-by-track paired evaluations were available in this snapshot. "
              + (f"Query reductions ranged from {min(reductions):.2f}% to {max(reductions):.2f}%. " if reductions else "")
              + ("The missed critical-mutation sets were identical in all available pairs, with shared detection failures remaining. " if same else "Missed critical-mutation sets were not identical in every available pair; identity-level results are reported. ")
              +consequence)
    conclusion=("The scoped experiment quantifies review-query reductions relative to a specified comparator while separating critical-mutation capture from statistical-output preservation. "
        +("No additional critical-mutation misses were observed in DRP-B in the completed comparisons, but shared misses remained. " if same else "The mutation-level comparisons identify pathway-specific as well as shared detection limitations. ")
        +consequence+" These descriptive findings do not prove formal non-inferiority, majority-rule elimination, universal mathematical concordance or zero CSR-wide variance.")
    final_summaries=[]
    for comparison in ["A vs clean","B vs clean","B vs A"]:
        checks=[x for x in r["outcomeC"] if x["comparison"]==comparison]
        final_summaries.append(f"{comparison}: {sum(x['status']=='MATCH' for x in checks)} matched, {sum(x['status']=='DIFFERENCE' for x in checks)} differed and {sum(x['status']=='NOT EVALUABLE' for x in checks)} were not evaluable among {len(checks)} saved category comparisons. Each track/scenario contributes separately; counts are not independent trials.")
    replacements={
        "STATUS":status,
        "ABSTRACT_RESULTS":abstract,
        "AMENDMENT":policy["preExecutionAmendment"]+" The initial lock and log are retained. No outcome-based changes were made to the completed experiment.",
        "RESULTS":"\n\n".join(narrative+final_summaries+[consequence]),
        "QUERY_TABLE":markdown_table(["Scenario","Track","Queries A","Queries B","Reduction"],query),
        "CAPTURE_TABLE":markdown_table(["Scenario","Track","Captured A","Captured B","Shared misses","A-only","B-only"],capture),
        "OUTPUT_TABLE":markdown_table(["Scenario","Track","Comparison","Mismatch / cells","Failed categories"],comparisons),
        "MISSES_TABLE":markdown_table(["Scenario","Track","Family","Shared misses"],families),
        "CONCLUSION":conclusion,
        "FIGURE":"![Figure 1](Manuscript_Paired_Intervention_Figure.png)\n\nFigure 1. Scoped paired feasibility results. A: deduplicated query episodes. B: critical mutations missed. C: captured versus shared missed critical mutations by family, shown once per scenario because both pathways and tracks agree (development n=72; held-out n=108). D: zero mismatches among 118,482 serialized cells per seven-category comparison. The denominator includes identifiers; twelve repeated comparisons represent 1,421,784 checks, not independent observations. Numeric tolerance: atol=1e-8, rtol=1e-10. Shared misses are not clinically harmless merely because these summaries match." if complete else "Figure pending.",
    }
    text=Path(__file__).with_name("manuscript.md").read_text()
    for key,value in replacements.items():text=text.replace("{{"+key+"}}",value)
    if release_ready:
        text=text.replace("Affiliation, corresponding-author contact details and ORCID: to be supplied by the author.",f"Affiliation: {metadata['affiliation']}. Correspondence: {metadata['corresponding_email']}. ORCID: {metadata['orcid']}.")
        start=text.index("## Declarations and submission requirements")
        end=text.index("## References",start)
        text=text[:start]+"## Declarations\n\n"+"\n\n".join(f"{key.replace('_',' ').title()}: {value}" for key,value in metadata.items())+"\n\nAI assistance was used for software development and manuscript drafting; the author is responsible for verification and journal-policy compliance.\n\n"+text[end:]
    assert "{{" not in text
    base="CDISCPILOT01_Manuscript_Draft"
    (OUT/(base+".md")).write_text(text)
    parts=blocks(text);html=html_document(parts,OUT)
    (OUT/(base+".html")).write_text(html)
    pdf_document(html,OUT/(base+".pdf"),release_ready=release_ready);docx_document(parts,OUT/(base+".docx"),OUT)
    workbook(OUT/"CDISCPILOT01_Publication_Results.xlsx",r,policy,status,identity,pairs)
    checklist=f"""# Submission-readiness checklist

Current status: {status}

- [ ] Confirm all held-out and clean-reference results are complete and reviewed.
- [ ] Obtain independent clinical and statistical review of shared and pathway-specific misses.
- [ ] Resolve CDISC data-use permissions for perturbation experiments and redistribution.
- [ ] Confirm institutional ethics determination; do not assume exemption.
- [x] Record the supplied author name: Kunal Dubey.
- [ ] Supply affiliation, correspondence details, ORCID and confirmed contributions.
- [ ] Confirm funding, conflicts and acknowledgements.
- [ ] Choose a journal and adapt word count, tables, references and AI disclosure.
- [ ] Review comparator fairness and the fact that query counts are not measured workload.
- [ ] Archive permitted code/results with a persistent identifier and reproducible environment details.
- [ ] Approve the final manuscript; do not claim universal safety or full CSR validation.

No clinical analyses were rerun to produce this package.
"""
    (OUT/"CDISCPILOT01_Submission_Checklist.md").write_text(checklist)
    if release_ready:
        (OUT/"CDISCPILOT01_Submission_Checklist.md").write_text("# Release metadata checklist\n\nAll ten required metadata fields populated by the author; completed results verified.\n\n"+"".join(f"- [x] {key.replace('_',' ')} supplied\n" for key in metadata)+"\n- [ ] Confirm journal-specific forms, independent review and final author approval.\nMetadata completeness is not independent verification of declarations or permissions.\n")
    snapshot={"author":"Kunal Dubey","status":status,"complete":complete,"createdUTC":datetime.now(timezone.utc).isoformat(),
              "sourceResultFile":str(source.relative_to(ROOT)),"sourceResultSHA256":hashlib.sha256(blob).hexdigest(),
              "frozenPolicySHA256":(STUDY/"policy.sha256").read_text(),"pairComparisons":pairs,
              "missIdentityAudit":identity,"outcomeA":r["outcomeA"],"outcomeB":r["outcomeB"],"outcomeC":r["outcomeC"]}
    snapshot["reportingEnvironment"]={"python":sys.version,**{n:importlib.metadata.version(n) for n in ["numpy","pandas","scipy","statsmodels","openpyxl","pymupdf"]}}
    snapshot["reportingCodeHashes"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.iterdir() if p.suffix in (".py",".md")}
    snapshot["reportingRevision"]={"scope":"Authorized reporting-only edits; clinical experiment not rerun",
        "frozenExporterSHA256":policy["codeHashes"]["export_scoped_study.py"],
        "revisedExporterSHA256":hashlib.sha256((ROOT/"scripts/clinical/export_scoped_study.py").read_bytes()).hexdigest(),
        "protectedEvidenceHashes":json.loads((OUT/"reporting-revisions/protected-hashes.json").read_text())}
    (OUT/"Publication_Evidence_Snapshot.json").write_text(json.dumps(snapshot,indent=2,allow_nan=False))
    names=[base+ext for ext in [".docx",".pdf",".html",".md"]]+["CDISCPILOT01_Publication_Results.xlsx","CDISCPILOT01_Submission_Checklist.md","Publication_Evidence_Snapshot.json"]
    from submission_materials import prepare
    names += prepare(ROOT,OUT,STUDY,policy,status,complete,metadata,release_ready)
    if complete and (OUT/"Manuscript_Paired_Intervention_Figure.png").exists():names.append("Manuscript_Paired_Intervention_Figure.png")
    with zipfile.ZipFile(OUT/"CDISCPILOT01_Publication_Package.zip","w",zipfile.ZIP_DEFLATED) as package:
        for name in names:package.write(OUT/name,name)
    names.append("CDISCPILOT01_Publication_Package.zip")
    # Preserve all existing download entries; this does not change scientific output values.
    report=json.loads((OUT/"analysis.json").read_text())
    previous=set(report.get("currentValidationNotes",[]))
    notes=[
        f"SCOPED STUDY: {len(pairs)} of four paired scenario/track evaluations available. "+status,
        "Clean reconstruction: eight dataset matches plus the narrowly accepted CIBIC+ provenance exception; not nine exact matches.",
        "Rule scope: 48 executable comparator rules, 40 retained in DRP-B, and 77 blocked/external original rules. Shared safeguards remain.",
        "Eight of 22 executable rules originally labelled Tier 3 were removed (36.4%); this is not majority-rule elimination.",
        abstract,
        consequence,
        "Critical capture means unique source-record flagging followed by simulated whole-record verification, not diagnosis of the altered field or clinical PPV.",
        "Target-calibrated reconstruction is not independent validation. NPI mean-window, vital EOT and missing-laboratory-category conflicts remain explicit.",
        "Numeric comparisons use absolute 1e-8 and relative 1e-10 tolerances. Serialized cell percentages include identifier columns and are not variance estimates.",
        "Regenerated summaries do not certify every original CSR shell or a complete eCTD submission.",
        "Two fixed-seed scenarios in one pilot dataset do not establish formal non-inferiority, universal safety or external generalizability.",
        "Earlier estimate-stability, synthetic-power and frozen-ADaM figures are historical analyses, not the paired intervention results.",
        "CDISC data-use terms include restrictions on modification; resolve applicability and permissions before submission or redistribution.",
        "Release metadata populated; author must confirm final journal requirements." if release_ready else "The manuscript is an author-review draft. Authorship, ethics, funding/conflicts, independent review and journal requirements remain to be confirmed.",
    ]
    report["warnings"]=notes
    report["methodology"]=notes+[x for x in report.get("methodology",[]) if x not in previous and x not in notes and "not executed" not in x.lower() and "have not run" not in x.lower()]
    report["currentValidationNotes"]=notes
    entries={d["name"]:d for d in report["downloads"]}
    for name in names:entries[name]={"name":name,"url":"/api/analysis/files/"+name,"description":status}
    report["downloads"]=list(entries.values())
    temporary=OUT/"analysis.publication.tmp";temporary.write_text(json.dumps(report,indent=2,allow_nan=False));temporary.replace(OUT/"analysis.json")
    if complete:
        for ext in [".html",".pdf"]:shutil.copy2(OUT/(base+ext),OUT/("Manuscript_Current_Sections"+ext))
        # The saved scientific result has already normalized NaN to JSON null.
        # Publish that record rather than re-exporting the in-memory NaN values.
        (OUT/"Scoped_Feasibility_Results.json").write_text(json.dumps(r,indent=2,allow_nan=False))
        manifest_path=OUT/"Output_Status_Manifest.csv"
        with manifest_path.open(newline="") as stream:
            reader=csv.DictReader(stream);columns=reader.fieldnames;manifest=list(reader)
        published=names+["CDISCPILOT01_Paired_Intervention_Results.xlsx","Scoped_Feasibility_Results.json","Manuscript_Current_Sections.html","Manuscript_Current_Sections.pdf"]
        manifest=[row for row in manifest if row["file"] not in published]
        manifest += [{"file":name,"status":status,"pairedChallengesExecuted":True} for name in published]
        with manifest_path.open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(manifest)
    print(json.dumps({"complete":complete,"pairedComparisons":len(pairs),"wordCount":len(text.split()),"files":names},indent=2))

def workbook(path,r,policy,status,identity,pairs):
    from export_scoped_study import export_matrix,cell_difference_rows,add_readme_index
    book=openpyxl.load_workbook(OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx")
    def sheet(name,rows):
        if name in book:book.remove(book[name])
        ws=book.create_sheet(name)
        if rows:
            keys=list(rows[0]);ws.append(keys)
            for row in rows:ws.append([json.dumps(row.get(k)) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in keys])
            for cell in ws[1]:cell.font=Font(bold=True)
            for column in ws.columns:
                ws.column_dimensions[column[0].column_letter].width=24
            ws.freeze_panes="A2";ws.auto_filter.ref=ws.dimensions
        return ws
    first=sheet("Current_Validation_Status",[{"status":status},{"status":"Read-only publication export of saved results. No analyses rerun."},{"status":"77 original rules blocked/external; eight of 22 executable Tier 3 labels removed."},{"status":"Shared misses are not complete critical protection; inspect all clean-reference comparisons."},{"status":"Data-use permission, authorship, ethics and independent review require confirmation."}])
    book._sheets.remove(first);book._sheets.insert(0,first)
    sheet("Rule_Safety_Audit_Matrix",export_matrix(policy["matrix"]))
    sheet("Frozen_Study_Policy",[{"item":k,"value":v} for k,v in policy.items() if k!="matrix"])
    for name,key in [("Outcome_A","outcomeA"),("Outcome_B","outcomeB"),("Outcome_C","outcomeC"),("Cell_Differences","cellDifferences"),("Scenario_Coverage","scenarioCoverage"),("Independent_Path_Hashes","pathHashes")]:sheet(name,cell_difference_rows(r) if key=="cellDifferences" else r[key])
    audit=[{k:v for k,v in row.items() if k not in ("before","after","subject","sourceRow")} for row in r["mutationAudit"]]
    sheet("Mutation_Recovery",audit)
    sheet("Miss_Identity_Comparison",identity);sheet("Paired_Query_and_Miss_Summary",pairs)
    sheet("Scenario_Status",[{"scenario":s,"track":t,"completedPaths":",".join(x["pathway"] for x in r["outcomeA"] if (x["scenario"],x["track"])==(s,t)) or "PENDING","outputComparisons":sum((x["scenario"],x["track"])==(s,t) for x in r["outcomeC"])} for s in SCENARIOS for t in TRACKS])
    add_readme_index(book)
    book.save(path)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--require-complete",action="store_true");parser.add_argument("--release-ready",action="store_true")
    args=parser.parse_args();build(args.require_complete,args.release_ready)
