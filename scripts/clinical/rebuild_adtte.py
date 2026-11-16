"""TTDE from rebuilt subject and adverse-event data; no target-value lookups."""
import re
import numpy as np
import pandas as pd
from rebuild_adsl import sas_date

def rebuild_adtte(adsl, adae, items):
    out=pd.DataFrame(index=adsl.index)
    evidence={}
    for name,spec in items.items():
        match=re.fullmatch(r"ADSL\.([A-Z0-9]+)",spec["comment"].strip())
        if match and match[1] in adsl and name!="STARTDT":
            out[name]=adsl[match[1]]
            evidence[name]="Define direct mapping: "+spec["comment"]
    events=adae.loc[adae.AOCC01FL.eq("Y")]
    if events.USUBJID.duplicated().any():
        raise ValueError("Multiple first dermatologic events for a subject.")
    events=events.set_index("USUBJID")
    onset=adsl.USUBJID.map(events.ASTDT)
    observed=onset.notna() & onset.ge(adsl.TRTSDT)
    out["PARAM"]="Time to First Dermatologic Event"
    out["PARAMCD"]="TTDE"
    out["STARTDT"]=sas_date(adsl.RFSTDTC)
    out["ADT"]=onset.where(observed,sas_date(adsl.RFENDTC))
    out["CNSR"]=np.where(observed,0.,1.)
    out["AVAL"]=out.ADT-out.STARTDT+1
    out["EVNTDESC"]=np.where(observed,"Dematologic Event Occured","Study Completion Date")
    out["SRCDOM"]=np.where(observed,"ADAE","ADSL")
    out["SRCVAR"]=np.where(observed,"ASTDT","RFENDT")
    out["SRCSEQ"]=adsl.USUBJID.map(events.AESEQ).where(observed)
    for column in out:
        if column not in evidence:
            evidence[column]="Define: "+items[column]["comment"]
    evidence["STARTDT"]+=" RFSTDTC converted to SAS date."
    evidence["ADT"]+=" Event selection from published ADAE first-dermatologic-event flag; treatment-start-day events included."
    return out,evidence
