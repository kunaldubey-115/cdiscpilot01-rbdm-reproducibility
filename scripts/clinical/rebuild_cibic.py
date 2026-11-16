"""CIBIC+ source reconstruction using SAP windows and selected-observation LOCF."""
import re
import numpy as np
import pandas as pd
from rebuild_adsl import sas_date

WINDOWS={8:(2.,84.,56.,"2-84"),16:(85.,140.,112.,"85-140"),24:(141.,np.nan,168.,">140")}

def set_window(frame,visit):
    lo,hi,target,label=WINDOWS[visit]
    frame["AVISITN"]=float(visit)
    frame["AVISIT"]=f"Week {visit}"
    frame["AWLO"]=lo
    frame["AWHI"]=hi
    frame["AWTARGET"]=target
    frame["AWRANGE"]=label
    frame["AWTDIFF"]=(frame["ADY"]-target).abs()
    return frame

def rebuild_cibic(sdtm,adsl,items):
    q=sdtm["qs"]
    q=q.loc[q.QSCAT.eq("CLINICIAN'S INTERVIEW-BASED IMPRESSION OF CHANGE (CIBIC+)") & q.USUBJID.isin(adsl.USUBJID)].copy().reset_index(drop=True)
    out=pd.DataFrame(index=q.index)
    subject=adsl.set_index("USUBJID")
    evidence={}
    for name,spec in items.items():
        match=re.fullmatch(r"(ADSL|QS)\.([A-Z0-9]+)",spec["comment"].strip())
        if not match:
            continue
        domain,column=match.groups()
        if domain=="ADSL":
            if column=="FASFL":
                column="EFFFL"
            if column=="USUBJID":
                out[name]=q.USUBJID
            elif column in subject:
                out[name]=q.USUBJID.map(subject[column])
            else:
                continue
        elif column in q:
            out[name]=q[column]
        else:
            continue
        evidence[name]="Define direct mapping: "+spec["comment"]+("; legacy FASFL interpreted as the defined EFFFL." if name=="EFFFL" else "")
    out["ADT"]=sas_date(q.QSDTC)
    out["ADY"]=out.ADT-out.TRTSDT+out.ADT.ge(out.TRTSDT).astype(int)
    out["PARAMCD"]="CIBICVAL"
    out["PARAM"]="CIBIC Score"
    out["PARAMN"]=1.
    out["AVAL"]=q.QSSTRESN
    out["DTYPE"]=""
    out["AWU"]="DAYS"
    out["ANL01FL"]=""
    out["AVISIT"]=""
    out["AWRANGE"]=""
    for name in ["AVISITN","AWLO","AWHI","AWTARGET","AWTDIFF"]:
        out[name]=np.nan
    for visit,(lo,hi,_,_) in WINDOWS.items():
        mask=out.ADY.ge(lo) & (out.ADY.le(hi) if pd.notna(hi) else True)
        assigned=set_window(out.loc[mask].copy(),visit)
        out.loc[mask,assigned.columns]=assigned
    eligible=out.loc[out.AVISITN.notna() & out.AVAL.notna()]
    first=eligible.sort_values(["USUBJID","AVISITN","AWTDIFF","ADY","QSSEQ"],kind="stable").drop_duplicates(["USUBJID","AVISITN"]).index
    out.loc[first,"ANL01FL"]="Y"
    imputed=[]
    for _,group in out.loc[first].groupby("USUBJID",sort=True):
        present=set(group.AVISITN)
        for visit in WINDOWS:
            if visit in present:
                continue
            previous=group.loc[group.AVISITN.lt(visit)].sort_values("AVISITN")
            if previous.empty:
                continue
            row=set_window(previous.iloc[[-1]].copy(),visit)
            row["DTYPE"]="LOCF"
            row["ANL01FL"]="Y"
            imputed.append(row)
    if imputed:
        out=pd.concat([out,*imputed],ignore_index=True)
    for column in out:
        if column not in evidence:
            evidence[column]="Define: "+items[column]["comment"]
    evidence["AVISITN"]+=" SAP §8.2, physical CSR p426: ADY 2–84, 85–140, >140."
    evidence["ANL01FL"]+=" Closest target day; equidistant assessments prefer earlier ADY, then source sequence."
    evidence["DTYPE"]+=" Only analysis-selected observations carried forward; no backwards imputation."
    evidence["AWHI"]+=" Unbounded >140 window represented as missing upper limit; no undocumented sentinel inserted."
    return out,evidence
