"""Shared source-only BDS mechanics. Reference datasets are never inputs."""
import re
import numpy as np
import pandas as pd
from rebuild_adsl import sas_date, normalize_precision

def source_frame(source, adsl, items, domain):
    source=source.loc[source.USUBJID.isin(adsl.USUBJID)].copy().reset_index(drop=True)
    subject=adsl.set_index("USUBJID")
    out=pd.DataFrame(index=source.index)
    for name,spec in items.items():
        if spec["oid"].count(".")!=1:
            continue
        match=re.fullmatch(r"(ADSL|"+domain+r")\.([A-Z0-9]+)",spec["comment"].strip())
        if not match:
            continue
        table,column=match.groups()
        if table=="ADSL":
            column={"FASFL":"EFFFL"}.get(column,column)
            # Guide p4 distinguishes character treatment from numeric dose.
            if name=="TRTA":column="TRT01A"
            if column=="USUBJID":out[name]=source.USUBJID
            elif column in subject:out[name]=source.USUBJID.map(subject[column])
        elif column in source:out[name]=source[column]
    return source,out

def parameter_labels(out,items):
    out["PARAM"]=out.PARAMCD.map(items["PARAMCD"]["codes"])
    inverse={v:float(k) for k,v in items["PARAMN"]["codes"].items()}
    out["PARAMN"]=out.PARAM.map(inverse)

def baseline(out,keys,flag):
    selected=out.loc[flag]
    if selected.duplicated(keys).any():
        raise ValueError("Ambiguous multiple baseline observations: "+str(keys))
    values=selected.set_index(keys).AVAL
    out["BASE"]=values.reindex(pd.MultiIndex.from_frame(out[keys])).to_numpy()

def evidence(items):
    return {k:"Cached define: "+v["comment"] for k,v in items.items() if v["oid"].count(".")==1}

def scheduled_visits(out,visit):
    week=pd.to_numeric(visit.str.extract(r"^WEEK (\d+)",expand=False),errors="coerce")
    out["AVISITN"]=week.where(~visit.eq("BASELINE"),0.)
    out["AVISIT"]=np.where(visit.eq("BASELINE"),"Baseline",np.where(week.notna(),"Week "+week.fillna(0).astype(int).astype(str),""))

def rebuild_advs(sdtm,adsl,items,*,mode="sap"):
    if mode not in ("sap","reference-compatible"):raise ValueError("Unknown mode")
    source,out=source_frame(sdtm["vs"],adsl,items,"VS")
    out["PARAMCD"]=source.VSTESTCD
    parameter_labels(out,items)
    out["ATPT"]=source.VSTPT
    out["ATPTN"]=source.VSTPTNUM
    out["ADT"]=sas_date(source.VSDTC)
    out["AVAL"]=source.VSSTRESN
    out["ABLFL"]=source.VSBLFL
    baseline(out,["USUBJID","PARAMCD","ATPT"],out.ABLFL.eq("Y"))
    out["CHG"]=out.AVAL-out.BASE
    out["PCHG"]=100*out.CHG/out.BASE.replace(0,np.nan)
    scheduled_visits(out,source.VISIT)
    out["ANL01FL"]=np.where(out.AVISITN.notna(),"Y","")
    keys=["USUBJID","PARAMCD","ATPT"]
    eligible=out.loc[(out.AVISITN.between(4,26) if mode=="reference-compatible" else out.AVISITN.gt(0) & out.AVISITN.le(24)) & (True if mode=="reference-compatible" else out.AVAL.notna())]
    end=eligible.sort_values(keys+["ADT","VSSEQ"]).drop_duplicates(keys,keep="last").copy()
    end["AVISITN"]=99.;end["AVISIT"]="End of Treatment"
    out=pd.concat([out,end],ignore_index=True)
    info=evidence(items)
    info["TRTA"]="Guide p4 character treatment; legacy TRTA numeric-dose comment conflicts with variable type."
    info["AVISIT"]="SAP section 11.6: end of treatment is the last planned postbaseline assessment on or before Week 24. Reference Week 26 EOT records are not silently adopted."
    if mode=="reference-compatible":
        info["AVISIT"]="Experimental reference-compatible EOT: last observed scheduled Week 4–26 assessment per subject/parameter/timepoint. Not authenticated SAS logic; differs from SAP Week-24 boundary."
    return out,info

def rebuild_labs(sdtm,adsl,items,category,*,mode="sap"):
    if mode not in ("sap","reference-compatible"):raise ValueError("Unknown mode")
    parameters=set(items["PARAMCD"]["codes"])
    selected=sdtm["lb"].loc[sdtm["lb"].LBTESTCD.isin(parameters)]
    if mode=="reference-compatible":
        selected=selected.loc[~selected.VISITNUM.isin([2,3,6,201])]
    source,out=source_frame(selected,adsl,items,"LB")
    out["PARAMCD"]=source.LBTESTCD
    out["ADT"]=sas_date(source.LBDTC)
    out["ADY"]=source.LBDY
    out["AVAL"]=source.LBSTRESN
    out["PARCAT1"]=category
    out["ABLFL"]=np.where(source.VISITNUM.eq(1),"Y","")
    out["A1LO"]=source.LBSTNRLO
    out["A1HI"]=source.LBSTNRHI
    if mode=="reference-compatible":
        out["A1LO"]=out.A1LO.mask(out.A1LO.abs().lt(1e-70))
    out["ALBTRVAL"]=pd.concat([out.AVAL-1.5*out.A1HI,.5*out.A1LO-out.AVAL],axis=1).max(axis=1)
    if mode=="reference-compatible":
        out["ALBTRVAL"]=pd.concat([(out.AVAL-1.5*source.LBSTNRHI).abs(),(.5*source.LBSTNRLO-out.AVAL).abs()],axis=1).max(axis=1)
    out["ANRIND"]=np.select([out.AVAL.lt(.5*out.A1LO),out.AVAL.gt(1.5*out.A1HI)],["L","H"],default="N")
    if mode=="sap":out.loc[out.AVAL.isna(),"ANRIND"]=""
    if mode=="reference-compatible":
        out.loc[out.A1HI.isna() & source.LBNRIND.eq("ABNORMAL") & out.AVAL.notna(),"ANRIND"]="H"
    keys=["USUBJID","PARAMCD"]
    baseline(out,keys,out.ABLFL.eq("Y"))
    index=pd.MultiIndex.from_frame(out[keys])
    base=out.loc[out.ABLFL.eq("Y")].set_index(keys)
    out["BNRIND"]=base.ANRIND.reindex(index).fillna("").to_numpy()
    # Literal define mappings; apparent ratio-label reversal remains visible.
    out["R2A1LO"]=out.AVAL/out.A1HI.replace(0,np.nan)
    out["R2A1HI"]=out.AVAL/out.A1LO.replace(0,np.nan)
    if mode=="reference-compatible":
        out["R2A1LO"],out["R2A1HI"]=out["R2A1HI"].copy(),out["R2A1LO"].copy()
    for dest,src in [("BR2A1LO","R2A1LO"),("BR2A1HI","R2A1HI")]:
        out[dest]=out.loc[out.ABLFL.eq("Y")].set_index(keys)[src].reindex(index).to_numpy()
    out["CHG"]=out.AVAL-out.BASE
    if mode=="reference-compatible":out.loc[out.ABLFL.eq("Y"),"CHG"]=np.nan
    scheduled_visits(out,source.VISIT)
    out.loc[source.VISITNUM.eq(1),["AVISITN","AVISIT"]]=[0.,"Baseline"]
    out["AENTMTFL"]=""
    eligible=out.loc[source.VISITNUM.between(4,12)]
    if mode=="reference-compatible":
        eligible=eligible.loc[eligible.VISITNUM.isin([4,5,7,8,9,10,11,12])]
    last=eligible.sort_values(keys+["ADT","LBSEQ"]).drop_duplicates(keys,keep="last").index
    out.loc[last,"AENTMTFL"]="Y"
    if mode=="reference-compatible":
        out["AENTMTFL"]=""
        final=eligible.sort_values(keys+["ADT","LBSEQ"]).drop_duplicates(keys,keep="last")
        out.loc[final.index,"AENTMTFL"]="Y"
    out["ANL01FL"]=""
    maximum_pool=eligible.loc[eligible.ALBTRVAL.notna()] if mode=="reference-compatible" else eligible
    maximum=maximum_pool.sort_values(keys+["ALBTRVAL","ADT","LBSEQ"],ascending=[True,True,False,True,True]).drop_duplicates(keys).index
    out.loc[maximum,"ANL01FL"]="Y"
    derived=out.copy()
    ordered=out.sort_values(keys+["ADT","LBSEQ"])
    if mode=="reference-compatible":
        ordered=ordered.loc[ordered.VISITNUM.isin([1,4,5,7,8,9,10,11,12,13])]
    previous=ordered.groupby(keys).AVAL.shift().reindex(out.index)
    denominator=.5*(source.LBSTNRHI-source.LBSTNRLO) if mode=="reference-compatible" else .5*(out.A1HI-out.A1LO)
    derived["AVAL"]=(out.AVAL-previous)/denominator.replace(0,np.nan)
    derived.loc[source.LBBLFL.eq("Y"),"AVAL"]=np.nan
    derived["PARAMCD"]="_"+out.PARAMCD
    if mode=="reference-compatible":
        for code,definition in items["AVAL"].get("values",{}).items():
            precision=definition.get("precision")
            if precision is not None:
                mask=derived.PARAMCD.eq(code)
                derived.loc[mask,"AVAL"]=normalize_precision(derived.loc[mask,"AVAL"].round(12),precision)
    clear=["BASE","CHG","A1LO","A1HI","R2A1LO","R2A1HI","BR2A1LO","BR2A1HI"]
    if mode!="reference-compatible":clear.append("ALBTRVAL")
    for c in clear:
        derived[c]=np.nan
    derived["ABLFL"]="";derived["BNRIND"]=""
    derived["ANRIND"]=np.select([derived.AVAL.lt(-1),derived.AVAL.gt(1)],["L","H"],default="N")
    derived.loc[derived.AVAL.isna(),"ANRIND"]=""
    derived["ANL01FL"]=""
    candidates=derived.loc[source.VISITNUM.between(4,12) & derived.AVAL.notna()].assign(magnitude=lambda f:f.AVAL.abs())
    if mode=="reference-compatible":
        candidates=candidates.loc[candidates.VISITNUM.isin([4,5,7,8,9,10,11,12])]
    first=candidates.sort_values(keys+["magnitude","ADT","LBSEQ"],ascending=[True,True,False,True,True]).drop_duplicates(keys).index
    derived.loc[first,"ANL01FL"]="Y"
    out=pd.concat([out,derived],ignore_index=True)
    parameter_labels(out,items)
    end=out.loc[out.AENTMTFL.eq("Y")].copy()
    end["AVISITN"]=99.;end["AVISIT"]="End of Treatment"
    out=pd.concat([out,end],ignore_index=True)
    if mode=="reference-compatible":out["AVISIT"]=out.AVISIT.replace("",".").str.rjust(16)
    info=evidence(items)
    if mode=="reference-compatible":
        for field in ["AVISIT","AVAL","ANRIND","ANL01FL","ALBTRVAL","A1LO","R2A1LO","R2A1HI","AENTMTFL"]:
            info[field]="EXPERIMENTAL reference-compatible convention; see Tested_Conventions in ADaM_Reference_Compatibility_Experiments.xlsx. Not original SAS authentication."
    return out,info

def rebuild_adlbc(sdtm,adsl,items,*,mode="sap"):
    return rebuild_labs(sdtm,adsl,items,"CHEM",mode=mode)

def rebuild_adlbh(sdtm,adsl,items,*,mode="sap"):
    return rebuild_labs(sdtm,adsl,items,"HEM",mode=mode)
