"""Source-only adverse-event reconstruction using define comments and rebuilt ADSL."""
import re
import numpy as np
import pandas as pd
from rebuild_adsl import sas_date

def rebuild_adae(sdtm, adsl, items):
    ae=sdtm["ae"].loc[sdtm["ae"].USUBJID.isin(adsl.USUBJID)].copy().reset_index(drop=True)
    if ae.duplicated(["USUBJID","AESEQ"]).any():
        raise ValueError("ADAE source subject/sequence key is not unique.")
    subject=adsl.set_index("USUBJID")
    out=pd.DataFrame(index=ae.index)
    evidence={}
    for name,spec in items.items():
        match=re.fullmatch(r"(AE|ADSL)\.([A-Z0-9]+)",spec["comment"].strip())
        if not match:
            continue
        domain,variable=match.groups()
        if domain=="AE" and variable in ae:
            out[name]=ae[variable]
        elif domain=="ADSL" and variable in subject:
            out[name]=ae.USUBJID.map(subject[variable])
        elif variable=="USUBJID":
            out[name]=ae.USUBJID
        else:
            continue
        evidence[name]="Define direct mapping: "+spec["comment"]
    start=ae.AESTDTC.fillna("").astype(str)
    impute_day=start.str.fullmatch(r"\d{4}-\d{2}")
    out["ASTDT"]=sas_date(start.where(~impute_day,start+"-01"))
    out["ASTDTF"]=np.where(impute_day,"D","")
    out["AENDT"]=sas_date(ae.AEENDTC)
    for date,day in [("ASTDT","ASTDY"),("AENDT","AENDY")]:
        out[day]=out[date]-out.TRTSDT+out[date].ge(out.TRTSDT).astype(int)
    # Published adae.sas calculates ADUR before imputing onset days.
    out["ADURN"]=out.AENDT-sas_date(start)+1
    out["ADURU"]=np.where(out.ADURN.notna(),"DAY","")
    out["TRTEMFL"]=np.where(out.ASTDT.notna() & out.TRTSDT.notna() & out.ASTDT.ge(out.TRTSDT),"Y","N")
    term=out.AEDECOD.fillna("")
    soc=out.AEBODSYS.fillna("")
    derm=term.str.contains("APPLICATION|DERMATITIS|ERYTHEMA|BLISTER",regex=True) | (
        soc.eq("SKIN AND SUBCUTANEOUS TISSUE DISORDERS") & ~term.isin(["COLD SWEAT","HYPERHIDROSIS","ALOPECIA"]))
    out["CQ01NAM"]=np.where(derm,"DERMATOLOGIC EVENTS","")
    selected=out.TRTEMFL.eq("Y")
    for column,groups,mask in [
        ("AOCCFL",["USUBJID"],selected),
        ("AOCCSFL",["USUBJID","AEBODSYS"],selected & soc.ne("")),
        ("AOCCPFL",["USUBJID","AEBODSYS","AEDECOD"],selected & term.ne("")),
        ("AOCC02FL",["USUBJID"],selected & out.AESER.eq("Y")),
        ("AOCC03FL",["USUBJID","AEBODSYS"],selected & out.AESER.eq("Y") & soc.ne("")),
        ("AOCC04FL",["USUBJID","AEBODSYS","AEDECOD"],selected & out.AESER.eq("Y") & term.ne("")),
        ("AOCC01FL",["USUBJID"],selected & derm),
    ]:
        out[column]=""
        first=out.loc[mask].sort_values(groups+["ASTDT","AESEQ"],kind="stable").drop_duplicates(groups).index
        out.loc[first,column]="Y"
    for column in out:
        if column not in evidence:
            evidence[column]="Define: "+items[column]["comment"]
    evidence["ASTDT"]+=" Only YYYY-MM onset dates impute day 01; year-only dates remain missing, as specified."
    evidence["CQ01NAM"]+=" Published adae.sas uses literal case-sensitive terms and SKIN AND SUBCUTANEOUS TISSUE DISORDERS, resolving the define's whitespace typo without modifying source terms."
    evidence["AOCC01FL"]="Published adae.sas flagfrst macro explicitly selects CQ01NAM='DERMATOLOGIC EVENTS'; resolves the define's contradictory empty-string predicate."
    evidence["ADURN"]="Published adae.sas computes ADUR from original complete onset/end dates BEFORE onset-day imputation; mapped to updated ADURN, preserving missing duration."
    evidence["ADURU"]="Define DAY only when ADURN nonmissing; original-code duration-before-imputation order retained."
    return out,evidence
