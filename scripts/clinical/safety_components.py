"""Supported subchecks, explicitly NOT substitutes for complete composite rules."""
import numpy as np
import pandas as pd

def evaluate_components(data):
    rows=[]
    def emit(identifier,domain,frame,status,interpretation):
        for index,state in status.items():
            rows.append({"component":identifier,"domain":domain,"sourceRow":int(index),
                         "subject":frame.loc[index,"USUBJID"],"status":state,
                         "interpretation":interpretation})
    ex=data["ex"]
    start=pd.to_datetime(ex.EXSTDTC.str[:10],format="%Y-%m-%d",errors="coerce")
    end=pd.to_datetime(ex.EXENDTC.str[:10],format="%Y-%m-%d",errors="coerce")
    flags=start.isna() | end.isna() | start.gt(end)
    emit("023.date_order","EX",ex,pd.Series(np.where(flags,"FLAG","NO_FLAG"),index=ex.index),
         "Complete calendar dates and start<=end only; no assertion about full treatment-window eligibility.")
    lb=data["lb"].loc[data["lb"].VISITNUM.isin([1,4,5,7,8,9,10,11,12,13])]
    value=pd.to_numeric(lb.LBSTRESN,errors="coerce")
    low=pd.to_numeric(lb.LBSTNRLO,errors="coerce").mask(lambda x:x.abs().lt(1e-70),0)
    high=pd.to_numeric(lb.LBSTNRHI,errors="coerce").mask(lambda x:x.abs().lt(1e-70),0)
    valid=np.isfinite(value)&np.isfinite(low)&np.isfinite(high)&high.gt(0)&low.le(high)
    flags=value.gt(1.5*high)|value.lt(.5*low)
    states=pd.Series(np.where(~valid,"UNASSESSABLE",np.where(flags,"FLAG","NO_FLAG")),index=lb.index)
    emit("067.sap_analysis_threshold","LB",lb,states,
         "SAP 8.3 threshold range on scheduled visits: >1.5*ULN or <0.5*LLN. NOT a Grade 3/4 or CTCAE classification.")
    vs=data["vs"].loc[data["vs"].VSTESTCD.isin(["SYSBP","DIABP","PULSE","WEIGHT"])]
    flags=~np.isfinite(pd.to_numeric(vs.VSSTRESN,errors="coerce")) | vs.VSSTRESU.isna() | vs.VSSTRESU.astype(str).str.strip().eq("")
    emit("082.completeness","VS",vs,pd.Series(np.where(flags,"FLAG","NO_FLAG"),index=vs.index),
         "Present-record numeric value/unit completeness only; no physiologic limits or expected missing-record check.")
    return pd.DataFrame(rows)
