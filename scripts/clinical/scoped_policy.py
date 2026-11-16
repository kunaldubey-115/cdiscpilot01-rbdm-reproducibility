"""Prespecified feasibility policy; unsupported rules never become passes."""
import hashlib
import json
from pathlib import Path
import openpyxl
from dual_track import OUT, DATA, POLICY, TRACKS, rebuild_track, specifications, compare_dataset, gate, TARGETS
import pandas as pd
from rules import evaluate_rules

ROOT=Path(__file__).resolve().parents[2]
GAPS={22,51,93,104,118,125}
SUPPRESS=GAPS|{89,122}

def freeze(source):
    directory=OUT/"scoped-study";directory.mkdir(exist_ok=True)
    path=directory/"frozen_policy.json"
    if path.exists():raise RuntimeError("Frozen study exists; do not overwrite or retune after viewing results")
    spec=specifications()
    built={t:rebuild_track(source,spec,t) for t in TRACKS}
    baseline={t:v[0] for t,v in built.items()}
    targets={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in TARGETS}
    clean_gate=gate(*built[TRACKS[0]],targets)
    if not clean_gate["passed"]:raise RuntimeError("Nine-dataset reference gate failed")
    del targets
    # Verify the narrowly scoped metadata removals before generating challenges.
    changed={k:v.copy(deep=True) for k,v in source.items()}
    dated=changed["vs"].VSDTC.str.len().ge(10)
    changed["vs"].loc[dated,"VSDTC"]=changed["vs"].loc[dated,"VSDTC"].str[:10]+"T23:59"
    changed["sc"]["SCCAT"]=changed["sc"].SCCAT.str.lower()
    proofs=[]
    for track in TRACKS:
        rebuilt,_=rebuild_track(changed,spec,track)
        for name in baseline[track]:
            rows=compare_dataset(name,rebuilt[name],baseline[track][name],{})
            if any(r["status"]!="MATCH" for r in rows):
                raise RuntimeError("Metadata independence check failed: "+track+"/"+name)
            proofs.append({"track":track,"dataset":name,"metadataPerturbation":"VS clock added/changed to 23:59 + SCCAT lowercase","status":"MATCH"})
    template=openpyxl.load_workbook(ROOT/"scripts/clinical/input/template.xlsx",data_only=True)
    evaluated=evaluate_rules(template,{**source,**baseline[TRACKS[0]]})
    active=[r["id"] for r in evaluated if r["status"]=="evaluated"]
    if len(active)!=48:raise RuntimeError("Executable scope changed; review policy before freeze")
    domains={
        "DM":("ADSL and downstream populations/site factors","Demographics, all models and safety summaries"),
        "DS":("ADSL completion/disposition; exposure fallback","Completer populations and downstream models"),
        "EX":("ADSL exposure and ADAE treatment-emergence","Safety population and TTDE"),
        "AE":("ADAE, dermatologic flags, ADTTE","Safety and TTDE"),
        "QS":("ADSL efficacy/MMSE; ADQSADAS, ADQSCIBC, ADQSNPIX","Primary models and NPI summaries"),
        "LB":("ADLBC, ADLBH baseline/changes/abnormality","Laboratory shifts"),
        "VS":("ADSL baseline covariates; ADVS","Demographics and vital summaries"),
        "MH":("ADSL primary-diagnosis onset/duration","Demographic summaries"),
        "CM":("No direct dependency in nine current builders; clinical restrictions remain unresolved","Other submission/clinical dependencies unknown"),
        "SC":("ADSL education from characteristic result fields","Demographic education summaries"),
    }
    matrix=[]
    lookup={r["id"]:r for r in evaluated}
    for raw in template["Published_Control_DRP_A"].iter_rows(min_row=5,max_row=129,values_only=True):
        rid,_,domain,fields,_,description,reference,tier,original=raw[:9]
        r=lookup[rid];number=int(rid[-3:])
        if number in GAPS:
            reason="Remove contiguous-number predicate only. Shared positive-integer and duplicate-key safeguards remain in BOTH pathways. No record is deleted or renumbered."
        elif number==89:
            reason="Calendar dates retained; exact HH:MM omission alone suppressed for this analysis-feasibility scope. All-nine source-rebuild independence tested in both tracks. Not a blanket clinical timing waiver."
        elif number==122:
            reason="Uppercase-only SCCAT formatting suppressed; education values, coding and source records untouched. All-nine independence tested in both tracks."
        else:reason="Retain; no suppression justified. Unknown dependencies and blocked checks are not treated as clean."
        matrix.append({"rule":rid,"domain":domain,"sourceFields":fields,"description":r["description"],
            "workbookReferenceUnverified":reference,"tier":tier,"executionStatus":r["status"],
            "protocolSAPNeed":"Preserve efficacy, consent and safety protections; workbook reference is not independent adjudication",
            "lineage":domains[domain][0],"TFLDependency":domains[domain][1],
            "mandatoryProtection":"All Tier 1/2 checks retained; external and unavailable protections explicitly unresolved",
            "DRPA":"EXECUTE" if rid in active else "BLOCKED / EXTERNAL",
            "DRPB":"SUPPRESS SCOPED PREDICATE" if number in SUPPRESS else ("EXECUTE" if rid in active else "RETAIN — NOT EXECUTABLE"),
            "reason":reason})
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in DATA.rglob("*") if p.is_file() and p.suffix in (".xpt",".xml",".pdf",".sas")}
    for p in [ROOT/"scripts/clinical/input/template.xlsx",*list((OUT/"reference-evidence").glob("*"))]:
        if p.is_file():sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    code={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")}
    policy={"design":"Scoped dual-track feasibility; not full 125-rule validation",
        "activeA":active,"activeB":[rid for rid in active if int(rid[-3:]) not in SUPPRESS],
        "matrix":matrix,"metadataIndependence":proofs,"sourceHashes":sources,"codeHashes":code,
        "tolerances":POLICY["tolerances"],"seeds":POLICY["seeds"],
        "sharedSafeguards":"Unique positive integer sequence identifiers in each source domain; supported EX order, SAP lab threshold and VS completeness components",
        "correction":"Independent single-pass whole-record source verification: restore injected cells only on uniquely identified flagged source rows, identically for A/B. Detectors never receive the injection truth ledger.",
        "criticalDetection":"Known critical mutation's source row was uniquely flagged for review; not proof a specific rule diagnosed its cause.",
        "queryYield":"Known injected-error-containing flagged records / all deduplicated query episodes; not clinically adjudicated query PPV",
        "sampling":"Development and held-out perturbed subjects separated by stable subject hash parity; all records remain in study datasets. Held-out selection/magnitudes differ.",
        "endpointScope":"Population flags, three fitted models, TTDE KM, and regenerated demographic/NPI/lab/vital summaries. Not certified complete CSR shells.",
        "noRetuning":"Do not change rules, corrections or thresholds after either challenge is inspected."}
    policy["cleanGate"]=clean_gate["coverage"]
    policy["criticalityCaveat"]="Tier-3 metadata perturbations follow the requested analytic scenario; their classification does not certify clinical harmlessness."
    policy["preExecutionAmendment"]="Initial attempt aborted during development-input construction: no VS clock times existed to remove. No pathway ran, no outcomes were inspected and held-out generation was not reached. Preserve the initial lock in scoped-study-aborted-before-execution. Revised clock perturbation removes an existing time or, if absent, adds 12:34 (development) / 23:59 (held-out). Independence test now adds clock times. All decision rules, corrections, tolerances and seeds unchanged."
    blob=json.dumps(policy,indent=2,sort_keys=True)
    path.write_text(blob)
    (directory/"policy.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest())
    return policy

def load_policy():
    directory=OUT/"scoped-study";blob=(directory/"frozen_policy.json").read_text()
    if hashlib.sha256(blob.encode()).hexdigest()!=(directory/"policy.sha256").read_text():
        raise RuntimeError("Frozen policy hash mismatch")
    policy=json.loads(blob)
    for path,digest in policy["sourceHashes"].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise RuntimeError("Source changed: "+path)
    for name,digest in policy["codeHashes"].items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=digest:raise RuntimeError("Code changed after freeze: "+name)
    return policy
