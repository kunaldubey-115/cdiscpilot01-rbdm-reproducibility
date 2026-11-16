"""Key-aligned cell audits; compare BOTH pathways to clean, not just each other."""
import json
import numpy as np
import pandas as pd
from dual_track_models import model_summary
from tables import BUILDERS

def summaries(data):
    result={}
    pop=data["adsl"][["USUBJID","ITTFL","SAFFL","EFFFL","COMP24FL"]]
    result["Population flags"]=pop.melt(id_vars="USUBJID",var_name="Flag",value_name="Value")
    try:result["Models and TTDE"]=model_summary(data)
    except Exception as error:result["Models and TTDE"]={"error":type(error).__name__+": "+str(error)}
    for name,builder in BUILDERS.items():
        try:result[name+" regenerated summary"]=builder(data[name])
        except Exception as error:result[name+" regenerated summary"]={"error":type(error).__name__+": "+str(error)}
    return result

def compare_summary(actual,expected):
    if isinstance(actual,dict) or isinstance(expected,dict):
        return {"status":"NOT EVALUABLE","cells":None,"mismatches":None,"mismatchPercent":None,
                "detail":str({"actual":actual if isinstance(actual,dict) else "OK","expected":expected if isinstance(expected,dict) else "OK"})},[]
    value="Subjects" if "Subjects" in expected.columns else "Value"
    keys=[c for c in expected.columns if c!=value]
    if actual.columns.tolist()!=expected.columns.tolist():raise ValueError("Summary schema changed")
    if actual.duplicated(keys).any() or expected.duplicated(keys).any():raise ValueError("Ambiguous summary key")
    a=actual.set_index(keys)[value];b=expected.set_index(keys)[value]
    union=a.index.union(b.index);av=a.reindex(union);bv=b.reindex(union)
    structural=~union.isin(a.index)|~union.isin(b.index)
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
        equal=np.isclose(av,bv,atol=1e-8,rtol=1e-10,equal_nan=True)
    else:equal=(av.eq(bv)|(av.isna()&bv.isna())).to_numpy()
    differences=[]
    for i in np.flatnonzero(structural|~equal):
        differences.append({"key":str(union[i]),"column":"ALL — missing row" if structural[i] else value,
                            "actual":str(av.iloc[i]),"expected":str(bv.iloc[i])})
    count=int(structural.sum())*len(expected.columns)+int((~equal&~structural).sum())
    cells=len(union)*len(expected.columns)
    return {"status":"MATCH" if count==0 else "DIFFERENCE","cells":cells,"mismatches":count,
            "mismatchPercent":100*count/cells if cells else None,"detail":"Key-aligned regenerated summaries; not certification of complete CSR shells"},differences
