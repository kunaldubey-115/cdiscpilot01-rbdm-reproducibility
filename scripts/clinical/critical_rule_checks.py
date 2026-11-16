"""Predicates supported by cached study definitions; no invented clinical limits."""
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

@lru_cache(maxsize=1)
def controlled_terms():
    path=Path(__file__).resolve().parents[2]/"generated-artifacts/clinical/data/sdtm-define.xml"
    root=ET.parse(path).getroot()
    lists={}
    for node in root.iter():
        if node.tag.split("}")[-1]=="CodeList":
            lists[node.get("OID")]={c.get("CodedValue") for c in node
                if c.tag.split("}")[-1] in ("CodeListItem","EnumeratedItem")}
    result={}
    for node in root.iter():
        if node.tag.split("}")[-1]=="ItemDef":
            ref=next((c.get("CodeListOID") for c in node if c.tag.split("}")[-1]=="CodeListRef"),None)
            if lists.get(ref):result[node.get("OID")]=lists[ref]
    return result

def check(number,d,data):
    if number in (68,83):
        domain="LB" if number==68 else "VS"
        dates=pd.to_datetime(d[domain+"DTC"].str[:10],format="%Y-%m-%d",errors="coerce")
        starts=pd.to_datetime(d.USUBJID.map(data["dm"].set_index("USUBJID").RFSTDTC).str[:10],format="%Y-%m-%d",errors="coerce")
        baseline=d.VISITNUM.eq(1) if number==68 else d.VSBLFL.eq("Y") | d.VISITNUM.eq(3)
        scheduled=d.VISITNUM.isin([4,5,7,8,9,10,11,12])
        selected=baseline | scheduled
        invalid=dates.isna() | starts.isna() | (baseline & dates.gt(starts)) | (scheduled & dates.lt(starts))
        return d.loc[selected],invalid.loc[selected],"Calendar-date chronology review: baseline must not follow first dose; planned postbaseline visits must not precede it. SAP sections 8.3, 11.5/11.6 (CSR physical pp427,432). Same-day observations allowed; no clock-time order inferred. Not a test that every postbaseline visit occurred on drug, nor an expected missing-visit inventory."
    if number==7:
        terms=controlled_terms()
        return d,~d.SEX.isin(terms["DM.SEX"]) | ~d.RACE.isin(terms["DM.RACE"]),"Membership in the study's cached SDTM define.xml SEX/RACE codelists; not a claim of current external terminology certification."
    if number==15:
        d=d.loc[d.DSCAT.eq("DISPOSITION EVENT")].copy()
        absent=data["dm"].loc[~data["dm"].USUBJID.isin(d.USUBJID),["USUBJID"]].copy()
        absent["DSDECOD"]="";absent["DSSEQ"]=float("nan")
        d=pd.concat([d,absent],ignore_index=True)
        return d,~d.DSDECOD.isin(controlled_terms()["DS.DSDECOD"]),"Disposition-event records checked against cached DISCCD; DM subjects without a disposition event generate subject-level flags, not invented source corrections."
    if number==55:
        categories=["ALZHEIMER'S DISEASE ASSESSMENT SCALE","CLINICIAN'S INTERVIEW-BASED IMPRESSION OF CHANGE (CIBIC+)"]
        d=d.loc[d.QSCAT.isin(categories)&(d.QSBLFL.eq("Y") | d.VISIT.eq("BASELINE"))]
        dates=pd.to_datetime(d.QSDTC.str[:10],format="%Y-%m-%d",errors="coerce")
        starts=pd.to_datetime(d.USUBJID.map(data["dm"].set_index("USUBJID").RFSTDTC).str[:10],format="%Y-%m-%d",errors="coerce")
        return d,dates.isna() | starts.isna() | dates.gt(starts),"Present baseline records: complete calendar date <= DM.RFSTDTC; invalid/partial dates flagged, not imputed. Does not assert whole-assessment presence."
    if number==53:
        maxima={f"ACITM{i:02}":m for i,m in [(1,10),(2,5),(4,5),(5,5),(6,5),(7,8),(8,12),(11,5),(12,5),(13,5),(14,5)]}
        group=["USUBJID","VISITNUM","QSDTC"]
        assessments=d.loc[d.QSCAT.eq("ALZHEIMER'S DISEASE ASSESSMENT SCALE")]
        items=assessments.loc[assessments.QSTESTCD.isin(maxima)].copy()
        values=pd.to_numeric(items.QSSTRESN,errors="coerce")
        invalid=values.isna() | values.lt(0) | values.gt(items.QSTESTCD.map(maxima))
        invalid |= items.duplicated(group+["QSTESTCD"],keep=False)
        records=items.copy();records["_flag"]=invalid
        absent=[]
        for key,g in assessments.groupby(group,dropna=False,sort=False):
            missing=set(maxima)-set(g.QSTESTCD)
            if missing:
                row=dict(zip(group,key));row.update(QSSEQ=float("nan"),_flag=True)
                absent.append(row)
        out=pd.concat([records,pd.DataFrame(absent)],ignore_index=True)
        return out,out["_flag"].astype(bool),"SAP scoring item maxima (sum 70), numeric completeness and duplicate-item checks on observed assessments. Missing item rows create assessment-level flags, not invented source rows. Comparator's 100% completeness is stricter than SAP total-score prorating allowance; no whole missing-visit claim."
    return None
