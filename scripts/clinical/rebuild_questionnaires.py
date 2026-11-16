"""Questionnaire candidates derived from SDTM and cached specifications only."""
import numpy as np
import pandas as pd
from rebuild_adsl import sas_date, normalize_precision
from rebuild_bds import source_frame, parameter_labels, baseline, evidence

def rebuild_questionnaire(sdtm,adsl,items,npix=False,*,mode="sap"):
    if mode not in ("sap","reference-compatible"):raise ValueError("Unknown mode")
    codes=set(items["PARAMCD"]["codes"])
    source,out=source_frame(sdtm["qs"].loc[sdtm["qs"].QSTESTCD.isin(codes)],adsl,items,"QS")
    out["PARAMCD"]=source.QSTESTCD
    out["QSSEQ"]=source.QSSEQ
    out["AVAL"]=source.QSSTRESN
    out["ADT"]=sas_date(source.QSDTC)
    out["ADY"]=out.ADT-out.TRTSDT+out.ADT.ge(out.TRTSDT).astype(int)
    out["ABLFL"]=source.QSBLFL
    out["DTYPE"]=""
    group=["USUBJID","VISITNUM","ADT"]
    if not npix:
        maxima={f"ACITM{i:02}":m for i,m in [(1,10),(2,5),(4,5),(5,5),(6,5),(7,8),(8,12),(11,5),(12,5),(13,5),(14,5)]}
        components=out.loc[out.PARAMCD.isin(maxima)].copy()
        components["availableRange"]=components.PARAMCD.map(maxima).where(components.AVAL.notna(),0)
        aggregate=components.groupby(group,dropna=False).agg(score=("AVAL","sum"),n=("AVAL","count"),available=("availableRange","sum"))
        aggregate["total"]=(aggregate.score*70/aggregate.available.replace(0,np.nan)).where(aggregate.n.ge(8))
        totals=out.PARAMCD.eq("ACTOT")
        out.loc[totals,"AVAL"]=aggregate.total.reindex(pd.MultiIndex.from_frame(out.loc[totals,group])).to_numpy()
        if mode!="reference-compatible":out.loc[totals & ~out.ABLFL.eq("Y"),"QSSEQ"]=np.nan
    parameter_labels(out,items)
    if not npix:
        keep=~(out.PARAMCD.eq("ACTOT") & out.AVAL.isna())
        out=out.loc[keep].copy()
    baseline(out,["USUBJID","PARAMCD"],out.ABLFL.eq("Y"))
    out["CHG"]=out.AVAL-out.BASE
    if (npix and mode=="sap") or (not npix and mode=="reference-compatible"):
        out["CHG"]=out.CHG.where(out.ADY.gt(1))
    out["PCHG"]=100*out.CHG/out.BASE.mask(out.BASE.abs().lt(1e-70))
    out["AVISIT"]="";out["AWRANGE"]="";out["AWU"]="DAYS"
    for c in ["AVISITN","AWLO","AWHI","AWTARGET","AWTDIFF"]:out[c]=np.nan
    windows={0:(-np.inf,1.,1.,"<=1")}
    if npix:
        lows=[2,22,36,50,64,78,92,106,120,134,148,162,176]
        highs=[21,35,49,63,77,91,105,119,133,147,161,175,np.inf]
        windows.update({week:(float(lo),float(hi),float(week*7),f"{lo}-{hi}" if np.isfinite(hi) else ">175") for week,lo,hi in zip(range(2,28,2),lows,highs)})
    else:windows.update({8:(2.,84.,56.,"2-84"),16:(85.,140.,112.,"85-140"),24:(141.,np.inf,168.,">140")})
    def window(frame,visit):
        lo,hi,target,label=windows[visit]
        frame["AVISITN"]=float(visit);frame["AVISIT"]="Baseline" if visit==0 else f"Week {visit}"
        frame["AWLO"]=lo if np.isfinite(lo) else np.nan
        frame["AWHI"]=hi if np.isfinite(hi) else np.nan
        frame["AWTARGET"]=target;frame["AWRANGE"]=label;frame["AWTDIFF"]=(frame.ADY-target).abs()
        return frame
    for visit,(lo,hi,_,_) in windows.items():
        mask=out.ADY.between(lo,hi)
        out.loc[mask,:]=window(out.loc[mask].copy(),visit)
    out["ANL01FL"]=""
    eligible=out.loc[out.AVISITN.notna() & (True if mode=="reference-compatible" else out.AVAL.notna())]
    first=eligible.sort_values(["USUBJID","PARAMCD","AVISITN","AWTDIFF","ADY","QSSEQ"],kind="stable").drop_duplicates(["USUBJID","PARAMCD","AVISITN"]).index
    out.loc[first,"ANL01FL"]="Y"
    if not npix:
        if mode=="reference-compatible":
            for _,g in out.loc[out.PARAMCD.eq("ACTOT")].sort_values(["ADT","VISITNUM"]).groupby("USUBJID",sort=False):
                value=np.nan
                for index,row in g.iterrows():
                    if row.ANL01FL=="Y":value=row.AVAL
                    elif pd.notna(value):
                        out.loc[index,"AVAL"]=value
                        out.loc[index,"CHG"]=value-row.BASE
                        out.loc[index,"PCHG"]=100*(value-row.BASE)/row.BASE if row.BASE else np.nan
                        if not np.isclose(row.AVAL,value,atol=1e-8,rtol=1e-10,equal_nan=True):
                            out.loc[index,"DTYPE"]="LOCF"
        copies=[]
        eligible_totals=out.loc[out.PARAMCD.eq("ACTOT")] if mode=="reference-compatible" else out.loc[first].loc[lambda f:f.PARAMCD.eq("ACTOT")]
        for _,g in eligible_totals.groupby("USUBJID"):
            for visit in [8,16,24]:
                if g.AVISITN.eq(visit).any():continue
                earlier=g.loc[g.AVISITN.lt(visit)].sort_values(["AVISITN","ADT","VISITNUM"])
                if earlier.empty:continue
                row=window(earlier.iloc[[-1]].copy(),visit);row["DTYPE"]="LOCF"
                if mode=="reference-compatible":
                    row["ABLFL"]="";row["ANL01FL"]="Y"
                    row["CHG"]=row.AVAL-row.BASE
                    row["PCHG"]=100*row.CHG/row.BASE.mask(row.BASE.abs().lt(1e-70))
                copies.append(row)
        if copies:out=pd.concat([out,*copies],ignore_index=True)
    else:
        out["PARAMTYP"]=""
        base_rows=out.loc[out.PARAMCD.eq("NPTOT") & out.ABLFL.eq("Y")].copy()
        base_rows["PARAMCD"]="NPTOTMN";base_rows["DTYPE"]="AVERAGE";base_rows["PARAMTYP"]="DERIVED"
        base_rows["ABLFL"]="";base_rows["ANL01FL"]="Y"
        for c in ["CHG","PCHG"]:base_rows[c]=np.nan
        chosen=out.loc[out.PARAMCD.eq("NPTOT") & out.ANL01FL.eq("Y") & out.AVISITN.between(4,24)]
        if mode=="reference-compatible":
            chosen=chosen.loc[chosen.AVISITN.gt(4) & chosen.AVISITN.le(12)]
        means=chosen.groupby("USUBJID").AVAL.mean()
        rows=chosen.sort_values(["USUBJID","ADT"]).drop_duplicates("USUBJID",keep="last").copy()
        rows["AVAL"]=rows.USUBJID.map(means)
        rows["PARAMCD"]="NPTOTMN";rows["PARAMTYP"]="DERIVED";rows["DTYPE"]="AVERAGE"
        rows["AVISITN"]=98.;rows["AVISIT"]="Weeks 4-24";rows["ABLFL"]=""
        for c in ["CHG","PCHG","QSSEQ"]:rows[c]=np.nan
        if mode=="reference-compatible":
            for c in ["ADT","ADY","VISITNUM","AWTDIFF"]:rows[c]=np.nan
            rows["VISIT"]="";rows["AWRANGE"]="22 - 175";rows["AWLO"]=22.;rows["AWHI"]=175.;rows["AWTARGET"]=98.
            definition=items["AVAL"].get("values",{}).get("NPTOTMN",{})
            if definition.get("precision") is not None:
                rows["AVAL"]=normalize_precision(rows.AVAL,definition["precision"])
            rows["AWTDIFF"]=0.
            base_rows["ABLFL"]="Y"
            base_rows["CHG"]=0.
            base_rows["PCHG"]=0.
            base_rows.loc[base_rows.BASE.abs().lt(1e-70),"PCHG"]=np.nan
        out=pd.concat([out,base_rows,rows],ignore_index=True)
        parameter_labels(out,items)
        if mode=="reference-compatible":
            out["AVISIT"]=out.AVISIT.str.rjust(16)
            out["AWRANGE"]=out.AWRANGE.str.replace(r"(?<=\d)-(?=\d)"," - ",regex=True)
            out["AWRANGE"]=out.AWRANGE.replace("<=1","<= 1")
            mask=out.PARAMCD.eq("NPITM02S")
            out.loc[mask,"PARAM"]=out.loc[mask,"PARAM"].str.replace(") Score",")  Score",regex=False)
    info=evidence(items)
    info["AVAL"]="Source values; ADAS total recomputed from 11 item scores with SAP 14.2 range-adjustment and >30% missing exclusion."
    if mode=="reference-compatible":
        for field in ["AVAL","CHG","PCHG","DTYPE","AVISIT","QSSEQ","ABLFL","ANL01FL","AWTDIFF","AWRANGE"]:
            info[field]="EXPERIMENTAL reference-compatible convention; see Tested_Conventions in ADaM_Reference_Compatibility_Experiments.xlsx. Not original SAS authentication."
        if npix:
            info["AVAL"]="EXPERIMENTAL: NPTOTMN uses selected analysis Weeks 6,8,10,12 despite the retained Week 4–24 label. Substantive reference/SAP conflict."
    return out,info

def rebuild_adqsadas(sdtm,adsl,items,*,mode="sap"):
    return rebuild_questionnaire(sdtm,adsl,items,mode=mode)

def rebuild_adqsnpix(sdtm,adsl,items,*,mode="sap"):
    return rebuild_questionnaire(sdtm,adsl,items,npix=True,mode=mode)
