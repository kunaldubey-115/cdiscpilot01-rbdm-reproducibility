"""Detectors see dirty data only. Correction is a separate simulation oracle."""
import pandas as pd
import numpy as np
from rules import evaluate_rules
from safety_components import evaluate_components
from discrepancy_ledger import collect_flags
from dual_track import rebuild_track

def detect(source,spec,track,pathway,policy,template):
    rebuilt,_=rebuild_track(source,spec,track)
    ledger=[]
    rules=evaluate_rules(template,{**source,**rebuilt},ledger=ledger)
    active=set(policy["activeA" if pathway=="A" else "activeB"])
    if any(r["status"]!="evaluated" for r in rules if r["id"] in active):
        raise RuntimeError("Frozen active rule became unavailable")
    ledger=[r for r in ledger if r["ruleId"] in active]
    for domain,frame in source.items():
        seq=domain.upper()+"SEQ"
        if seq not in frame:continue
        numeric=pd.to_numeric(frame[seq],errors="coerce")
        mask=numeric.isna() | ~np.isfinite(numeric) | numeric.le(0) | numeric.ne(np.floor(numeric)) | frame.duplicated(["USUBJID",seq],keep=False)
        ledger.extend(collect_flags("SHARED."+domain.upper()+".identity",domain.upper(),frame,frame,mask))
    components=evaluate_components(source)
    for row in components.loc[components.status.eq("FLAG")].to_dict("records"):
        domain=row["domain"];frame=source[domain.lower()]
        selected=frame.loc[[row["sourceRow"]]]
        ledger.extend(collect_flags("SHARED."+row["component"],domain,frame,selected,pd.Series(True,index=selected.index)))
    return ledger,rules,components

def correct(source,ledger,truth):
    """Simulated verification restores known injected cells on uniquely flagged rows.

    No uninjected cell is edited. Neither detector nor policy receives truth.
    Whole-record verification can discover a mutation unrelated to the triggering
    rule; report capture, not rule-specific diagnostic sensitivity.
    """
    result={k:v.copy(deep=True) for k,v in source.items()}
    identified={(r["domain"],r["sourceRow"]) for r in ledger if r["automaticCorrectionEligible"]}
    audit=[]
    for mutation in truth:
        captured=(mutation["domain"],mutation["sourceRow"]) in identified
        if captured:
            result[mutation["domain"].lower()].at[mutation["sourceRow"],mutation["field"]]=mutation["before"]
        audit.append({**mutation,"captured":captured,"corrected":captured})
    return result,audit
