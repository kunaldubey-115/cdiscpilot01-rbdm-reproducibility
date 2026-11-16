"""Record identities for queries; no target-data or correction access."""
import json
import pandas as pd

def collect_flags(rule_id,domain,source,evaluated,mask):
    if not source.index.is_unique:
        raise ValueError("Source row indices must be unique before rule execution")
    if not mask.index.equals(evaluated.index):
        raise ValueError("Rule mask is not aligned with its evaluated records")
    seq=domain+"SEQ"
    keycols=["USUBJID"]+([seq] if seq in source.columns and seq in evaluated.columns else [])
    groups={}
    for index,row in source.iterrows():
        key=tuple(row[k] for k in keycols)
        groups.setdefault(key,[]).append(index)
    result=[]
    for _,row in evaluated.loc[mask.fillna(False).astype(bool)].iterrows():
        key=tuple(row[k] for k in keycols)
        candidates=groups.get(key,[])
        # Aggregate subject-level flags cannot automatically authorize correction
        # of every source record. Duplicate keys require adjudication as well.
        record_scope=(seq in keycols or domain=="DM") and len(candidates)==1
        identity=dict(zip(keycols,[str(v) for v in key]))
        episode=[domain,*[str(v) for v in key]]
        if not record_scope:
            for column in ("VISITNUM","QSDTC","AVISITN"):
                if column in row and pd.notna(row[column]):
                    identity[column]=str(row[column]);episode.extend([column,str(row[column])])
        result.append({"ruleId":rule_id,"domain":domain,"subject":str(row["USUBJID"]),
                       "scope":"record" if record_scope else "subject_or_ambiguous",
                       "sourceRow":int(candidates[0]) if record_scope else None,
                       "candidateRows":len(candidates),"key":json.dumps(identity,sort_keys=True),
                       "episodeId":json.dumps(episode,ensure_ascii=True),
                       "automaticCorrectionEligible":record_scope})
    return result
