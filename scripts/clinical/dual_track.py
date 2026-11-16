"""Approved dual-track design. Build from SDTM; reference ADaM is audit-only."""
import json
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Font
from validate_rebuild import (DATA, OUT, TARGETS, SDTM, specifications, digest,
    compare_records, compare_bds, compare_cibic, all_targets_passed,
    cibic_convention_passed, cibic_exception_rows)
from rebuild_adsl import rebuild_adsl
from rebuild_adae import rebuild_adae
from rebuild_adtte import rebuild_adtte
from rebuild_cibic import rebuild_cibic
from rebuild_bds import rebuild_advs, rebuild_adlbc, rebuild_adlbh
from rebuild_questionnaires import rebuild_adqsadas, rebuild_adqsnpix

TRACKS=("reference_replication","sap_first_sensitivity")
POLICY={
    "design":"Dual-track study approved by user",
    "tracks":{
        "reference_replication":"Target-calibrated compatibility conventions; not proof of SAP compliance.",
        "sap_first_sensitivity":"SAP-first candidate interpretations; not certified SAP compliance or exact reference reproduction."
    },
    "shared":"Existing reference-compatible ADSL, ADAE, ADTTE and approved SAP-selected CIBIC+ remain unchanged in both tracks.",
    "comparison":"Compare A and B against that track's own clean rebuild. Report cross-track differences separately; never pool them.",
    "exception":"Only the documented 35-row / six-field CIBIC+ exception is accepted.",
    "tolerances":{"absolute":1e-8,"relative":1e-10},
    "seeds":{"development":20261120,"held_out":20261121},
    "challenge_policy":"No challenges until rule dispositions, correction logic, record-level flags and endpoint comparisons are ready and frozen.",
}

def rebuild_track(source,spec,track):
    if track not in TRACKS:raise ValueError("Unknown analysis track")
    mode="reference-compatible" if track==TRACKS[0] else "sap"
    frames={};proof={}
    frames["adsl"],proof["adsl"]=rebuild_adsl(source,spec["adsl"],mode="reference-compatible")
    frames["adae"],proof["adae"]=rebuild_adae(source,frames["adsl"],spec["adae"])
    frames["adtte"],proof["adtte"]=rebuild_adtte(frames["adsl"],frames["adae"],spec["adtte"])
    frames["adqscibc"],proof["adqscibc"]=rebuild_cibic(source,frames["adsl"],spec["adqscibc"])
    for name,builder in {"adqsadas":rebuild_adqsadas,"adqsnpix":rebuild_adqsnpix,
                         "adlbc":rebuild_adlbc,"adlbh":rebuild_adlbh,"advs":rebuild_advs}.items():
        frames[name],proof[name]=builder(source,frames["adsl"],spec[name],mode=mode)
    return frames,proof

def compare_dataset(name,actual,expected,proof):
    if name=="adqscibc":return compare_cibic(actual,expected,proof)
    if name=="adsl":return compare_records(actual,expected,proof,["USUBJID"])
    if name=="adae":return compare_records(actual,expected,proof,["USUBJID","AESEQ"])
    if name=="adtte":return compare_records(actual,expected,proof,["USUBJID","PARAMCD"])
    return compare_bds(actual,expected,proof,name)

def gate(frames,proof,targets):
    coverage=[];fields={}
    for name in TARGETS:
        rows=compare_dataset(name,frames[name],targets[name],proof[name]);fields[name]=rows
        matched=sum(row["status"]=="MATCH" for row in rows)
        row={"dataset":name.upper(),"targetRows":len(targets[name]),"rebuiltRows":len(frames[name]),
             "matchingFields":matched,"targetFields":len(targets[name].columns),
             "status":"PASSED" if matched==len(targets[name].columns) else "FAILED"}
        if name=="adqscibc" and cibic_convention_passed(rows) and len(cibic_exception_rows(frames[name],targets[name]))==35:
            row.update(status="PASSED (SAP-Aligned Convention)",conventionVerified=True)
        coverage.append(row)
    return {"passed":all_targets_passed(coverage),"coverage":coverage,"fields":fields}

def require_challenge_readiness(report):
    """A clean gate is necessary, but does not replace intervention prerequisites."""
    if not report["tracks"][TRACKS[0]]["passed"]:
        raise RuntimeError("Reference reconstruction gate has not passed")
    if not report["interventionReady"]:
        raise RuntimeError("Rule audit, record-level intervention and outcome prerequisites are not ready")

def main():
    hashes={str(p):digest(p) for p in DATA.rglob("*") if p.is_file() and p.suffix in (".xpt",".xml",".pdf",".sas")}
    source={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
    source["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
    spec=specifications()
    # Both source-only constructions finish before any target is loaded.
    built={track:rebuild_track(source,spec,track) for track in TRACKS}
    targets={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in TARGETS}
    reports={track:gate(*built[track],targets) for track in TRACKS}
    cross={name:compare_dataset(name,built[TRACKS[1]][0][name],built[TRACKS[0]][0][name],{})
           for name in TARGETS}
    from dual_track_models import compare_models
    models=compare_models(built[TRACKS[0]][0],built[TRACKS[1]][0])
    result={"policy":POLICY,"tracks":reports,"crossTrackFields":cross,"interventionReady":False,
            "pairedRunsExecuted":False,"remaining":["125-rule lineage/safety audit and frozen dispositions",
                "Record-level flag ledger and identical correction algorithm",
                "Complete track-specific model and table comparison runner"],
            "sourceHashes":hashes,"baselineModelComparison":models.to_dict("records")}
    assert all(digest(__import__("pathlib").Path(p))==h for p,h in hashes.items()),"Source cache changed"
    (OUT/"dual_track_validation.json").write_text(json.dumps(result,indent=2))
    if (OUT/"scoped-study/scoped_results.json").exists():
        print("Clean dual-track audit refreshed; locked scoped-study workbook preserved.")
        return
    from export_paired_status import main as export_status
    export_status()
    book=openpyxl.load_workbook(OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx")
    old=book["Current_Validation_Status"];book.remove(old)
    status=book.create_sheet("Current_Validation_Status",0)
    status.append(["DUAL-TRACK STUDY — CHALLENGES NOT EXECUTED","Clean reconstruction is not intervention evidence."])
    status.append(["Reference replication gate","PASSED WITH APPROVED CIBIC+ EXCEPTION" if reports[TRACKS[0]]["passed"] else "BLOCKED"])
    status.append(["SAP-first reference comparison","Separate sensitivity results; differences are not waived or labelled matches."])
    status.append(["Intervention status","BLOCKED — unfinished rule audit, flag/correction ledger and outcome runner."])
    status.append(["Decision","Reference replication and SAP-first sensitivity results will remain separate."])
    for track,label in [(TRACKS[0],"Reference_Gate"),(TRACKS[1],"SAP_First_Comparison")]:
        sheet=book.create_sheet(label)
        sheet.append(["Dataset","Status","Target records","Rebuilt records","Matching fields","Total fields"])
        for row in reports[track]["coverage"]:
            sheet.append([row[k] for k in ["dataset","status","targetRows","rebuiltRows","matchingFields","targetFields"]])
    sheet=book.create_sheet("Dual_Track_Policy");sheet.append(["Item","Policy"])
    for key,value in POLICY.items():sheet.append([key,json.dumps(value) if isinstance(value,dict) else value])
    sheet=book.create_sheet("Clean_Track_Model_Comparison")
    sheet.append(list(models.columns))
    for row in models.itertuples(index=False,name=None):sheet.append(list(row))
    sheet=book.create_sheet("Cross_Track_Differences");sheet.append(["Dataset","Field","Status","Records compared","Mismatches","Example"])
    for name,rows in cross.items():
        for row in rows:
            if row["status"]!="MATCH":sheet.append([name.upper(),row["variable"],row["status"],row["compared"],row["mismatches"],row.get("example","")])
    # Keep old comparison tabs explicitly identified rather than relabelling their contents.
    for name in ["ADQSADAS","ADQSNPIX","ADLBC","ADLBH","ADVS"]:
        book[name+"_Comparison"].title=name+"_SAP_Candidate"
    for track,prefix in [(TRACKS[0],"Ref"),(TRACKS[1],"SAP")]:
        for name,rows in reports[track]["fields"].items():
            sheet=book.create_sheet(prefix+"_"+name.upper()+"_Fields")
            sheet.append(["Field","Status","Records compared","Mismatches","Evidence","Example"])
            for row in rows:sheet.append([row.get(k) for k in ["variable","status","compared","mismatches","evidence","example"]])
    for row in book["Scenario_Status"].iter_rows(min_row=2):
        row[2].value="NOT GENERATED / NOT EXECUTED — intervention prerequisites unfinished"
    for sheet in book:
        if sheet.title in ("Protocol_SAP_Blueprint","CRF_Page_Domain_Annotations"):continue
        sheet.freeze_panes="A2"
        for cell in sheet[1]:cell.font=Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width=42
            for cell in col:cell.alignment=Alignment(wrap_text=True,vertical="top")
    book.save(OUT/"CDISCPILOT01_Paired_Intervention_Results.xlsx")
    print(json.dumps({track:{"passed":r["passed"],"coverage":r["coverage"]} for track,r in reports.items()},indent=2))

if __name__=="__main__":main()
