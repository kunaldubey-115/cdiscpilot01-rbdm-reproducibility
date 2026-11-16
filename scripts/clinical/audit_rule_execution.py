"""Audit clean rule execution and query identity before freezing interventions."""
import json
import pandas as pd
import openpyxl
from dual_track import DATA, OUT, SDTM, specifications, rebuild_track
from rebuild_adsl import rebuild_adsl
from rules import evaluate_rules

def main():
    sources={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
    sources["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
    rebuilt,_=rebuild_track(sources,specifications(),"reference_replication")
    sources.update(rebuilt)
    workbook=openpyxl.load_workbook(DATA.parents[2]/"scripts/clinical/input/template.xlsx",data_only=True)
    ledger=[]
    results=evaluate_rules(workbook,sources,ledger=ledger)
    from safety_components import evaluate_components
    components=evaluate_components(sources)
    component_counts=components.groupby(["component","status"]).size().rename("records").reset_index()
    counts=pd.Series([r["status"] for r in results]).value_counts().to_dict()
    summary={"scope":"Clean-input execution audit, not injected-error detection or clinical adjudication",
             "analysisTrack":"reference_replication",
             "derivedInputs":"Source-rebuilt ADaM supplied to dependent rules; no cached target ADaM columns used",
             "ruleStatuses":counts,"predicateFlags":len(ledger),
             "deduplicatedRecordOrSubjectEpisodes":len({r["episodeId"] for r in ledger}),
             "ambiguousOrSubjectFlags":sum(r["scope"]!="record" for r in ledger),
             "dispositionsFrozen":False,"pairedRunsExecuted":False}
    (OUT/"Rule_Execution_Ledger.json").write_text(json.dumps({"summary":summary,"rules":results,"ledger":ledger,"supportedComponentSummary":component_counts.to_dict("records")},indent=2))
    with pd.ExcelWriter(OUT/"Rule_Execution_Readiness.xlsx",engine="openpyxl") as writer:
        pd.DataFrame([{"item":k,"value":str(v)} for k,v in summary.items()]).to_excel(writer,sheet_name="Readiness",index=False)
        pd.DataFrame(results).to_excel(writer,sheet_name="All_125_Rules",index=False)
        pd.DataFrame([r for r in results if str(r["tier"]).startswith("Tier 1") and r["status"].startswith("blocked")]).to_excel(writer,sheet_name="Blocked_Critical_Rules",index=False)
        pd.DataFrame(ledger).to_excel(writer,sheet_name="Flag_Ledger",index=False)
        component_counts.to_excel(writer,sheet_name="Partial_Check_Summary",index=False)
        components.to_excel(writer,sheet_name="Partial_Check_Records",index=False)
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
