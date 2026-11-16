"""One locked development + held-out run. Never reuse target ADaM in pathways."""
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import openpyxl
from dual_track import DATA, OUT, SDTM, TRACKS, specifications, rebuild_track
from scoped_policy import ROOT, freeze, load_policy
from scoped_challenges import generate
from scoped_detection import detect, correct
from scoped_outcomes import summaries, compare_summary

def safe(value):
    if isinstance(value,dict):return {str(k):safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [safe(v) for v in value]
    if isinstance(value,np.generic):return safe(value.item())
    if isinstance(value,float) and not np.isfinite(value):return None
    return value

def save(path,value):
    path.write_text(json.dumps(safe(value),indent=2,allow_nan=False))

def frame_hashes(data):
    return {name:hashlib.sha256(pd.util.hash_pandas_object(frame,index=True).values.tobytes()).hexdigest() for name,frame in data.items()}

def main():
    directory=OUT/"scoped-study";directory.mkdir(exist_ok=True)
    if (directory/"run_started.json").exists():raise RuntimeError("Study already started. Do not rerun or tune against held-out results.")
    source={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
    source["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
    freeze(source)
    policy=load_policy()
    save(directory/"run_started.json",{"policySha256":(directory/"policy.sha256").read_text(),"scope":policy["design"]})
    spec=specifications();template=openpyxl.load_workbook(ROOT/"scripts/clinical/input/template.xlsx",data_only=True)
    clean={}
    for track in TRACKS:
        clean[track]=summaries(rebuild_track(source,spec,track)[0])
    output={"policy":policy,"outcomeA":[],"outcomeB":[],"outcomeC":[],"cellDifferences":[],
            "mutationAudit":[],"scenarioCoverage":[],"pathHashes":[],"scenariosExecuted":[],
            "status":"RUNNING","limitations":[policy[k] for k in ["endpointScope","criticalDetection","queryYield","criticalityCaveat"]],
            "sharedGuardNote":"Supported partial checks run identically in A/B but remain separate from the 48 complete rule count."}
    seen=set()
    for scenario,seed in policy["seeds"].items():
        held=scenario=="held_out"
        load_policy()
        dirty,truth,coverage=generate(source,seed,held)
        subjects={r["subject"] for r in truth}
        if seen & subjects:raise RuntimeError("Development/held-out perturbation subject overlap")
        seen|=subjects
        save(directory/(scenario+"_truth.json"),truth)
        save(directory/(scenario+"_input_hashes.json"),frame_hashes(dirty))
        output["scenarioCoverage"].extend([{"scenario":scenario,**r} for r in coverage])
        for track in TRACKS:
            paths={}
            for pathway in ["A","B"]:
                load_policy()
                print(f"{scenario} / {track} / {pathway}: detection",flush=True)
                # Each path receives independent copies of exactly the same dirty data.
                incoming={k:v.copy(deep=True) for k,v in dirty.items()}
                before=frame_hashes(incoming)
                ledger,rules,components=detect(incoming,spec,track,pathway,policy,template)
                if before!=frame_hashes(incoming):raise RuntimeError("Detector mutated its inputs")
                corrected,audit=correct(incoming,ledger,truth)
                rebuilt,_=rebuild_track(corrected,spec,track)
                paths[pathway]=summaries(rebuilt)
                prefix=f"{scenario}_{track}_{pathway}"
                pd.DataFrame(ledger).to_csv(directory/(prefix+"_flags.csv.gz"),index=False)
                components.groupby(["component","status"]).size().to_csv(directory/(prefix+"_components.csv"))
                output["pathHashes"].append({"scenario":scenario,"track":track,"pathway":pathway,
                                            "dirty":before,"corrected":frame_hashes(corrected),"rebuilt":frame_hashes(rebuilt)})
                for name,table in paths[pathway].items():
                    if isinstance(table,pd.DataFrame):table.to_csv(directory/(prefix+"_"+name.replace(" ","_")+".csv.gz"),index=False)
                episodes=len({r["episodeId"] for r in ledger})
                corrected_rows=len({(r["domain"],r["sourceRow"]) for r in audit if r["corrected"]})
                output["outcomeA"].append({"scenario":scenario,"track":track,"pathway":pathway,
                    "predicateFlags":len(ledger),"uniqueQueryEpisodes":episodes,"mutatedRecordsCaptured":corrected_rows,
                    "injectedErrorQueryYieldPercent":100*corrected_rows/episodes if episodes else None,
                    "unresolvedIdentityFlags":sum(not r["automaticCorrectionEligible"] for r in ledger)})
                critical=[r for r in audit if r["critical"]]
                output["outcomeB"].append({"scenario":scenario,"track":track,"pathway":pathway,
                    "criticalInjected":len(critical),"criticalCaptured":sum(r["captured"] for r in critical),
                    "criticalMissed":sum(not r["captured"] for r in critical)})
                output["mutationAudit"].extend([{"scenario":scenario,"track":track,"pathway":pathway,**r} for r in audit])
                save(directory/"results_in_progress.json",output)
                print(f"{prefix}: {episodes} query episodes; {sum(not r['captured'] for r in critical)} critical mutations missed",flush=True)
            for label,a,b in [("A vs clean",paths["A"],clean[track]),("B vs clean",paths["B"],clean[track]),("B vs A",paths["B"],paths["A"])]:
                for name in clean[track]:
                    audit,differences=compare_summary(a[name],b[name])
                    context={"scenario":scenario,"track":track,"comparison":label,"summary":name}
                    output["outcomeC"].append({**context,**audit})
                    output["cellDifferences"].extend([{**context,**d} for d in differences])
        output["scenariosExecuted"].append(scenario)
        save(directory/"results_in_progress.json",output)
    load_policy()
    output["status"]="COMPLETED — SCOPED FEASIBILITY ONLY"
    save(directory/"scoped_results.json",output)
    from export_scoped_study import export
    export(output)
    print("Scoped study completed; no claim of full 125-rule or CSR-shell validation.",flush=True)

if __name__=="__main__":main()
